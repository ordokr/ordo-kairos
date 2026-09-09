"""Cross-venue descriptors and the executable deviation between two venues.

``docs/PROTOCOL.md`` Gate C's hypothesis: *for events listed on both venues and verified to be the
same event, the executable price deviation — measured at size off both real order books, net of both
venues' round-trip costs — has a positive median.*

Two halves, kept apart on purpose:

**Descriptors** turn each venue's published market into a :class:`~kairos.identity.ParsedIdentity`,
using **structured fields where the venue publishes them** and the text extractor Gate C exercised
where it does not. Which of the two supplied each field is recorded, because "the matcher refused"
and "the venue never published it" are different findings and Gate C explicitly could not tell them
apart. The *comparison* stays shared — :func:`~kairos.identity.compare_identities`, whose six checks
were shown necessary one at a time — so no venue gets its own copy to drift (AXIOMS G8).

**Deviation** is the payoff identity, not a price difference. Buying YES on one venue and NO on the
other pays exactly $1 whatever happens, *if* the two resolve identically — so the edge is
``1 - (cost_yes + cost_no)``, the same arithmetic as a negRisk set, and the identity it rests on is
exactly as unprovable as an unverified leg set when the pair is not verified.

**Carry is charged on both legs, and that is not a double-count.** Collateral is locked at two venues
simultaneously, so the opportunity cost really is paid twice — the registration says so. The
half-spread is *not* charged, because a VWAP walked off an ask book has already crossed
(``effective_yes_cost_at``, C7).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from .book import Book, cost_to_buy
from .costs import CostModel
from .identity import (
    ParsedIdentity,
    RawMarket,
    detect_negation,
    parse_market,
    scope_tokens,
)

__all__ = [
    "Descriptor",
    "Deviation",
    "days_until",
    "polymarket_descriptor",
    "kalshi_descriptor",
    "date_blocks",
    "fill_pair",
    "edge_from_vwaps",
    "best_direction",
]


@dataclass(frozen=True)
class Descriptor:
    """One venue's market, reduced to what the identity comparison needs plus how to trade it."""

    venue: str
    market_id: str
    label: str
    identity: ParsedIdentity
    #: ``field -> "structured" | "text" | "missing"``. The census reads this to separate a matcher
    #: refusal from a venue that simply does not publish the evidence.
    provenance: tuple[tuple[str, str], ...]
    settle_iso: str | None
    yes_handle: str
    no_handle: str


@dataclass(frozen=True)
class Deviation:
    size: float
    edge: float
    direction: str
    yes_vwap: float
    no_vwap: float


def days_until(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        end = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0.0, (end - datetime.now(timezone.utc)).total_seconds() / 86400.0)


# ---------------------------------------------------------------------------
# Descriptors
# ---------------------------------------------------------------------------


def polymarket_descriptor(market: dict) -> Descriptor | None:
    """Polymarket publishes identity as **prose**, so every field goes through the text extractor.

    ``question`` is the title, ``description`` the rules and ``endDate`` the settlement instant.
    ``endDate`` is *nominal* — markets routinely resolve early — which overstates carry and makes
    edges look worse rather than better. That is the safe direction, and it is stated rather than
    buried (``scanb.py`` carries the same caveat for the same reason).
    """
    mid = str(market.get("id") or "")
    if not mid:
        return None
    try:
        tokens = json.loads(market.get("clobTokenIds") or "[]")
    except (TypeError, ValueError):
        tokens = []
    if len(tokens) < 2:
        return None
    raw = RawMarket(
        venue="polymarket",
        market_id=mid,
        title=str(market.get("question") or ""),
        rules=str(market.get("description") or ""),
        close_iso=str(market.get("endDate") or ""),
    )
    identity = parse_market(raw)
    # **`endDate`'s minute is trusted only when the prose confirms it.** Measured over 788 open
    # markets, 65% of `endDate`s sit at exactly 00:00Z and ~95% at a day boundary, so the field is
    # sometimes a real deadline and sometimes a placeholder and nothing in the payload says which.
    # But it is not unrecoverable either: the Somaliland market's rules say "by December 31, 2026,
    # 11:59 PM ET" and its `endDate` is 2027-01-01T04:59Z - the same instant. So the settlement
    # minute is trusted when two independent published sources agree on it and refused otherwise
    # (Gate C2). This rule can only ever *remove* trust, so its failure mode is lost power, never a
    # false pair - the safe direction for a venue-specific rule the null gate cannot cover.
    if not identity.instant_confirmed:
        identity = replace(identity, missing=tuple(dict.fromkeys(identity.missing
                                                                 + ("settlement_time",))))
    provenance = tuple(
        (field, "missing" if field in identity.missing else "text")
        for field in ("scope", "threshold", "settlement_instant", "settlement_time",
                      "modality", "resolution_source")
    )
    return Descriptor(
        venue="polymarket",
        market_id=mid,
        label=raw.title[:70],
        identity=identity,
        provenance=provenance,
        settle_iso=str(market.get("endDate") or "") or None,
        yes_handle=str(tokens[0]),
        no_handle=str(tokens[1]),
    )


