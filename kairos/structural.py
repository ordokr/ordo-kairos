"""Class B: structural (negRisk) arbitrage, and the null gate that must precede any scanner.

``docs/CENSUS-RESULTS.md`` Decision 001 held Class B behind its own null gate because **its
false-positive mode is unmeasured and severe**. Building the scanner first would repeat exactly the
error Gate 0 exists to prevent (A7). This module is the gate; it contains a scanner only because a
gate needs something to falsify.

**The claim under test.** A negRisk group is a set of mutually exclusive, exhaustive outcomes. Buying
one YES contract on every leg pays exactly $1 at settlement, whatever happens. So if the all-in cost
of the full set is below $1, the difference is riskless. That is the entire Class B thesis, and it is
a statement about *payoff identity* rather than about forecasting — which is why Look 3's rejection
of Class A says nothing about it.

**Three false-positive generators, all measured in the census, none hypothetical:**

1. **Truncation.** A paginated scan sees part of a group and sums incomplete legs. A first hand-probe
   of this API produced an apparent **53% arbitrage** entirely this way.
2. **Carry.** Collateral is locked until settlement, so a correctly-priced group *is supposed to*
   sum to less than $1. Carry adjustment reversed the sign on every long-dated group tested.
3. **Unstated exhaustiveness.** If the listed outcomes do not cover the space, the legs do not pay
   $1 between them and the identity the whole thesis rests on simply does not hold.

**One carry model, not two (AXIOMS C7).** ``CostModel.effective_yes_cost`` *already* charges carry
internally. Comparing its output against a discounted payoff would charge carry twice. So the
scanner compares all-in cost against a **nominal $1**, and the discounting lives only in the world
that generates prices. That asymmetry is deliberate and is itself under test: the two carry models in
this repo disagree by 0.0034 at one year and **0.0129 at two years** — larger than a plausible
arbitrage — so the gate measures what that inconsistency costs rather than assuming it away.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Callable, Sequence

from .baseline import SettlementTerms
from .costs import CONSERVATIVE, CostModel

__all__ = [
    "Leg",
    "NegRiskGroup",
    "ScanResult",
    "fair_group",
    "truncate_legs",
    "hide_an_outcome",
    "add_quote_noise",
    "inject_arbitrage",
    "scan",
    "scan_naive",
    "scan_verified",
]

#: Minimum fillable size, in contracts, before an edge counts as tradeable at all (AXIOMS D1).
#: An arbitrage you cannot fill is not an arbitrage; it is a screenshot.
MIN_FILL = 25.0

EPS = 1e-6


@dataclass(frozen=True)
class Leg:
    """One outcome in a negRisk group: its YES mid and the size fillable there."""

    outcome: str
    price: float
    depth: float


@dataclass(frozen=True)
class NegRiskGroup:
    """A set of outcomes that should be mutually exclusive and exhaustive.

    ``legs_are_complete`` and ``outcomes_are_exhaustive`` are **claims about knowledge**, not about
    the market. They record whether the scanner *knows* it has every leg and whether the listed
    outcomes cover the space. Both default to unknown, and the scanner refuses on unknown, because
    "we did not measure it" is not evidence of safety (AXIOMS A6).
    """

    group_id: str
    legs: tuple[Leg, ...]
    days_to_settlement: float
    legs_are_complete: bool = False
    outcomes_are_exhaustive: bool = False

    @property
    def nominal_sum(self) -> float:
        return sum(leg.price for leg in self.legs)


@dataclass(frozen=True)
class ScanResult:
    group_id: str
    fires: bool
    edge: float
    fillable: float
    refusals: tuple[str, ...]

    def explain(self) -> str:
        if self.refusals:
            return f"{self.group_id}: REFUSED ({', '.join(self.refusals)})"
        verdict = "ARBITRAGE CANDIDATE" if self.fires else "no edge after costs"
        return (
            f"{self.group_id}: {verdict}, edge {self.edge:+.5f}/contract, "
            f"fillable {self.fillable:.0f}"
        )


# ---------------------------------------------------------------------------
# Worlds — every one of these is arbitrage-free by construction
# ---------------------------------------------------------------------------


def fair_group(
    n_legs: int = 5,
    days: float = 30.0,
    *,
    seed: int = 0,
    depth: float = 500.0,
    group_id: str = "fair",
) -> NegRiskGroup:
    """A correctly-priced group. **No arbitrage exists here, at any horizon.**

    True probabilities sum to 1; quoted YES prices are those probabilities scaled by the settlement
    discount factor, which is what a market with locked collateral *should* quote (Gebele & Matthes
    2026). The nominal sum is therefore below 1 on purpose — that is carry, not free money, and a
    scanner that fires on it has found the discount rate rather than an edge.
    """
    if n_legs < 2:
        raise ValueError(f"a negRisk group needs at least 2 legs, got {n_legs}")
    rng = random.Random(seed)
    weights = [rng.uniform(0.05, 1.0) for _ in range(n_legs)]
    total = sum(weights)
    probs = [w / total for w in weights]
    d = SettlementTerms(days_to_settlement=days).discount_factor
    legs = tuple(
        Leg(outcome=f"o{i}", price=min(max(p * d, EPS), 1.0 - EPS), depth=depth)
        for i, p in enumerate(probs)
    )
    return NegRiskGroup(group_id, legs, days, legs_are_complete=True,
                        outcomes_are_exhaustive=True)


def truncate_legs(group: NegRiskGroup, *, keep: int, seed: int = 0) -> NegRiskGroup:
    """Show the scanner only part of the group — the 53%-arbitrage artefact.

    ``legs_are_complete`` becomes False because that is the truth of the situation: a paginated
    scan genuinely does not know whether it has every leg. The distortion is in the *knowledge*, and
    modelling it as anything else would let the scanner off the hook.
    """
    if keep >= len(group.legs):
        return group
    rng = random.Random(seed)
    kept = tuple(rng.sample(list(group.legs), keep))
    return replace(group, group_id=f"{group.group_id}+truncated", legs=kept,
                   legs_are_complete=False)


def hide_an_outcome(group: NegRiskGroup) -> NegRiskGroup:
    """Drop a leg *and* the claim of exhaustiveness — the outcome space is no longer covered.

    Distinct from truncation: there the missing leg exists and we failed to fetch it; here the
    listed outcomes genuinely do not span the space, so the buy-every-leg identity is false rather
    than unverified. Both look identical in the price sum, which is the point.
    """
    if len(group.legs) < 3:
        return group
    return replace(group, group_id=f"{group.group_id}+nonexhaustive", legs=group.legs[:-1],
                   outcomes_are_exhaustive=False)


def add_quote_noise(group: NegRiskGroup, *, sd: float = 0.004, seed: int = 0) -> NegRiskGroup:
    """Independent quote noise on each leg. Sums now wobble around the fair value in both
    directions, so any threshold will be crossed sometimes by chance alone."""
    rng = random.Random(seed)
    legs = tuple(
        replace(leg, price=min(max(leg.price + rng.gauss(0.0, sd), EPS), 1.0 - EPS))
        for leg in group.legs
    )
    return replace(group, group_id=f"{group.group_id}+noise", legs=legs)


def obvious_arbitrage(group: NegRiskGroup, *, nominal_sum: float = 0.70) -> NegRiskGroup:
    """**Cost-model-independent positive control.** Scale quotes to a fixed *nominal* sum.

    :func:`inject_arbitrage` bisects on ``effective_yes_cost`` to hit a target post-cost edge, which
    makes it circular as a control: it is defined by the very formula ``scan`` applies, so detecting
    it is guaranteed by construction rather than measured. This one is defined only by the quoted
    prices. A 5-leg group whose quotes sum to 0.70, paying $1 in a week, is riskless profit under
    any cost model anyone would defend — so failing to detect it is a statement about the scanner
    and not about the cost parameters.
    """
    total = group.nominal_sum
    if total <= 0:
        return group
    k = nominal_sum / total
    legs = tuple(
        replace(leg, price=min(max(leg.price * k, EPS), 1.0 - EPS)) for leg in group.legs
    )
    return replace(group, group_id=f"{group.group_id}+obvious", legs=legs)


def marginally_unprofitable(
    group: NegRiskGroup, *, shortfall: float = 0.005, costs: CostModel = CONSERVATIVE
) -> NegRiskGroup:
    """Arbitrage-free **by a hair**: post-cost edge of exactly ``-shortfall``.

    The discriminating null. Every other arbitrage-free world here is rejected by a structural
    refusal — a boolean the world hands the scanner — which tests flag-honouring rather than
    arithmetic. Here the structure is impeccable and *only the cost calculation* stands between the
    scanner and a false fire. If the fee, spread or carry terms are wrong in the profitable
    direction, this world is where it shows.
    """
    target = 1.0 + shortfall

    def cost_at(k: float) -> float:
        return sum(
            costs.effective_yes_cost(min(max(leg.price * k, EPS), 1.0 - EPS),
                                     group.days_to_settlement)
            for leg in group.legs
        )

    lo, hi = 1e-4, 3.0
    if cost_at(hi) < target:
        k = hi
    else:
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if cost_at(mid) < target:
                lo = mid
            else:
                hi = mid
        k = lo
    legs = tuple(
        replace(leg, price=min(max(leg.price * k, EPS), 1.0 - EPS)) for leg in group.legs
    )
    return replace(group, group_id=f"{group.group_id}+marginal", legs=legs)


def believed_complete(group: NegRiskGroup) -> NegRiskGroup:
    """Assert completeness the scanner cannot actually verify — the residual upstream risk.

    ``scan`` refuses a truncated group because the group *tells* it the leg set is incomplete. Real
    pagination does not announce itself. This models the case where completeness determination
    upstream is wrong, and the scanner has no way to know: a leg it never saw cannot be reasoned
    about. Carried as an **exhibit**, not a gate condition, because no arithmetic inside the scanner
    can fix it — the mitigation has to live in leg-set verification, and this measures how much that
    verification is carrying.
    """
    return replace(group, group_id=f"{group.group_id}+believed",
                   legs_are_complete=True, outcomes_are_exhaustive=True)


def thin_the_book(group: NegRiskGroup, *, depth: float = 3.0) -> NegRiskGroup:
    """Real prices, unfillable size. An edge that cannot be executed is not an edge (D1)."""
    legs = tuple(replace(leg, depth=depth) for leg in group.legs)
    return replace(group, group_id=f"{group.group_id}+thin", legs=legs)


def inject_arbitrage(
    group: NegRiskGroup, *, edge: float = 0.03, costs: CostModel = CONSERVATIVE
) -> NegRiskGroup:
    """**Positive control.** Scale prices until a genuine post-cost edge of ``edge`` exists.

    Solved by bisection on a uniform scale factor rather than derived, because
    ``effective_yes_cost`` is monotone in price but not analytically invertible through the fee
    term. A control whose edge is asserted rather than constructed is not a control.
    """
    target = 1.0 - edge

    def cost_at(k: float) -> float:
        return sum(
            costs.effective_yes_cost(min(max(leg.price * k, EPS), 1.0 - EPS),
                                     group.days_to_settlement)
            for leg in group.legs
        )

    lo, hi = 1e-4, 1.0
    if cost_at(hi) <= target:  # already cheap enough
        k = hi
    else:
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if cost_at(mid) > target:
                hi = mid
            else:
                lo = mid
        k = lo
    legs = tuple(
        replace(leg, price=min(max(leg.price * k, EPS), 1.0 - EPS)) for leg in group.legs
    )
    return replace(group, group_id=f"{group.group_id}+arb", legs=legs)


# ---------------------------------------------------------------------------
# The scanners
# ---------------------------------------------------------------------------


def scan_naive(group: NegRiskGroup, *, threshold: float = 0.02) -> ScanResult:
    """**Exhibit, never an instrument.** Sum the quotes, compare to $1, fire on the difference.

    No costs, no carry, no completeness check, no depth. This is the scanner a reasonable person
    writes first, and it is the one that produced a 53% arbitrage out of a pagination artefact. It
    exists so the gate can measure how often it is wrong against worlds known to contain nothing
    (AXIOMS C3's analogue for Class B).
    """
    edge = 1.0 - group.nominal_sum
    fillable = min((leg.depth for leg in group.legs), default=0.0)
    return ScanResult(group.group_id, edge > threshold, edge, fillable, ())


def scan_verified(
    group: NegRiskGroup,
    verification,
    *,
    costs: CostModel = CONSERVATIVE,
    min_fill: float = MIN_FILL,
) -> ScanResult:
    """Scan a group whose structure came from :mod:`kairos.legset`, not from a caller's assertion.

    This is the entry point a real scanner uses. :func:`scan` takes ``legs_are_complete`` and
    ``outcomes_are_exhaustive`` as fields, which is fine inside a null world where the harness knows
    the truth, and is exactly the hole Gate B measured against real data: the ``truncated_believed``
    exhibit fires 1.000 at every horizon precisely because a caller can assert completeness that
    nothing checked.

    The exhaustiveness test is applied **at the measured edge**, because it is a statement about the
    trade rather than the group: if every leg resolves NO the whole stake is lost, so the tolerable
    non-exhaustiveness rate is ``edge / (edge + stake)`` and a bigger edge buys more tolerance.
    That ordering — cost arithmetic first, then exhaustiveness at the resulting edge — is why this
    cannot simply be folded into the dataclass.
    """
    from .legset import LegSetVerification  # local: keeps `structural` importable without network

    if not isinstance(verification, LegSetVerification):
        raise TypeError(f"expected a LegSetVerification, got {type(verification).__name__}")

    fillable = min((leg.depth for leg in group.legs), default=0.0)
    if not verification.complete:
        return ScanResult(group.group_id, False, float("nan"), fillable,
                          tuple(verification.refusals) or ("leg_set_unverified",))

    try:
        total = sum(
            costs.effective_yes_cost(leg.price, group.days_to_settlement) for leg in group.legs
        )
    except Exception:  # noqa: BLE001 - a refusing cost model is a failed check, not a crash
        return ScanResult(group.group_id, False, float("nan"), fillable, ("cost_model_refused",))

    edge = 1.0 - total
    stake = max(total, EPS)
    refusals: list[str] = []
    if edge > 0.0 and not verification.exhaustive(edge=edge, stake=stake):
        refusals.append("exhaustiveness_risk_exceeds_edge")
    if edge > 0.0 and fillable < min_fill:
        refusals.append("insufficient_depth")
    fires = edge > 0.0 and not refusals
    return ScanResult(group.group_id, fires, edge, fillable, tuple(refusals))


def scan(
    group: NegRiskGroup,
    *,
    costs: CostModel = CONSERVATIVE,
    min_fill: float = MIN_FILL,
) -> ScanResult:
    """The disciplined scanner. Refuses by default; fires only on a fillable post-cost edge.

    Order of operations matters and is deliberate:

    1. **Refuse on unverified structure first.** An incomplete leg set or an unverified exhaustive
       claim makes the payoff identity unprovable, and an unprovable identity cannot be rescued by
       arithmetic on the prices. Fail closed (A6).
    2. **All-in cost against a nominal $1.** ``effective_yes_cost`` already includes spread, fee and
       carry, so the payoff is *not* discounted again (C7).
    3. **Fillability last.** An edge below ``min_fill`` contracts is reported as no-fire, because an
       unfillable edge is not an edge (D1).
    """
    refusals: list[str] = []
    if not group.legs_are_complete:
        refusals.append("incomplete_leg_set")
    if not group.outcomes_are_exhaustive:
        refusals.append("exhaustiveness_unverified")
    if len(group.legs) < 2:
        refusals.append("degenerate_group")

    fillable = min((leg.depth for leg in group.legs), default=0.0)
    try:
        total = sum(
            costs.effective_yes_cost(leg.price, group.days_to_settlement) for leg in group.legs
        )
    except Exception:  # noqa: BLE001 - a refusing cost model is a failed check, not a crash
        return ScanResult(group.group_id, False, float("nan"), fillable,
                          tuple(refusals) + ("cost_model_refused",))

    edge = 1.0 - total
    fires = (not refusals) and edge > 0.0 and fillable >= min_fill
    if not refusals and edge > 0.0 and fillable < min_fill:
        refusals.append("insufficient_depth")
    return ScanResult(group.group_id, fires, edge, fillable, tuple(refusals))
