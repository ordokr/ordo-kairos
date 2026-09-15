"""Leg-set completeness and exhaustiveness verification for Class B.

Gate B measured where the Class B false-positive risk actually lives, and it is not in the scanner.
A truncated group whose leg set is *asserted* complete fires **1.000 at every horizon**, and no
arithmetic inside `scan` can prevent it: a leg never seen cannot be reasoned about. So the entire
defence rests here.

Two separate properties, both of which the buy-every-leg identity needs and neither of which is
visible in prices:

**Completeness** — do we hold *every* leg? A paginated `/markets` scan sees whatever the page
boundary gave it, and does not announce the difference. This is what produced an apparent 53%
arbitrage in the first hand-probe of this API.

**Exhaustiveness** — do the listed outcomes cover the space? If an unlisted outcome occurs, every
leg resolves NO, the set pays **$0** rather than $1, and the "riskless" trade loses the entire
stake. This is not a smaller version of a mispricing; it is a different sign.

Measured, not assumed
---------------------

``/events/<id>`` returns the authoritative full market list. Verified against the live API
2026-09-08 on a 70-event sample: markets per event 3–51 with no round-number cap (so it does not
silently truncate the way offset pagination does), and **0/70 events spanned more than one
``negRiskMarketID``**, so event id is a safe group key. ``negRiskRequestID`` is **not** — it is
per-market (2,896 ids across 2,896 markets), and grouping on it yields singletons.

On exhaustiveness the measurement contradicted the obvious rule. Only **36%** of negRisk events
carry an explicit ``negRiskOther`` catch-all leg, so refusing the rest would discard two thirds of
the universe. But across **75 fully-resolved groups, every single one had exactly one winner** —
including all 54 with no Other leg. Zero-winner groups: **0/75**.

That does not make the risk zero, and this module refuses to pretend it does. Zero failures in 75
trials bounds the rate at roughly **4%** (rule of three), and 4% is not small next to a 5% edge —
see :func:`break_even_failure_rate`. The bound is a function of how many groups have been checked,
so the honest gate is arithmetic rather than a flag: **the residual risk must be smaller than the
edge can absorb**, and the sample that establishes it must be large enough to say so.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .polymarket import HEADERS, _get_retry, cache_dir

__all__ = [
    "EventLegSet",
    "LegSetVerification",
    "EXHAUSTIVENESS_TRIALS",
    "EXHAUSTIVENESS_FAILURES",
    "fetch_event",
    "event_leg_set",
    "residual_failure_bound",
    "break_even_failure_rate",
    "verify_leg_set",
]

EVENTS = "https://gamma-api.polymarket.com/events"

#: Measured on fully-resolved negRisk groups: every one had exactly one winning leg. These two
#: numbers are the entire empirical basis for tolerating a group with no explicit ``negRiskOther``
#: leg, and they are stated as a sample rather than a fact so the bound they support shrinks only
#: when someone measures more (AXIOMS A6).
#:
#: **Outputs of ``exhaustiveness.py``. Regenerate, never hand-edit** — the bound is load-bearing for
#: which trades are allowed, so a number typed in by hand is a trading rule with no evidence behind
#: it. Re-run after fetching more markets; the sample grows with the cache.
#:
#: ==========  =======  =======  ============  =================
#: measured    trials   fails    bound (3/n)   smallest edge
#: ==========  =======  =======  ============  =================
#: 2026-09-08       75        0       0.0400   ~5%
#: 2026-09-09      512        0       0.0059   ~1%
#: ==========  =======  =======  ============  =================
#:
#: Also measured across 4,968 closed negRisk legs: **zero voided, zero unclean**. That matters
#: because a voided group would be dropped by a clean-resolution filter, making the sample
#: structurally unable to contain the failures it looks for; the channel does not exist here.
EXHAUSTIVENESS_TRIALS = 512
EXHAUSTIVENESS_FAILURES = 0


@dataclass(frozen=True)
class EventLegSet:
    """The authoritative leg set for one negRisk event."""

    event_id: str
    neg_risk_market_id: str | None
    market_ids: frozenset[str]
    has_other_leg: bool
    all_closed: bool

    @property
    def n_legs(self) -> int:
        return len(self.market_ids)


@dataclass(frozen=True)
class LegSetVerification:
    """Whether a held leg set may be treated as complete and exhaustive, and on what evidence."""

    event_id: str
    observed: frozenset[str]
    authoritative: EventLegSet | None
    refusals: tuple[str, ...] = ()
    evidence: tuple[str, ...] = field(default=())

    @property
    def complete(self) -> bool:
        return not self.refusals and self.authoritative is not None

    @property
    def missing(self) -> frozenset[str]:
        """Legs the authority lists that we do not hold — the truncation, made visible."""
        if self.authoritative is None:
            return frozenset()
        return self.authoritative.market_ids - self.observed

    def exhaustive(self, *, edge: float, stake: float) -> bool:
        """Whether exhaustiveness is safe **for this edge**, not in the abstract.

        An explicit ``negRiskOther`` leg settles it outright. Failing that, the residual risk from
        the measured sample must be smaller than the edge can absorb — which is a statement about
        the trade, not about the group, and is why this takes arguments.
        """
        if self.authoritative is None:
            return False
        if self.authoritative.has_other_leg:
            return True
        return residual_failure_bound() < break_even_failure_rate(edge, stake)

    def explain(self, *, edge: float = 0.05, stake: float = 0.95) -> str:
        if self.refusals:
            return f"event {self.event_id}: REFUSED ({', '.join(self.refusals)})"
        a = self.authoritative
        assert a is not None
        exh = "explicit Other leg" if a.has_other_leg else (
            f"no Other leg; residual bound {residual_failure_bound():.3f} vs break-even "
            f"{break_even_failure_rate(edge, stake):.3f}"
        )
        return (
            f"event {self.event_id}: {a.n_legs} legs, complete, "
            f"exhaustive={self.exhaustive(edge=edge, stake=stake)} ({exh})"
        )


def fetch_event(event_id: str, *, use_cache: bool = True) -> dict | None:
    """One event with its full market list. Cached; **failures are never cached** (AXIOMS G5)."""
    cache = cache_dir() / "events"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{str(event_id)[:40]}.json"
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    try:
        data = _get_retry(f"{EVENTS}/{event_id}", timeout=25)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # a genuinely absent event IS a measurement; cache nothing either way
        return None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        return None
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def event_leg_set(event: dict) -> EventLegSet | None:
    """Reduce a raw event to its leg set, or None if it carries no usable market list."""
    markets = event.get("markets")
    if not isinstance(markets, list) or not markets:
        return None
    ids = frozenset(str(m.get("id")) for m in markets if m.get("id") is not None)
    if not ids:
        return None
    nrms = {m.get("negRiskMarketID") for m in markets if m.get("negRiskMarketID")}
    return EventLegSet(
        event_id=str(event.get("id")),
        neg_risk_market_id=next(iter(nrms)) if len(nrms) == 1 else None,
        market_ids=ids,
        has_other_leg=any(bool(m.get("negRiskOther")) for m in markets),
        all_closed=all(bool(m.get("closed")) for m in markets),
    )


def residual_failure_bound(
    trials: int = EXHAUSTIVENESS_TRIALS, failures: int = EXHAUSTIVENESS_FAILURES
) -> float:
    """Upper bound on the non-exhaustiveness rate given ``failures`` in ``trials``.

    With zero observed failures this is the **rule of three**: the 95% upper bound on a rate that
    has never been seen in ``n`` trials is about ``3/n``. Never zero — "we have not seen it" is not
    evidence that it cannot happen (AXIOMS A6), and the whole point of returning a *bound* rather
    than a point estimate is that the bound shrinks only by measuring more groups.
    """
    if trials <= 0:
        return 1.0
    if failures <= 0:
        return min(1.0, 3.0 / trials)
    return min(1.0, (failures + 3.0 * (failures ** 0.5) + 3.0) / trials)


def break_even_failure_rate(edge: float, stake: float) -> float:
    """The non-exhaustiveness rate at which the arbitrage stops being worth taking.

    If every leg resolves NO the whole ``stake`` is lost, not merely the edge. So

        EV = (1 - q) * edge - q * stake = 0   =>   q* = edge / (edge + stake)

    For a 5% edge on a 0.95 stake that is **5%** — uncomfortably close to the 4% bound the current
    exhaustiveness sample supports. A "riskless" trade whose failure mode costs twenty times its
    profit needs its failure rate measured, not assumed.
    """
    if edge <= 0.0:
        return 0.0
    if stake <= 0.0:
        return 1.0
    return edge / (edge + stake)


def verify_leg_set(
    event_id: str,
    observed_market_ids: Iterable[str],
    *,
    use_cache: bool = True,
) -> LegSetVerification:
    """Check a held leg set against the authoritative event listing.

    The authority is ``/events/<id>``, and it is **cross-checked rather than trusted**: if we hold a
    market the event does not list, the event is not authoritative for this group and the whole
    verification is refused. Trusting an endpoint to be complete is the assumption that produced the
    problem this module exists to solve.
    """
    observed = frozenset(str(m) for m in observed_market_ids)
    event = fetch_event(event_id, use_cache=use_cache)
    if event is None:
        return LegSetVerification(str(event_id), observed, None, ("event_unavailable",))
    legs = event_leg_set(event)
    if legs is None:
        return LegSetVerification(str(event_id), observed, None, ("event_lists_no_markets",))

    refusals: list[str] = []
    evidence: list[str] = [f"authority={legs.n_legs} legs"]
    if legs.neg_risk_market_id is None:
        # 0/70 sampled events spanned more than one group id, so this is anomalous rather than
        # routine - and an ambiguous grouping makes the payoff identity unprovable.
        refusals.append("event_spans_multiple_or_zero_neg_risk_groups")
    extra = observed - legs.market_ids
    if extra:
        refusals.append("authority_incomplete")
        evidence.append(f"held-but-unlisted={len(extra)}")
    missing = legs.market_ids - observed
    if missing:
        refusals.append("legs_missing")
        evidence.append(f"missing={len(missing)}")
    if legs.has_other_leg:
        evidence.append("explicit_other_leg")
    else:
        evidence.append(f"no_other_leg; residual_bound={residual_failure_bound():.3f}")
    return LegSetVerification(
        str(event_id), observed, legs, tuple(refusals), tuple(evidence)
    )
