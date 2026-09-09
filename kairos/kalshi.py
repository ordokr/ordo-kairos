"""Kalshi adapter: events, markets, order books, and the fee schedule the protocol requires.

``docs/PROTOCOL.md`` Gate C names Kalshi (`trade-api/v2`) as the second venue. Everything here is
public and unauthenticated, verified 2026-09-09.

Three apparatus facts, measured against the live API rather than assumed
-----------------------------------------------------------------------

**1. The order book is one-sided, and reading it directly inverts the trade.** Kalshi publishes only
*resting bids*: ``yes_dollars`` are bids to buy YES, ``no_dollars`` are bids to buy NO. There is no
ask ladder. A bid to buy NO at ``q`` **is** an offer to sell YES at ``1 - q``, so the YES ask ladder
is the NO bid ladder mirrored — and a caller who reads ``yes_dollars`` as asks would price a buy at
the *bid*, manufacturing an edge equal to the whole spread on every market.

Measured on 14 two-sided markets against the venue's own published quotes:

===================================  ======
``bid == max(yes_dollars)``          14/14
``ask == 1 - max(no_dollars)``       13/14
===================================  ======

The single miss was one tick (0.31 published vs 0.32 derived) between two calls seconds apart, which
is a snapshot race rather than a disagreement. The probe also showed sub-cent resting prices
(0.225 / 0.247) where the summary fields round to whole cents, so **the book is more precise than
``yes_ask_dollars``** and is the right input for an executable price.

**2. ``/markets`` returns parlay shards first.** A cursor sweep of ``/markets`` came back as 1,600
consecutive MVE parlay legs and no singles, which is not what a venue looks like; it produced the
false claim "0 of 1,600 quoted, all zero liquidity" (``CORRECTIONS.md`` Pass 17). Use
``/events?with_nested_markets=true``, which returned 87 of 132 nested markets two-sided quoted.

**3. Structured evidence exists and should be used as structured.** ``settlement_sources``,
``floor_strike``/``cap_strike`` and ``expiration_time`` are published as data. Round-tripping them
through prose so a text extractor can parse them back would add a failure mode for nothing.
"""

from __future__ import annotations

import json
import time
import urllib.error
from dataclasses import dataclass

from .book import Book, Level
from .polymarket import _get_retry

__all__ = [
    "KALSHI",
    "FeeSchedule",
    "KALSHI_FEES",
    "fetch_events",
    "fetch_books",
    "books_from_orderbook",
]

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"


@dataclass(frozen=True)
class FeeSchedule:
    """A venue's fee terms **and whether anyone checked them**.

    Gate C's frozen parameters require Kalshi's schedule to be "verified against its published terms
    before the run; pending that, the conservative quadratic form is assumed". A bare coefficient
    cannot express that condition, so the verification status travels with the number and the runner
    is expected to read it.

    This matters more than the usual pedantry because Gate C's kill rule is **terminal**: a verdict
    of "does not clear costs" ends the programme. An overstated fee would therefore kill a real edge,
    and an understated one would manufacture a false one. The number is load-bearing in both
    directions, so it may not be a silent default.
    """

    taker_coeff: float
    verified: bool
    source: str
    checked_on: str
    note: str


#: **Unverified.** Fetching the published schedule on 2026-09-09 returned HTTP 429 from
#: ``kalshi.com`` and the documentation host 404ed on the paths tried. The registered fallback
#: therefore applies: the conservative quadratic form, which is the shape of Kalshi's published fee
#: and is already the default in :mod:`kairos.costs`. `scanc.py` must not announce Gate C's terminal
#: verdict on the strength of this number alone — it reports the fee coefficient at which the verdict
#: would flip instead, which turns an unverified input into a measured dependency (AXIOMS A6, G3).
KALSHI_FEES = FeeSchedule(
    taker_coeff=0.07,
    verified=False,
    source="https://kalshi.com/docs/kalshi-fee-schedule.pdf",
    checked_on="2026-09-09",
    note="fetch returned HTTP 429; docs host 404 on /trading/fees and /getting-started/fees",
)


