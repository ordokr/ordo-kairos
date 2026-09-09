"""Turn a raw forecast into a probability you may size on.

Two jobs, in order.

**Anchor on the market.** AIA Forecaster (Alur et al. 2025, arXiv 2511.07678) is the state of the
art in LLM forecasting: it matches human superforecasters on ForecastBench, yet **underperforms
market consensus** on liquid prediction markets - while an *ensemble* of forecaster and consensus
**beats consensus alone**. The market price is therefore the prior, and a model only ever earns a
bounded adjustment to it. Default blend weight is 0.0: the model starts with no say and must
demonstrate skill to get any.

**Recalibrate externally.** Cash et al. 2025 (Memory & Cognition, DOI 10.3758/s13421-025-01755-4)
find LLMs are overconfident and - unlike humans - **fail to adjust confidence based on past
performance**. Self-reported confidence is therefore never admissible. Calibration here is fitted
statistically on resolved markets via isotonic regression (pool-adjacent-violators). The direction
of the calibration-over-accuracy result (Walsh & Joshi 2023) is supported by Hubacek et al. 2019 and
Wunderlich et al. 2026; its reported effect size is not usable - see the note in
:mod:`kairos.sizing` on the 2025 corrigendum.

Both the blend weight and the blend space are hyperparameters, so both must be written to the trial
ledger before their results are read (see :mod:`kairos.score`).
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

__all__ = [
    "BlendSpace",
    "blend",
    "IsotonicCalibrator",
    "ReliabilityReport",
    "reliability",
]

_EPS = 1e-9


class BlendSpace(str, Enum):
    """Where the market anchor and the model forecast are mixed.

    LOGIT is the default: it mixes evidence rather than probabilities, so a confident model cannot
    drag a 0.98 market price down as violently as a linear mix would. LINEAR is offered because it
    is what "ensembling with consensus" usually means in the literature, and the difference is an
    empirical question this repo is built to answer rather than assume.
    """

    LOGIT = "logit"
    LINEAR = "linear"


def _logit(p: float) -> float:
    p = min(max(p, _EPS), 1.0 - _EPS)
    return math.log(p / (1.0 - p))


def _expit(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def blend(
    market: float,
    model: float,
    weight: float = 0.0,
    space: BlendSpace = BlendSpace.LOGIT,
) -> float:
    """Mix a model forecast into the market price.

    Args:
        market: The market's implied probability. The prior.
        model: The model's probability.
        weight: Model weight in [0, 1]. **0.0 means "trade the market", which is the correct
            default** until the model has demonstrated out-of-sample skill against the market
            baseline on log score.
        space: See :class:`BlendSpace`.

    Returns:
        The blended probability.
    """
    for name, v in (("market", market), ("model", model), ("weight", weight)):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{name} must lie in [0, 1], got {v!r}")
    if weight == 0.0:
        return market
    if space is BlendSpace.LINEAR:
        return (1.0 - weight) * market + weight * model
    return _expit((1.0 - weight) * _logit(market) + weight * _logit(model))


@dataclass
class IsotonicCalibrator:
    """Monotone recalibration by pool-adjacent-violators (PAVA).

    Fits a non-decreasing step function mapping raw forecasts to empirical frequencies, then
    interpolates linearly between the fitted knots. Monotonicity is the point: it can correct
    systematic over- or under-confidence without ever reordering two forecasts, so it cannot
    manufacture discrimination the model did not have.

    This targets the documented failure mode directly. Le 2026 (arXiv 2602.19520), on 353M trades
    across 429k contracts, finds **persistent underconfidence in political markets - prices compress
    toward 50%** - which is exactly a monotone distortion, and therefore exactly what isotonic
    regression removes.
    """

    x: tuple[float, ...] = ()
    y: tuple[float, ...] = ()

    @property
    def fitted(self) -> bool:
        return len(self.x) > 0

    def fit(
        self,
        forecasts: Sequence[float],
        outcomes: Sequence[float],
        weights: Sequence[float] | None = None,
    ) -> "IsotonicCalibrator":
        """Fit on resolved markets. ``outcomes`` are 0/1 (or frequencies in [0, 1])."""
        if len(forecasts) != len(outcomes):
            raise ValueError(
                f"forecasts and outcomes must be the same length, got "
                f"{len(forecasts)} and {len(outcomes)}"
            )
        if not forecasts:
            raise ValueError("cannot fit a calibrator on zero observations")
        w = [1.0] * len(forecasts) if weights is None else list(weights)
        if len(w) != len(forecasts):
            raise ValueError(f"weights length {len(w)} != forecasts length {len(forecasts)}")
        if any(wi <= 0.0 for wi in w):
            raise ValueError("weights must be positive")

        order = sorted(range(len(forecasts)), key=lambda i: forecasts[i])
        xs = [float(forecasts[i]) for i in order]
        ys = [float(outcomes[i]) for i in order]
        ws = [float(w[i]) for i in order]

        # Merge exact ties in x first, so the fit is a well-defined function of x.
        mx: list[float] = []
        my: list[float] = []
        mw: list[float] = []
        for xi, yi, wi in zip(xs, ys, ws):
            if mx and abs(xi - mx[-1]) < _EPS:
                total = mw[-1] + wi
                my[-1] = (my[-1] * mw[-1] + yi * wi) / total
                mw[-1] = total
            else:
                mx.append(xi)
                my.append(yi)
                mw.append(wi)

        fitted = _pava(my, mw)
        self.x = tuple(mx)
        self.y = tuple(fitted)
        return self

    def predict(self, p: float) -> float:
        """Map a raw forecast to its calibrated probability.

        Falls through unchanged when unfitted, so an uncalibrated pipeline degrades to the identity
        rather than to a silent lie.
        """
        if not self.fitted:
            return p
        xs, ys = self.x, self.y
        if p <= xs[0]:
            return ys[0]
        if p >= xs[-1]:
            return ys[-1]
        i = bisect_left(xs, p)
        x0, x1 = xs[i - 1], xs[i]
        y0, y1 = ys[i - 1], ys[i]
        if x1 - x0 < _EPS:
            return y1
        return y0 + (y1 - y0) * (p - x0) / (x1 - x0)


def _pava(values: Sequence[float], weights: Sequence[float]) -> list[float]:
    """Pool-adjacent-violators: nearest non-decreasing sequence in weighted least squares."""
    blocks: list[list[float]] = []  # [weighted_sum, weight, count]
    for v, w in zip(values, weights):
        block = [v * w, w, 1.0]
        while blocks and blocks[-1][0] / blocks[-1][1] >= block[0] / block[1]:
            prev = blocks.pop()
            block[0] += prev[0]
            block[1] += prev[1]
            block[2] += prev[2]
        blocks.append(block)
    out: list[float] = []
    for wsum, wtot, count in blocks:
        out.extend([wsum / wtot] * int(count))
    return out


@dataclass(frozen=True)
class ReliabilityReport:
    """Murphy decomposition of the Brier score, plus expected calibration error.

    ``brier == reliability - resolution + uncertainty`` up to binning error.

    - **reliability** (lower is better): how far bin frequencies sit from bin forecasts. This is
      miscalibration, and it is the part isotonic regression removes.
    - **resolution** (higher is better): how far bin frequencies sit from the base rate. This is
      discrimination - real information. Calibration cannot create it.
    - **uncertainty**: the base rate's own variance. A property of the questions, not the forecaster.
    """

    n: int
    brier: float
    reliability: float
    resolution: float
    uncertainty: float
    ece: float
    bins: tuple[tuple[float, float, int], ...]

    @property
    def decomposition_residual(self) -> float:
        return self.brier - (self.reliability - self.resolution + self.uncertainty)


def reliability(
    forecasts: Sequence[float], outcomes: Sequence[float], n_bins: int = 10
) -> ReliabilityReport:
    """Bin forecasts and measure calibration against realised frequencies."""
    if len(forecasts) != len(outcomes):
        raise ValueError(
            f"forecasts and outcomes must be the same length, got "
            f"{len(forecasts)} and {len(outcomes)}"
        )
    if not forecasts:
        raise ValueError("cannot measure reliability on zero observations")
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins!r}")

    n = len(forecasts)
    base = sum(outcomes) / n
    brier = sum((f - o) ** 2 for f, o in zip(forecasts, outcomes)) / n

    buckets: list[list[tuple[float, float]]] = [[] for _ in range(n_bins)]
    for f, o in zip(forecasts, outcomes):
        idx = min(int(f * n_bins), n_bins - 1)
        buckets[idx].append((f, o))

    rel = 0.0
    res = 0.0
    ece = 0.0
    summary: list[tuple[float, float, int]] = []
    for bucket in buckets:
        if not bucket:
            continue
        k = len(bucket)
        mean_f = sum(f for f, _ in bucket) / k
        mean_o = sum(o for _, o in bucket) / k
        rel += k * (mean_f - mean_o) ** 2
        res += k * (mean_o - base) ** 2
        ece += k * abs(mean_f - mean_o)
        summary.append((mean_f, mean_o, k))

    return ReliabilityReport(
        n=n,
        brier=brier,
        reliability=rel / n,
        resolution=res / n,
        uncertainty=base * (1.0 - base),
        ece=ece / n,
        bins=tuple(summary),
    )
