"""Order-book depth: what a set of legs actually costs to buy at size.

Gate B enforced ``MIN_FILL`` against a **synthetic** depth field, which made it the one part of the
Class B stack with no real data behind it. This is that layer.

**An edge at the touch is not an edge at size.** Buying one contract at the best ask says nothing
about buying twenty-five: the book thins, and the marginal price walks away from you. So the cost of
a leg is the **volume-weighted average price to fill the target size**, not the top-of-book quote,
and a set that cannot be filled at size is reported as unexecutable rather than as a cheap
opportunity (AXIOMS D1).

Two apparatus facts, measured against the live CLOB rather than assumed
-----------------------------------------------------------------------

**The book is sorted worst-first on both sides.** Asks arrive descending — ``0.999, 0.998, 0.95,
…`` — so ``asks[0]`` is the price you would never get. Verified against Gamma's own ``bestAsk``
field on 12 live markets: best ask equals ``asks[-1]`` in **12/12** and ``asks[0]`` in **0/12**.
Reading the top of the list is not a small error; on every market probed it returned 0.999.

**A crossed price must not be charged spread again.** ``CostModel.effective_yes_cost`` takes a *mid*
and adds ``half_spread`` to model crossing. A VWAP walked off the ask book has already crossed, so
passing it there would charge the spread twice — the same double-count that C7 exists for. Use
:meth:`CostModel.effective_yes_cost_at`, which takes an already-traded price and applies taker fee
and carry only.
"""

from __future__ import annotations

import json
import urllib.error
from dataclasses import dataclass
from typing import Sequence

from .polymarket import _get_retry, cache_dir

__all__ = ["Level", "Book", "Fill", "parse_book", "fetch_book", "fetch_book_result",
           "cost_to_buy", "proceeds_from_sell", "queue_fills"]

CLOB_BOOK = "https://clob.polymarket.com/book"


@dataclass(frozen=True)
class Level:
    price: float
    size: float


@dataclass(frozen=True)
class Book:
    """One side-pair, each **sorted best-first** — asks ascending, bids descending.

    The raw endpoint sorts both worst-first. Normalising here, once, means no caller has to remember
    which end is which; the alternative is every consumer independently rediscovering that
    ``asks[0]`` is 0.999.
    """

    asks: tuple[Level, ...]
    bids: tuple[Level, ...]
    tick_size: float = 0.001
    min_order_size: float = 0.0

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def ask_depth(self) -> float:
        return sum(lv.size for lv in self.asks)


@dataclass(frozen=True)
class Fill:
    """The result of walking one side of the book for a target size.

    Used for both directions: ``vwap`` is the price paid when walking the asks and the price
    received when walking the bids.
    """

    vwap: float
    filled: float
    requested: float
    levels_consumed: int

    @property
    def complete(self) -> bool:
        return self.filled >= self.requested - 1e-9

    def explain(self) -> str:
        status = "filled" if self.complete else f"PARTIAL ({self.filled:.0f}/{self.requested:.0f})"
        return f"{status} at vwap {self.vwap:.4f} across {self.levels_consumed} level(s)"


def parse_book(raw: dict) -> Book:
    """Normalise a raw CLOB book to best-first ordering.

    Sorted explicitly rather than reversed. Reversing assumes the endpoint's ordering is stable, and
    an ordering that silently changed would flip every price in the system while still looking like
    a book.
    """
    def levels(key: str, *, ascending: bool) -> tuple[Level, ...]:
        out: list[Level] = []
        for item in raw.get(key) or []:
            try:
                out.append(Level(float(item["price"]), float(item["size"])))
            except (KeyError, TypeError, ValueError):
                continue  # a malformed level is not a level; dropping it is a measurement
        out.sort(key=lambda lv: lv.price, reverse=not ascending)
        return tuple(out)

    def num(key: str, default: float) -> float:
        try:
            return float(raw.get(key, default))
        except (TypeError, ValueError):
            return default

    return Book(
        asks=levels("asks", ascending=True),    # best ask = lowest
        bids=levels("bids", ascending=False),   # best bid = highest
        tick_size=num("tick_size", 0.001),
        min_order_size=num("min_order_size", 0.0),
    )


