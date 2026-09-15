"""The abstention gate. Default action is ABSTAIN; every check must pass to trade.

Selectivity, not speed, is where the accuracy lives. Kota 2026 (arXiv 2605.30802) evaluated
multi-agent LLM oracles on 1,189 resolved Kalshi questions and found that auto-resolving **only the
unanimous, high-confidence** subset yields **97.87% accuracy on 47% of the dataset** - while forcing
an answer on everything drags accuracy to 83%. The same study found **deliberative consensus
collapses to ~76%, below every single-model baseline**, because "confidently wrong models flip
correct ones". Hence: independent aggregation, unanimity required, no debate.

Two more checks encode findings that are cheap to ignore and expensive to learn:

- **Excluded contract classes.** Dai et al. 2026 (arXiv 2606.31675): after Polymarket launched
  5-minute Bitcoin contracts, settlement-time spot order flow spiked and reversed - "manipulators
  capture a large amount of profit, mostly from retail". The effect is **absent in 15-minute
  contracts**. Short price-settled horizons are a farm, so they are refused structurally.
- **Depth.** Cheng et al. 2026 (arXiv 2605.00864): 76.9% of Polymarket combinatorial opportunities
  were capped at ~14.8 shares. An edge you cannot fill at size is not an edge, and a backtest that
  ignores depth will report one anyway.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .costs import CostModel

__all__ = ["Check", "GateDecision", "MarketSnapshot", "GateConfig", "evaluate"]


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class MarketSnapshot:
    """Everything the gate needs to know about one contract.

    Attributes:
        settles_on_tradeable_price: Whether resolution reads a price a participant can move by
            trading the underlying. This is the property that makes a contract manipulable; the
            5-minute horizon is a symptom of it, not the disease.
        external_manipulation_analysis: A human-written, externally grounded analysis of who could
            move this settlement reference and at what cost **to them**, including positions we
            cannot see. The only thing that lets a price-settled market through. Deliberately a
            string rather than a number: if it were computable from the fields above, the refusal
            it bypasses would not be needed (CORRECTIONS item 11, AXIOMS D4, A6).
        settlement_manipulation_cost: Dollars required to move the settlement reference enough to
            flip the outcome. ``None`` means unmeasured, and the gate fails closed on it.
    """

    market_id: str
    mid: float
    days_to_resolution: float
    depth_contracts: float
    settles_on_tradeable_price: bool = False
    dispute_prone: bool = False
    settlement_manipulation_cost: float | None = None
    external_manipulation_analysis: str | None = None


@dataclass(frozen=True)
class GateConfig:
    """Thresholds. Each one is a trial-ledger entry when changed.

    Attributes:
        min_edge_lcb: The lower confidence bound of the edge must exceed this, *after* costs. Not
            the point estimate - Baker & McHale 2013 is explicit that parameter uncertainty must
            shrink the decision, not just the stake.
        edge_z: Standard errors used to form that lower bound.
        min_horizon_days: Refuses very short horizons outright (Dai et al. 2026).
        require_unanimity: All ensemble members must agree on the side (Kota 2026).
        min_members: Minimum ensemble size for unanimity to mean anything.
        min_depth_contracts: Fillable size floor (Cheng et al. 2026).
        allow_dispute_prone: Wen et al. 2026 (arXiv 2604.15674) measure **$972M** of Polymarket
            volume in disputed events and find LLMs *cannot* predict which markets will be disputed
            in advance. Default is to refuse flagged rule sets rather than price the risk.
    """

    min_edge_lcb: float = 0.02
    edge_z: float = 1.0
    min_horizon_days: float = 1.0
    require_unanimity: bool = True
    min_members: int = 3
    min_depth_contracts: float = 100.0
    allow_dispute_prone: bool = False
    allow_price_settled_short_horizon: bool = False


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    checks: tuple[Check, ...] = field(default_factory=tuple)

    @property
    def failures(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if not c.passed)

    def explain(self) -> str:
        verdict = "TRADE" if self.allowed else "ABSTAIN"
        lines = [f"{verdict} ({len(self.failures)}/{len(self.checks)} checks failed)"]
        lines.extend(
            f"  [{'ok ' if c.passed else 'FAIL'}] {c.name}: {c.detail}" for c in self.checks
        )
        return "\n".join(lines)


def evaluate(
    p: float,
    market: MarketSnapshot,
    *,
    costs: CostModel,
    config: GateConfig,
    member_forecasts: Sequence[float] = (),
    p_stderr: float = 0.0,
    intended_contracts: float = 0.0,
) -> GateDecision:
    """Run every check. Returns ``allowed=True`` only if all of them pass.

    Args:
        p: Calibrated probability of YES.
        market: The contract.
        costs: Cost model - edge is measured after costs, never before.
        config: Thresholds.
        member_forecasts: Individual ensemble member probabilities, for the unanimity check.
            Independent forecasts only; see the module docstring on why debate is excluded.
        p_stderr: Standard error of ``p``, for the lower confidence bound.
        intended_contracts: Size we mean to trade, checked against available depth.
    """
    checks: list[Check] = []

    in_band = costs.price_in_band(market.mid)
    checks.append(
        Check(
            "price_band",
            in_band,
            f"mid {market.mid:.4f} vs band "
            f"[{costs.min_price:.2f}, {costs.max_price:.2f}] (longshot exclusion)",
        )
    )

    short_price_settled = (
        market.settles_on_tradeable_price
        and market.days_to_resolution * 24 * 60 < 15.0
        and not config.allow_price_settled_short_horizon
    )
    checks.append(
        Check(
            "settlement_manipulation",
            not short_price_settled,
            "sub-15-minute price-settled contract: retail is the counterparty to manipulators "
            "(Dai et al. 2026)"
            if short_price_settled
            else "contract class permitted",
        )
    )

    # The general rule the 5-minute BTC case is only an instance of: never trade a market whose
    # resolution a participant could economically move. Fails closed when the cost of manipulation
    # has not been measured, because "we didn't check" is not evidence of safety (AXIOMS A6, D4).
    #
    # CORRECTIONS item 11, resolved 2026-09-09: **unconditional fail-closed.**
    #
    # This check used to pass when the measured cost of moving the settlement reference exceeded a
    # multiple of *our* intended size. That comparison was withdrawn because it is not a model of
    # manipulation at all: a manipulator's payoff is not bounded by our position. It can include
    # prediction-market positions on other venues, positions in the underlying, and positions held
    # by parties we cannot see. Scaling a threshold to our own size answers a question nobody asked,
    # and dressing an unmeasured quantity in a safety factor is precisely what A6 forbids.
    #
    # So there is no arithmetic here any more. A market whose resolution reads a tradeable price is
    # refused unless an **externally grounded manipulation analysis** is attached to it. That escape
    # is deliberately a string a human must write and sign off, not a number a pipeline can compute:
    # if it could be computed from fields we already have, the refusal would not be needed (D4).
    if market.settles_on_tradeable_price:
        analysis = (market.external_manipulation_analysis or "").strip()
        manipulability_ok = bool(analysis)
        if manipulability_ok:
            manip_detail = f"externally grounded manipulation analysis on file: {analysis[:80]}"
        else:
            cost = market.settlement_manipulation_cost
            observed = (
                f" (observed cost to move it ${cost:,.0f}, recorded but NOT a pass condition)"
                if cost is not None else ""
            )
            manip_detail = (
                "settles on a tradeable price and no externally grounded manipulation analysis "
                f"is attached - failing closed{observed}"
            )
    else:
        manipulability_ok = True
        manip_detail = "resolution does not read a tradeable price"
    checks.append(Check("resolution_manipulability", manipulability_ok, manip_detail))

    horizon_ok = market.days_to_resolution >= config.min_horizon_days
    checks.append(
        Check(
            "horizon",
            horizon_ok,
            f"{market.days_to_resolution:.3f}d vs min {config.min_horizon_days:.3f}d",
        )
    )

    dispute_ok = config.allow_dispute_prone or not market.dispute_prone
    checks.append(
        Check(
            "resolution_risk",
            dispute_ok,
            "flagged dispute-prone rule set (Wen et al. 2026)"
            if not dispute_ok
            else "rule set not flagged",
        )
    )

    depth_ok = market.depth_contracts >= max(config.min_depth_contracts, intended_contracts)
    checks.append(
        Check(
            "depth",
            depth_ok,
            f"{market.depth_contracts:.1f} available vs "
            f"{max(config.min_depth_contracts, intended_contracts):.1f} required",
        )
    )

    if config.require_unanimity:
        n = len(member_forecasts)
        if n < config.min_members:
            unanimous = False
            detail = f"{n} members, need >= {config.min_members}"
        else:
            above = sum(1 for m in member_forecasts if m > market.mid)
            below = sum(1 for m in member_forecasts if m < market.mid)
            unanimous = above == n or below == n
            detail = (
                f"{above} above / {below} below market mid across {n} members"
                + ("" if unanimous else " - not unanimous")
            )
        checks.append(Check("ensemble_unanimity", unanimous, detail))

    shrink = config.edge_z * p_stderr
    try:
        yes_cost = costs.effective_yes_cost(market.mid, market.days_to_resolution)
        no_cost = costs.effective_no_cost(market.mid, market.days_to_resolution)
        best_edge = max((p - shrink) - yes_cost, (1.0 - p - shrink) - no_cost)
        edge_ok = best_edge >= config.min_edge_lcb
        detail = (
            f"best post-cost edge LCB {best_edge:+.4f} vs threshold "
            f"{config.min_edge_lcb:+.4f} (yes cost {yes_cost:.4f}, no cost {no_cost:.4f}, "
            f"shrink {shrink:.4f})"
        )
    except Exception as exc:  # noqa: BLE001 - a refusing cost model is a failed check, not a crash
        edge_ok = False
        detail = f"cost model refused: {exc}"
    checks.append(Check("edge_after_costs", edge_ok, detail))

    return GateDecision(allowed=all(c.passed for c in checks), checks=tuple(checks))
