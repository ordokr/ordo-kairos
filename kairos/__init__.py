"""Ordo Kairos - a decision core for event-contract markets.

Not a trading bot. An instrument for deciding, on measured evidence and without risking capital,
whether one is worth building. See ``SPEC.md`` for the evidence and the kill rule.

The pipeline, in causal order - information first, sizing last::

    nullworld    Gate 0: can this pipeline correctly find NOTHING?   <- ranks above everything
    inference    the primary test: paired score differences, cluster-robust
    baseline     q_raw -> q_ref: REJECTED (Look 3). Settlement model retained for Class B
    score        proper scores, trial ledger, deflated Sharpe (secondary)
    economics    edge x capacity x frequency - costs; effective sample size (planning only)
    costs        what an edge must clear before it is an edge
    calibration  market-anchored blending + isotonic recalibration
    gate         the abstention gate; default action is ABSTAIN
    sizing       (p, q_ref) -> stake; governs the wealth path, cannot create edge
    state        refuses to write runtime state anywhere publish-eligible

Sizing sits at the bottom on purpose. It determines growth, drawdown and ruin *given* an edge; it
cannot manufacture one. Establishing that an edge exists is the job of `baseline` + `score`, and
establishing that it is worth having is the job of `economics`.
"""

from __future__ import annotations

# ``LogitRecalibration`` and ``MarketBaseline`` are deliberately NOT re-exported. Look 3 rejected
# logit recalibration of the market price on 983 disjoint out-of-sample events, so it must not be
# reachable from the package's public surface — but the code stays importable from
# ``kairos.baseline`` because ``gate1.py`` needs it to reproduce Gates 1-2a and Looks 1-3. A result
# whose code has been deleted is an assertion, not a result. See ``docs/LOOK3-RESULTS.md`` and the
# amendment recorded in ``docs/PROTOCOL.md``.
from .baseline import BaselineError, SettlementTerms
from .calibration import BlendSpace, IsotonicCalibrator, ReliabilityReport, blend, reliability
from .costs import CONSERVATIVE, CostError, CostModel
from .economics import (
    EconomicsError,
    StrategyEconomics,
    effective_sample_size,
    rank_strategies,
    sufficient_evidence,
)
from .gate import Check, GateConfig, GateDecision, MarketSnapshot, evaluate
from .inference import (
    InferenceError,
    SuperiorityResult,
    cluster_bootstrap_test,
    paired_deltas,
    superiority_test,
    wild_cluster_bootstrap_test,
)
from .nullworld import GateReport, World, WorldReport, run_gate0
from .score import (
    Trial,
    TrialLedger,
    brier_score,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    log_score,
    min_backtest_length,
    skill_score,
)
from .sizing import (
    Clamp,
    ClampReason,
    RiskLimits,
    Side,
    Stake,
    growth_rate,
    kelly_fraction,
    size_position,
)
from .state import StateLocationError, state_dir

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # gate 0 - null-world falsification
    "run_gate0",
    "GateReport",
    "WorldReport",
    "World",
    # inference - the primary test
    "superiority_test",
    "paired_deltas",
    "cluster_bootstrap_test",
    "wild_cluster_bootstrap_test",
    "SuperiorityResult",
    "InferenceError",
    # baseline — q_ref is REJECTED (Look 3). Only the settlement model survives, and it survives
    # because Class B uses it, not because Class A rescued it.
    "SettlementTerms",
    "BaselineError",
    # economics
    "StrategyEconomics",
    "rank_strategies",
    "effective_sample_size",
    "sufficient_evidence",
    "EconomicsError",
    # costs
    "CostModel",
    "CostError",
    "CONSERVATIVE",
    # calibration
    "blend",
    "BlendSpace",
    "IsotonicCalibrator",
    "reliability",
    "ReliabilityReport",
    # gate
    "evaluate",
    "GateConfig",
    "GateDecision",
    "MarketSnapshot",
    "Check",
    # sizing
    "size_position",
    "kelly_fraction",
    "growth_rate",
    "Side",
    "Stake",
    "RiskLimits",
    "Clamp",
    "ClampReason",
    # score
    "log_score",
    "brier_score",
    "skill_score",
    "TrialLedger",
    "Trial",
    "expected_max_sharpe",
    "deflated_sharpe_ratio",
    "min_backtest_length",
    # state
    "state_dir",
    "StateLocationError",
]
