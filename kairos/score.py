"""The go/no-go metric, and the machinery that stops it lying.

**Score against the market, not against zero.** A forecaster that looks excellent in isolation may
carry no information the price did not already have. Every score here is reported as a *skill
score* relative to the market price baseline: positive means the model beat the market, which is
the only comparison that pays.

**Never select on ROI.** Wunderlich et al. 2020 (Int. J. Forecasting,
DOI 10.1016/j.ijforecast.2019.08.009) demonstrate - theoretically, in simulation, and on three
sports datasets - that positive betting returns arise "systematically or randomly in the absence of
a superior model accuracy". ROI is a valid measure of profitability and an invalid measure of skill.
It is reported here and never selected on.

**Count the trials.** Bailey & López de Prado's results are brutal and specific: after only **7**
strategy configurations you should expect to find a 2-year backtest with annualised Sharpe above
1.0 when the true Sharpe is **zero** (arXiv/SSRN 2308682). Wiecki et al. 2016 (J. Investing) checked
this against 888 real algorithms with live out-of-sample records and found backtest Sharpe predicts
out-of-sample performance with **R^2 < 0.025**. So the ledger is not bookkeeping - it is the input
to the deflation that makes any Sharpe claim admissible.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any, Sequence

__all__ = [
    "log_score",
    "brier_score",
    "skill_score",
    "Trial",
    "TrialLedger",
    "expected_max_sharpe",
    "deflated_sharpe_ratio",
    "min_backtest_length",
]

_EPS = 1e-15
_EULER_MASCHERONI = 0.5772156649015329
_NORMAL = NormalDist()


def _validate_pairs(forecasts: Sequence[float], outcomes: Sequence[float]) -> None:
    if len(forecasts) != len(outcomes):
        raise ValueError(
            f"forecasts and outcomes must be the same length, got "
            f"{len(forecasts)} and {len(outcomes)}"
        )
    if not forecasts:
        raise ValueError("cannot score zero observations")
    for f in forecasts:
        if not 0.0 <= f <= 1.0:
            raise ValueError(f"forecast {f!r} outside [0, 1]")
    for o in outcomes:
        if o not in (0, 1, 0.0, 1.0):
            raise ValueError(f"outcome {o!r} must be 0 or 1")


def log_score_pointwise(
    forecasts: Sequence[float], outcomes: Sequence[float]
) -> list[float]:
    """Per-observation negative log likelihood. Lower is better. Strictly proper.

    Forecasts are clipped away from {0, 1} so a single confident miss costs a large but finite
    amount rather than infinity - an infinite score would make every comparison degenerate.

    The pointwise form is what :mod:`kairos.inference` needs: the primary hypothesis is about the
    *paired sequence* of score differences, and collapsing to a mean before testing throws away the
    dependence structure the test has to respect.
    """
    _validate_pairs(forecasts, outcomes)
    out: list[float] = []
    for f, o in zip(forecasts, outcomes):
        p = min(max(f, _EPS), 1.0 - _EPS)
        out.append(-math.log(p) if o else -math.log(1.0 - p))
    return out


def brier_score_pointwise(
    forecasts: Sequence[float], outcomes: Sequence[float]
) -> list[float]:
    """Per-observation squared error. Lower is better. Strictly proper."""
    _validate_pairs(forecasts, outcomes)
    return [(f - o) ** 2 for f, o in zip(forecasts, outcomes)]


def log_score(forecasts: Sequence[float], outcomes: Sequence[float]) -> float:
    """Mean negative log likelihood. Lower is better. Strictly proper."""
    pointwise = log_score_pointwise(forecasts, outcomes)
    return sum(pointwise) / len(pointwise)


def brier_score(forecasts: Sequence[float], outcomes: Sequence[float]) -> float:
    """Mean squared error of the probability. Lower is better. Strictly proper."""
    pointwise = brier_score_pointwise(forecasts, outcomes)
    return sum(pointwise) / len(pointwise)


def skill_score(
    forecasts: Sequence[float],
    outcomes: Sequence[float],
    baseline: Sequence[float],
    scorer=log_score,
) -> float:
    """Fractional improvement over a baseline. **Positive means you beat the market.**

    ``1 - score(forecasts) / score(baseline)``. Pass the market price as ``baseline``; that is the
    comparison the SPEC gate is written against, and the one AIA Forecaster (arXiv 2511.07678)
    fails on liquid prediction markets while still matching superforecasters in isolation.
    """
    if len(baseline) != len(forecasts):
        raise ValueError(
            f"baseline length {len(baseline)} != forecasts length {len(forecasts)}"
        )
    base = scorer(baseline, outcomes)
    if base <= 0.0:
        raise ValueError(
            f"baseline score {base!r} is non-positive; skill is undefined against a perfect "
            f"baseline"
        )
    return 1.0 - scorer(forecasts, outcomes) / base


@dataclass(frozen=True)
class Trial:
    """One configuration that was tried. Written before its result is read."""

    trial_id: str
    config: dict[str, Any]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    note: str = ""


class TrialLedger:
    """Append-only record of every configuration tried.

    The deflated Sharpe ratio is a function of how many things you tried. An unrecorded trial does
    not merely go unmentioned - it inflates every subsequent significance claim. Hence append-only,
    and hence :meth:`record` is meant to be called *before* the result is looked at.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._trials: list[Trial] = []
        if path is not None and path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    self._trials.append(Trial(**json.loads(line)))

    def record(self, trial_id: str, config: dict[str, Any], note: str = "") -> Trial:
        """Append a trial. Duplicate ids are refused so the count cannot be quietly reset."""
        if any(t.trial_id == trial_id for t in self._trials):
            raise ValueError(
                f"trial_id {trial_id!r} already recorded; re-using an id would undercount trials "
                f"and inflate the deflated Sharpe"
            )
        trial = Trial(trial_id=trial_id, config=config, note=note)
        self._trials.append(trial)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(trial), sort_keys=True) + "\n")
        return trial

    def __len__(self) -> int:
        return len(self._trials)

    @property
    def trials(self) -> tuple[Trial, ...]:
        return tuple(self._trials)