#: Strike types that name a single one-sided threshold. A **range** market (floor *and* cap) is a
#: different object from an above-X binary, and there is no single number that represents it — so
#: rather than collapse it to one bound, the threshold is marked unrecoverable and the pair fails
#: closed. Collapsing it would let a band pair with a binary that shares one of its edges.
_FLOOR_TYPES = frozenset({"greater", "greater_or_equal"})
_CAP_TYPES = frozenset({"less", "less_or_equal"})


def kalshi_descriptor(event: dict, market: dict) -> Descriptor | None:
    """Kalshi publishes strikes, settlement sources and the determination instant as **data**.

    ``close_time`` is the settlement instant, not ``expiration_time``: measured on ``KXBTCD``,
    ``close_time`` is 16:00Z for a market titled "12pm EDT" while ``expiration_time`` sits seven days
    later, which is the administrative settlement window. Using the latter would compare a
    determination instant against a bookkeeping deadline.

    Carry still uses ``expiration_time``, because that is when the collateral is actually released.
    """
    ticker = str(market.get("ticker") or "")
    if not ticker:
        return None
    if market.get("mve_selected_legs") or str(market.get("market_type") or "") != "binary":
        return None  # a parlay leg is not a single event (CORRECTIONS Pass 17)

    missing: list[str] = []
    provenance: dict[str, str] = {}

    close = str(market.get("close_time") or "")
    instant = None
    if len(close) >= 16 and "T" in close:
        instant = f"{close[:10]}T{close[11:16]}Z"
        provenance["settlement_instant"] = "structured"
    else:
        missing.append("settlement_instant")
        provenance["settlement_instant"] = "missing"

    names = [str(s.get("name") or "") for s in (event.get("settlement_sources") or [])]
    source = scope_tokens(" ".join(n for n in names if n))
    if source:
        provenance["resolution_source"] = "structured"
    else:
        missing.append("resolution_source")
        provenance["resolution_source"] = "missing"

    strike_type = str(market.get("strike_type") or "")
    floor, cap = market.get("floor_strike"), market.get("cap_strike")
    threshold: float | None = None
    if floor is not None and cap is not None:
        missing.append("threshold")
        provenance["threshold"] = "missing"  # a band, not a strike
    elif strike_type in _FLOOR_TYPES and floor is not None:
        threshold = float(floor)
        provenance["threshold"] = "structured"
    elif strike_type in _CAP_TYPES and cap is not None:
        threshold = float(cap)
        provenance["threshold"] = "structured"
    elif floor is None and cap is None:
        # No numeric strike. For ``strike_type == "custom"`` the selector is an *outcome*, not a
        # threshold — ``{"Holder": "Klaus Iohannis"}`` — and it belongs in the scope, where it makes
        # the identity more specific rather than less. Folding it in can only reduce accidental
        # matches, so it is safe in the direction that matters.
        provenance["threshold"] = "structured"
    else:
        missing.append("threshold")
        provenance["threshold"] = "missing"  # a strike exists but its type is unrecognised

    custom = market.get("custom_strike")
    selector = " ".join(str(v) for v in custom.values()) if isinstance(custom, dict) else ""
    title = str(event.get("title") or market.get("title") or "")
    sub = str(market.get("yes_sub_title") or "")
    scope = scope_tokens(f"{title} {sub} {selector}")
    if scope:
        provenance["scope"] = "text"
    else:
        missing.append("scope")
        provenance["scope"] = "missing"

    # Modality from the subtitle, which is where Kalshi puts it: "Before Jan 1, 2050" is a deadline,
    # "On Sep 9, 2026 at 12pm EDT" and a strike like "$68,600 or above" are determined at the close.
    # The event's own subtitle is the fallback, because a market-level subtitle is sometimes just the
    # outcome name ("Mars") with the period stated one level up.
    modality = None
    for text in (sub, str(event.get("sub_title") or "")):
        head = text.strip().split(" ")[0].lower() if text.strip() else ""
        if head in ("before", "by"):
            modality = "deadline"
            break
        if head in ("on", "at", "above", "below") or head[:1].isdigit() or head[:1] == "$":
            modality = "instant"
            break
    if modality is None:
        missing.append("modality")
        provenance["modality"] = "missing"
    else:
        provenance["modality"] = "structured"

    identity = ParsedIdentity(
        scope=scope,
        threshold=threshold,
        instant=instant,
        source=source,
        negated=detect_negation(f"{title} {sub} {selector}"),
        missing=tuple(missing),
        modality=modality,
        instant_confirmed=instant is not None,
    )
    return Descriptor(
        venue="kalshi",
        market_id=ticker,
        label=f"{title} / {sub}"[:70],
        identity=identity,
        provenance=tuple(sorted(provenance.items())),
        settle_iso=str(market.get("expiration_time") or market.get("close_time") or "") or None,
        yes_handle=ticker,
        no_handle=ticker,
    )