def fetch_events(pages: int = 20, *, status: str = "open", limit: int = 200,
                 pause: float = 0.15) -> list[dict]:
    """Sweep ``/events?with_nested_markets=true`` by cursor.

    Cursor pagination, not offset: the API returns the next cursor and an empty one at the end, so
    the sweep stops on the venue's own signal rather than on a page count that could silently
    truncate the universe (the defect ``fetch_window`` exists for on the other venue).
    """
    out: list[dict] = []
    cursor = ""
    for _ in range(pages):
        url = (f"{KALSHI}/events?with_nested_markets=true&limit={limit}&status={status}"
               + (f"&cursor={cursor}" if cursor else ""))
        try:
            page = _get_retry(url, timeout=30)
        except urllib.error.HTTPError as e:
            print(f"      kalshi events: HTTP {e.code} - partial universe", flush=True)
            break
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            print("      kalshi events: network - partial universe", flush=True)
            break
        events = (page or {}).get("events") or []
        if not events:
            break
        out.extend(events)
        cursor = (page or {}).get("cursor") or ""
        if not cursor:
            break
        time.sleep(pause)
    return out


def _ladder(rows, *, mirror: bool) -> tuple[Level, ...]:
    levels: list[Level] = []
    for row in rows or []:
        try:
            price, size = float(row[0]), float(row[1])
        except (TypeError, ValueError, IndexError):
            continue  # a malformed level is not a level; dropping it is a measurement
        if mirror:
            price = 1.0 - price
        if size > 0.0:
            levels.append(Level(price, size))
    return tuple(levels)


def books_from_orderbook(raw: dict) -> tuple[Book, Book]:
    """``(yes_book, no_book)`` from one Kalshi order book.

    The mirroring is the whole point of this function and is the fact measured in the module
    docstring: an ask on one side is a resting bid on the other. Both books are sorted **best-first**
    to match :class:`kairos.book.Book`'s contract, and sorted explicitly rather than reversed,
    because an ordering that silently changed would flip every price while still looking like a book.
    """
    ob = raw.get("orderbook_fp") or raw.get("orderbook") or {}
    yes_bids = _ladder(ob.get("yes_dollars"), mirror=False)
    no_bids = _ladder(ob.get("no_dollars"), mirror=False)

    def book(asks: tuple[Level, ...], bids: tuple[Level, ...]) -> Book:
        return Book(asks=tuple(sorted(asks, key=lambda lv: lv.price)),
                    bids=tuple(sorted(bids, key=lambda lv: -lv.price)),
                    tick_size=0.01)

    return (
        book(asks=_ladder(ob.get("no_dollars"), mirror=True), bids=yes_bids),
        book(asks=_ladder(ob.get("yes_dollars"), mirror=True), bids=no_bids),
    )


def fetch_books(ticker: str) -> tuple[Book | None, Book | None, str]:
    """``(yes_book, no_book, reason)``. ``reason`` is ``"ok"`` or names the fault.

    Never cached. A book is a snapshot of something that changes by the second, and caching it turns
    a live executability check into a claim about the past. The failure is *named* rather than
    returned as a bare ``None`` so a caller counting failures cannot merge "the venue is illiquid"
    with "the network dropped" (AXIOMS G5).
    """
    try:
        raw = _get_retry(f"{KALSHI}/markets/{ticker}/orderbook", timeout=20)
    except urllib.error.HTTPError as e:
        return None, None, f"http_{e.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None, "network"
    except json.JSONDecodeError:
        return None, None, "unparseable"
    if not isinstance(raw, dict):
        return None, None, "unexpected_payload"
    yes_book, no_book = books_from_orderbook(raw)
    return yes_book, no_book, "ok"