def expected_max_sharpe(n_trials: int, sharpe_stdev: float = 1.0) -> float:
    """Expected maximum Sharpe across ``n_trials`` when the true Sharpe of every trial is zero.

    The Bailey/López de Prado order-statistic approximation::

        E[max SR] ~ sigma * [ (1 - g) * Z^-1(1 - 1/N) + g * Z^-1(1 - 1/(N*e)) ]

    with ``g`` the Euler-Mascheroni constant. This is the hurdle a candidate strategy must clear
    purely to be distinguishable from luck, and it grows with every configuration you try.
    """
    if n_trials < 2:
        raise ValueError(
            f"n_trials must be >= 2 for a maximum to be meaningful, got {n_trials!r}"
        )
    if sharpe_stdev <= 0.0:
        raise ValueError(f"sharpe_stdev must be positive, got {sharpe_stdev!r}")
    n = float(n_trials)
    a = _NORMAL.inv_cdf(1.0 - 1.0 / n)
    b = _NORMAL.inv_cdf(1.0 - 1.0 / (n * math.e))
    return sharpe_stdev * ((1.0 - _EULER_MASCHERONI) * a + _EULER_MASCHERONI * b)


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    *,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    sharpe_stdev: float = 1.0,
) -> float:
    """Probability that the observed Sharpe reflects genuine skill rather than selection.

    Corrects for (a) selection under multiple testing and (b) non-normal returns. All Sharpe values
    must share the periodicity of ``n_observations`` - mixing an annualised Sharpe with a daily
    observation count silently inflates the result.

    Args:
        observed_sharpe: The winning trial's Sharpe.
        n_trials: **Every** configuration tried, from the ledger. Not just the ones written up.
        n_observations: Number of return observations behind ``observed_sharpe``.
        skew: Skewness of the return series.
        kurtosis: Non-excess kurtosis (3.0 for a normal distribution).
        sharpe_stdev: Dispersion of Sharpe across trials.

    Returns:
        A probability in [0, 1]. Conventionally, below 0.95 is not evidence of skill.
    """
    if n_observations < 2:
        raise ValueError(f"n_observations must be >= 2, got {n_observations!r}")
    sr_star = expected_max_sharpe(n_trials, sharpe_stdev)
    variance = 1.0 - skew * observed_sharpe + ((kurtosis - 1.0) / 4.0) * observed_sharpe**2
    if variance <= 0.0:
        raise ValueError(
            f"degenerate Sharpe variance {variance!r} from skew={skew!r}, kurtosis={kurtosis!r}, "
            f"sharpe={observed_sharpe!r}; the moment estimates are inconsistent"
        )
    z = (observed_sharpe - sr_star) * math.sqrt(n_observations - 1) / math.sqrt(variance)
    return _NORMAL.cdf(z)


def min_backtest_length(n_trials: int, target_sharpe: float = 1.0) -> float:
    """Years of backtest needed before an in-sample Sharpe of ``target_sharpe`` means anything.

    Bailey et al.'s approximation ``MinBTL ~ 2 * ln(N) / SR^2``. With ``N=7`` and a target Sharpe of
    1.0 this is under 4 years - which is precisely why a two-year backtest showing Sharpe 1.0 after
    seven configurations is evidence of nothing at all.
    """
    if n_trials < 2:
        raise ValueError(f"n_trials must be >= 2, got {n_trials!r}")
    if target_sharpe <= 0.0:
        raise ValueError(f"target_sharpe must be positive, got {target_sharpe!r}")
    return 2.0 * math.log(n_trials) / (target_sharpe**2)
