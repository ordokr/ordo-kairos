"""Sizing: the map ``(p, q_ref) -> stake``.

**What this module is and is not the cause of.** Sizing governs the *wealth path* conditional on a
genuine edge - growth rate, drawdown, and probability of ruin. It cannot manufacture positive
expected value from a forecast that carries no information the market did not already have. The
causal order runs::

    incremental information over q_ref  ->  economic edge after friction  ->  sizing  ->  wealth path

and never sizing -> edge. An earlier version of this file called sizing "the principal cause of
PnL"; that was an inversion. Edge is the material cause (there must be something to size); sizing is
the formal cause of the wealth path. See :mod:`kairos.baseline` and :mod:`kairos.score`, which
establish whether there is anything here to size at all - they rank *above* this module, not below.

The evidence for taking sizing seriously anyway:

- **Gu et al. 2026** (arXiv 2607.06166) prove that a "proper" betting rule depending only on the
  forecast ``p`` and the market price ``q`` earns positive expected profit **whenever ``p`` beats
  ``q`` under a strictly proper scoring rule and liquidity suffices** - and that it is *essentially
  the only* strategy with that guarantee. Note the antecedent: the guarantee is conditional on
  having an information edge, which is precisely the point above. For the logarithmic scoring rule
  the proper bet is the Kelly bet, which is what this module implements. Treat the paper's reported
  +80.33% one-month live Kalshi ROI as a **hypothesis source, not evidence**: zero citations, one
  month, one deployment.
- **Walsh & Joshi 2023** (Machine Learning with Applications, DOI 10.1016/j.mlwa.2024.100539)
  report that selecting on calibration rather than accuracy raises sports-betting ROI. **Use the
  direction, not the magnitude.** The arXiv version (2303.06021) reports +110.42% vs +2.98%; the
  journal version reports +34.69% vs -35.17%; and a 2025 corrigendum
  (DOI 10.1016/j.mlwa.2025.100627) records errors "discovered in the original implementation"
  during modularisation and unit testing. Three versions, three magnitudes, one correction - so the
  effect size is not a foundation. The *direction* is independently supported by Hubacek et al.
  2019 (Int. J. Forecasting) and Wunderlich et al. 2026 (Int. J. Forecasting), both of which find
  that models optimised against market prices beat accuracy-optimised ones out of sample.
- **Galekwa et al. 2026** (IEEE Access, DOI 10.1109/access.2026.3669489): betting funds with
  genuinely accurate models still failed, for want of sizing discipline. Uncertainty-adjusted
  staking cut ruin probability from **78% to under 2%** while keeping **85%** of growth.
- **Baker & McHale 2013** (Decision Analysis, DOI 10.1287/deca.2013.0271): under parameter
  uncertainty the stake must be *shrunk*; shrunken Kelly beats raw Kelly out of sample.
- **MacLean et al. 2011**: full Kelly is short-term brutal - "a sequence of bad scenarios can lead
  to very poor final wealth outcomes" no matter how good the edge.
- **Uhrin et al. 2021** (IMA J. Management Math.): adaptive fractional Kelly is the strategy that
  holds up across sports and datasets.

Three shrinkages compose here, deliberately:

1. **Conservative belief.** Size on the confidence bound of ``p`` facing the bet, not on ``p``.
2. **Fractional Kelly.** Multiply by ``kelly_fraction`` (default 0.25).
3. **Hard caps.** Per-position and gross-exposure clamps that can only ever *reduce* a stake.

Plus a drawdown kill switch that refuses everything. The default action is ABSTAIN.

Note on scope: only the log-score (Kelly) member of Gu et al.'s proper-betting family is derived
and implemented here, because it is the member this module can prove for itself. The general
strictly-proper-scoring-rule family should be cross-checked against the paper before any live use.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from .costs import CostModel

__all__ = [
    "Side",
    "ClampReason",
    "Clamp",
    "RiskLimits",
    "Stake",
    "kelly_fraction",
    "size_position",
]


class Side(str, Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class ClampReason(str, Enum):
    """Why a stake was reduced. Every reduction is recorded so sizing is explainable."""

    FRACTIONAL_KELLY = "fractional_kelly"
    MAX_POSITION = "max_position"
    GROSS_EXPOSURE = "gross_exposure"
    DRAWDOWN_HALT = "drawdown_halt"
    NEGATIVE_EDGE = "negative_edge"
    PRICE_OUT_OF_BAND = "price_out_of_band"
    COST_EXCEEDS_PAYOFF = "cost_exceeds_payoff"


@dataclass(frozen=True)
class Clamp:
    reason: ClampReason
    before: float
    after: float

    def __post_init__(self) -> None:
        if self.after > self.before + 1e-12:
            raise ValueError(
                f"a clamp may only reduce a stake: {self.reason.value} "
                f"went {self.before!r} -> {self.after!r}"
            )


@dataclass(frozen=True)
class RiskLimits:
    """Hard bounds on a single decision and on the book.

    Attributes:
        kelly_fraction: Fractional-Kelly multiplier. 0.25 is the conventional quarter-Kelly and is
            supported by Uhrin et al. 2021 and MacLean et al. 2011. Values above 1.0 are refused -
            over-betting Kelly reduces growth *and* raises variance simultaneously
            (Johnstone 2022, Australian J. Management).
        edge_z: Standard deviations of shrinkage applied to the belief before sizing. 1.0 is
            deliberately mild; raise it when the forecast's uncertainty is poorly characterised.
        max_position_fraction: Cap on bankroll committed to one contract.
        max_gross_exposure: Cap on total bankroll committed across open positions.
        max_drawdown: Drawdown from high-water mark at which the book halts entirely.
    """

    kelly_fraction: float = 0.25
    edge_z: float = 1.0
    max_position_fraction: float = 0.02
    max_gross_exposure: float = 0.50
    max_drawdown: float = 0.20

    def __post_init__(self) -> None:
        if not 0.0 < self.kelly_fraction <= 1.0:
            raise ValueError(
                f"kelly_fraction must lie in (0, 1]; over-betting Kelly lowers growth and raises "
                f"variance at the same time. Got {self.kelly_fraction!r}"
            )
        if self.edge_z < 0.0:
            raise ValueError(f"edge_z must be non-negative, got {self.edge_z!r}")
        for name in ("max_position_fraction", "max_gross_exposure", "max_drawdown"):
            v = getattr(self, name)
            if not 0.0 < v <= 1.0:
                raise ValueError(f"{name} must lie in (0, 1], got {v!r}")
        if self.max_position_fraction > self.max_gross_exposure:
            raise ValueError(
                f"max_position_fraction ({self.max_position_fraction!r}) exceeds "
                f"max_gross_exposure ({self.max_gross_exposure!r}); one position could fill the book"
            )


@dataclass(frozen=True)
class Stake:
    """A sizing decision and the full audit trail that produced it."""

    side: Side
    fraction: float
    raw_kelly: float = 0.0
    belief: float = 0.0
    belief_shrunk: float = 0.0
    effective_cost: float = 0.0
    edge: float = 0.0
    clamps: tuple[Clamp, ...] = field(default_factory=tuple)
    reason: str = ""

    @property
    def abstained(self) -> bool:
        return self.side is Side.ABSTAIN or self.fraction <= 0.0

    def explain(self) -> str:
        head = (
            f"{self.side.value.upper()} {self.fraction:.4%} of bankroll "
            f"(raw Kelly {self.raw_kelly:.4%}, belief {self.belief:.4f} -> "
            f"{self.belief_shrunk:.4f}, cost {self.effective_cost:.4f}, edge {self.edge:+.4f})"
        )
        if self.abstained:
            head = f"ABSTAIN - {self.reason}"
        trail = "".join(
            f"\n  clamped by {c.reason.value}: {c.before:.4%} -> {c.after:.4%}" for c in self.clamps
        )
        return head + trail


def kelly_fraction(belief: float, cost: float) -> float:
    """Fraction of bankroll to spend on a binary contract paying $1.

    Pay ``cost`` per contract, receive 1 with probability ``belief``. Net odds are
    ``b = (1 - cost) / cost``, so the Kelly stake is::

        f* = (belief * b - (1 - belief)) / b = (belief - cost) / (1 - cost)

    Returns 0.0 when the bet is not favourable. Raises when ``cost >= 1``, since a contract costing
    a dollar or more can never be +EV against a dollar payoff.
    """
    if not 0.0 <= belief <= 1.0:
        raise ValueError(f"belief must lie in [0, 1], got {belief!r}")
    if cost >= 1.0:
        raise ValueError(
            f"cost {cost!r} >= 1.0: the contract costs at least its maximum payoff, so no belief "
            f"makes it +EV"
        )
    if cost <= 0.0:
        raise ValueError(f"cost must be positive, got {cost!r}")
    if belief <= cost:
        return 0.0
    return (belief - cost) / (1.0 - cost)


def size_position(
    p: float,
    mid: float,
    *,
    costs: CostModel,
    limits: RiskLimits,
    days_to_resolution: float,
    p_stderr: float = 0.0,
    gross_exposure_used: float = 0.0,
    drawdown: float = 0.0,
    maker: bool = False,
) -> Stake:
    """Convert a calibrated probability into a bankroll fraction, or abstain.

    Args:
        p: Calibrated probability that the contract resolves YES. Must already have been through
            :mod:`kairos.calibration` - a raw model or LLM output does not belong here.
        mid: Market mid price, which is also the market's own probability estimate.
        costs: All-in cost model. Edge is measured against effective cost, never against ``mid``.
        limits: Risk bounds.
        days_to_resolution: Horizon, for the settlement-wedge carry cost.
        p_stderr: Standard error of ``p``. Drives the conservative shrinkage; leaving it at 0.0
            asserts the forecast is exact, which it is not.
        gross_exposure_used: Bankroll fraction already committed across open positions.
        drawdown: Current drawdown from the high-water mark, as a positive fraction.
        maker: Whether the order rests rather than crosses.

    Returns:
        A :class:`Stake`. ``Side.ABSTAIN`` with fraction 0.0 is a normal, expected outcome and is
        the default whenever any condition fails.
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p must lie in [0, 1], got {p!r}")
    if p_stderr < 0.0:
        raise ValueError(f"p_stderr must be non-negative, got {p_stderr!r}")
    if drawdown < 0.0:
        raise ValueError(f"drawdown must be non-negative, got {drawdown!r}")

    if drawdown >= limits.max_drawdown:
        return Stake(
            side=Side.ABSTAIN,
            fraction=0.0,
            clamps=(Clamp(ClampReason.DRAWDOWN_HALT, 0.0, 0.0),),
            reason=(
                f"drawdown {drawdown:.2%} at or beyond halt threshold "
                f"{limits.max_drawdown:.2%}; book is closed"
            ),
        )

    if not costs.price_in_band(mid):
        return Stake(
            side=Side.ABSTAIN,
            fraction=0.0,
            clamps=(Clamp(ClampReason.PRICE_OUT_OF_BAND, 0.0, 0.0),),
            reason=(
                f"mid {mid:.4f} outside tradeable band "
                f"[{costs.min_price:.2f}, {costs.max_price:.2f}] - longshot exclusion"
            ),
        )

    headroom = max(0.0, limits.max_gross_exposure - gross_exposure_used)
    if headroom <= 0.0:
        return Stake(
            side=Side.ABSTAIN,
            fraction=0.0,
            clamps=(Clamp(ClampReason.GROSS_EXPOSURE, 0.0, 0.0),),
            reason=(
                f"gross exposure {gross_exposure_used:.2%} has consumed the "
                f"{limits.max_gross_exposure:.2%} budget"
            ),
        )

    shrink = limits.edge_z * p_stderr
    # Shrink toward the side we are NOT taking: conservative in the direction of the bet.
    yes_belief = max(0.0, p - shrink)
    no_belief = max(0.0, (1.0 - p) - shrink)

    try:
        yes_cost = costs.effective_yes_cost(mid, days_to_resolution, maker=maker)
        no_cost = costs.effective_no_cost(mid, days_to_resolution, maker=maker)
    except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the caller
        return Stake(side=Side.ABSTAIN, fraction=0.0, reason=f"cost model refused: {exc}")

    candidates: list[tuple[Side, float, float, float, float]] = []
    for side, belief, raw_belief, cost in (
        (Side.YES, yes_belief, p, yes_cost),
        (Side.NO, no_belief, 1.0 - p, no_cost),
    ):
        if cost >= 1.0:
            continue
        f_raw = kelly_fraction(belief, cost)
        if f_raw > 0.0:
            candidates.append((side, f_raw, raw_belief, belief, cost))

    if not candidates:
        best_gap = max(yes_belief - yes_cost, no_belief - no_cost)
        cheapest = min(yes_cost, no_cost)
        reason = (
            f"cost exceeds payoff on both sides (min effective cost {cheapest:.4f})"
            if cheapest >= 1.0
            else (
                f"no side clears cost after shrinkage: best shrunk edge {best_gap:+.4f} "
                f"(p={p:.4f}, stderr={p_stderr:.4f}, mid={mid:.4f}, "
                f"yes cost {yes_cost:.4f}, no cost {no_cost:.4f})"
            )
        )
        clamp = (
            ClampReason.COST_EXCEEDS_PAYOFF if cheapest >= 1.0 else ClampReason.NEGATIVE_EDGE
        )
        return Stake(
            side=Side.ABSTAIN,
            fraction=0.0,
            belief=p,
            effective_cost=cheapest,
            edge=best_gap,
            clamps=(Clamp(clamp, 0.0, 0.0),),
            reason=reason,
        )

    # Both sides can only be favourable if the two effective costs sum below 1.0, which means the
    # quoted market is inside our cost band on both legs. Take the larger stake; never both.
    side, raw, raw_belief, shrunk_belief, cost = max(candidates, key=lambda c: c[1])

    clamps: list[Clamp] = []
    f = raw

    stepped = f * limits.kelly_fraction
    clamps.append(Clamp(ClampReason.FRACTIONAL_KELLY, f, stepped))
    f = stepped

    if f > limits.max_position_fraction:
        clamps.append(Clamp(ClampReason.MAX_POSITION, f, limits.max_position_fraction))
        f = limits.max_position_fraction

    if f > headroom:
        clamps.append(Clamp(ClampReason.GROSS_EXPOSURE, f, headroom))
        f = headroom

    return Stake(
        side=side,
        fraction=f,
        raw_kelly=raw,
        belief=raw_belief,
        belief_shrunk=shrunk_belief,
        effective_cost=cost,
        edge=shrunk_belief - cost,
        clamps=tuple(clamps),
        reason="sized",
    )


def growth_rate(fraction: float, belief: float, cost: float) -> float:
    """Expected log growth per bet - the quantity Kelly maximises.

    Useful as an independent check: sizing at :func:`kelly_fraction` should maximise this, and any
    stake above it should show *lower* growth than the optimum. That asymmetry is what makes
    over-betting strictly worse than under-betting, and it is worth asserting in tests rather than
    trusting.
    """
    if not 0.0 <= fraction < 1.0:
        raise ValueError(f"fraction must lie in [0, 1), got {fraction!r}")
    if not 0.0 < cost < 1.0:
        raise ValueError(f"cost must lie in (0, 1), got {cost!r}")
    win_mult = 1.0 + fraction * (1.0 - cost) / cost
    lose_mult = 1.0 - fraction
    if win_mult <= 0.0 or lose_mult <= 0.0:
        return -math.inf
    return belief * math.log(win_mult) + (1.0 - belief) * math.log(lose_mult)