def date_blocks(left: list[Descriptor], right: list[Descriptor]
                ) -> dict[str, tuple[list[Descriptor], list[Descriptor]]]:
    """Group both venues by resolution **date**, the one check that must agree exactly.

    Blocking on a key the comparison already requires cannot lose a pair the comparison would have
    accepted, so this is a speed-up rather than a second filter with its own error rate. Descriptors
    with no recoverable instant are dropped here and counted by the caller — they could never pair.
    """
    blocks: dict[str, tuple[list[Descriptor], list[Descriptor]]] = {}
    for side, items in ((0, left), (1, right)):
        for d in items:
            if not d.identity.instant:
                continue
            day = d.identity.instant[:10]
            blocks.setdefault(day, ([], []))[side].append(d)
    return blocks


# ---------------------------------------------------------------------------
# The deviation
# ---------------------------------------------------------------------------


def fill_pair(yes_book: Book, no_book: Book, size: float) -> tuple[float, float] | str:
    """VWAPs to buy ``size`` YES on one venue and ``size`` NO on the other, or a named refusal.

    A partial fill is a refusal, not a cheaper trade. Half a hedge is an outright position, which is
    the one thing a "riskless" strategy must never accidentally hold (AXIOMS D1).
    """
    yes_fill = cost_to_buy(yes_book, size)
    if not yes_fill.complete:
        return "thin_yes_leg"
    no_fill = cost_to_buy(no_book, size)
    if not no_fill.complete:
        return "thin_no_leg"
    return yes_fill.vwap, no_fill.vwap


def edge_from_vwaps(yes_vwap: float, no_vwap: float, days: float, costs: CostModel) -> float:
    """``1 - (all-in cost of the YES leg + all-in cost of the NO leg)``.

    Both legs pay $1 on their own venue and exactly one of them wins, so the pair pays $1. Charging
    ``effective_yes_cost_at`` on the NO leg is correct rather than a shortcut: a NO contract has the
    same $1 payoff, the same taker fee shape and the same locked collateral.
    """
    return 1.0 - (costs.effective_yes_cost_at(yes_vwap, days)
                  + costs.effective_yes_cost_at(no_vwap, days))


def best_direction(poly_yes: Book, poly_no: Book, kalshi_yes: Book, kalshi_no: Book,
                   *, size: float, days: float, costs: CostModel
                   ) -> tuple[Deviation | None, str]:
    """The better of the two hedges, or the reason neither is executable.

    Both directions are tried because a deviation has a sign and only one side of it is tradeable:
    buying YES where it is cheap and NO where it is dear is a different trade from its mirror, and a
    scanner that checks only one direction measures half the distribution while reporting all of it.
    """
    best: Deviation | None = None
    reasons: list[str] = []
    for name, yes_book, no_book in (
        ("yes_polymarket", poly_yes, kalshi_no),
        ("yes_kalshi", kalshi_yes, poly_no),
    ):
        filled = fill_pair(yes_book, no_book, size)
        if isinstance(filled, str):
            reasons.append(f"{name}:{filled}")
            continue
        yes_vwap, no_vwap = filled
        edge = edge_from_vwaps(yes_vwap, no_vwap, days, costs)
        if best is None or edge > best.edge:
            best = Deviation(size, edge, name, yes_vwap, no_vwap)
    return best, "ok" if best else ("|".join(reasons) or "no_book")