def fetch_book_result(token_id: str, *, use_cache: bool = False) -> tuple[Book | None, str]:
    """``(book, reason)``. ``reason`` is ``"ok"`` on success and names the fault otherwise.

    :func:`fetch_book` returns a bare ``None`` on failure, which is convenient and is exactly how a
    scan came to report "29 groups too thin to fill" when the real answer was 29 groups whose books
    never loaded — a claim about the venue's liquidity that was actually a claim about the network.
    Callers that intend to *count* failures must use this form (AXIOMS G5).
    """
    cache = cache_dir() / "books"
    path = cache / f"{str(token_id)[:40]}.json"
    if use_cache and path.exists():
        try:
            return parse_book(json.loads(path.read_text(encoding="utf-8"))), "ok"
        except json.JSONDecodeError:
            pass
    try:
        raw = _get_retry(f"{CLOB_BOOK}?token_id={token_id}", timeout=20)
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, "network"
    except json.JSONDecodeError:
        return None, "unparseable"
    if not isinstance(raw, dict):
        return None, "unexpected_payload"
    if use_cache:
        cache.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw), encoding="utf-8")
    return parse_book(raw), "ok"


def fetch_book(token_id: str, *, use_cache: bool = False) -> Book | None:
    """Live order book for one CLOB token, or ``None``.

    ``use_cache`` defaults to **False**, unlike every other fetcher here. A book is a snapshot of
    something that changes by the second; caching it would turn a live executability check into a
    claim about the past, which is precisely what an arbitrage candidate must not be.

    Use :func:`fetch_book_result` when the failure needs to be counted rather than merely handled.
    """
    return fetch_book_result(token_id, use_cache=use_cache)[0]


def cost_to_buy(book: Book, size: float) -> Fill:
    """Walk the ask book from the best price and return the VWAP to fill ``size``.

    Returns a **partial** fill rather than raising when the book is too thin, because "you can buy
    6 of the 25 you wanted" is a measurement and the caller needs it to refuse for the right reason.
    ``vwap`` on a partial fill is the average over what *was* available, and is meaningless as an
    execution price — check :attr:`Fill.complete` before using it.
    """
    return _walk(book.asks, size)


def proceeds_from_sell(book: Book, size: float) -> Fill:
    """Walk the **bid** book from the best price and return the VWAP received to sell ``size``.

    The exit side of a round trip. Selling is not buying with the sign flipped — it consumes the
    other side of the book and the price walks *down* — so a sell priced off the asks reports a
    credit the seller would never receive.

    Partial fills are returned rather than raised, for the same reason as :func:`cost_to_buy`: a
    position that cannot be closed at size is a measurement the caller has to be able to refuse on.
    """
    return _walk(book.bids, size)


def queue_fills(side_flow: float, queue_ahead: float) -> float:
    """Contracts an order joining the **back** of the touch queue expects to fill.

    ``docs/PROTOCOL.md`` Gate 3.0. Gate M measured what a fill is worth; this is whether one
    happens. Price priority puts the resting size ahead of a new order, so nothing reaches it until
    ``queue_ahead`` is consumed — and **where a day's one-sided flow is smaller than the size already
    resting, the entrant is never filled and the strategy earns exactly zero**, whatever the spread
    it was quoting.

    Negative inputs raise rather than clamp: a negative flow or a negative queue is a broken
    measurement upstream, and silently reading it as zero would turn that into a finding.
    """
    if side_flow < 0.0 or queue_ahead < 0.0:
        raise ValueError(f"flow and queue must be non-negative, got {side_flow!r}, {queue_ahead!r}")
    return max(0.0, side_flow - queue_ahead)


def _walk(levels: Sequence[Level], size: float) -> Fill:
    """Consume ``levels`` best-first until ``size`` is filled. Both sides are already normalised."""
    if size <= 0:
        raise ValueError(f"size must be positive, got {size!r}")
    remaining = size
    notional = 0.0
    consumed = 0
    for level in levels:
        if remaining <= 1e-9:
            break
        take = min(level.size, remaining)
        notional += take * level.price
        remaining -= take
        consumed += 1
    filled = size - remaining
    vwap = notional / filled if filled > 0 else float("nan")
    return Fill(vwap=vwap, filled=filled, requested=size, levels_consumed=consumed)
