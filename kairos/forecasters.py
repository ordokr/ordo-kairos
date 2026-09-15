"""Gate 2: forecasters, pooling, and the correlation measurement that must precede pooling.

``docs/PROTOCOL.md`` Gate 2 fixes the order and it is not negotiable:

1. market alone
2. best single model
3. simplest cross-model pool
4. market-anchored simple pool

**stopping at the first that is not beaten.** Sophisticated weighting is built only if the simple
pools are beaten on frozen out-of-sample data (AXIOMS C9, E1).

**Correlation is measured before any weighting machinery exists** (AXIOMS C8). Begin et al. 2026
(`10.48550/arxiv.2606.26583`) found pairwise forecast-error correlation ≈ 0.70 among aligned agents,
leaving ten of them worth about **1.4** independent forecasters. Naming four models is not having
four opinions, and :func:`effective_forecasters` reproduces their arithmetic exactly.

**Everything here is leakage-free by construction.** Forecasters see the decision price and
price-path features computed strictly before the decision point — never the question text, which is
the channel through which a language model's training data would re-enter the evaluation. An LLM
forecaster is Gate 2b and requires the contamination question answered first.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .polymarket import Observation

__all__ = [
    "Predictor",
    "ForecasterSpec",
    "fit_logit_tilt",
    "apply_tilt",
    "FORECASTERS",
    "simple_pool",
    "logit_pool",
    "error_correlations",
    "tilt_correlations",
    "mean_offdiagonal",
    "effective_forecasters",
    "rolling_oos",
]

EPS = 1e-4
Predictor = Callable[[Observation], float]


def clip(p: float) -> float:
    return min(max(p, EPS), 1.0 - EPS)


def _logit(p: float) -> float:
    p = clip(p)
    return math.log(p / (1.0 - p))


def _expit(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def fit_logit_tilt(
    offsets: Sequence[float],
    feature_rows: Sequence[Sequence[float]],
    outcomes: Sequence[float],
    *,
    steps: int = 80,
    lr: float = 0.8,
) -> tuple[float, list[float]]:
    """Fit ``p = expit(offset + bias + beta . x)`` by gradient ascent on the log-likelihood.

    ``offset`` is the market's own logit, held fixed, so the fitted parameters are exactly *what the
    model adds to the market* — which is the quantity Gate 2 is about.

    Shared with :mod:`kairos.nullworld`, which uses the same fitter to manufacture adaptive
    overfitting in the Gate-0 harness. One implementation, two callers: a second copy would let the
    thing under test and the thing testing it drift apart.
    """
    n = len(offsets)
    if n == 0:
        raise ValueError("cannot fit on an empty sample")
    if not (len(feature_rows) == len(outcomes) == n):
        raise ValueError(
            f"offsets, feature_rows and outcomes must match: {n}, "
            f"{len(feature_rows)}, {len(outcomes)}"
        )
    k = len(feature_rows[0]) if feature_rows else 0
    beta = [0.0] * k
    bias = 0.0
    for _ in range(steps):
        gb = 0.0
        g = [0.0] * k
        for off, x, y in zip(offsets, feature_rows, outcomes):
            mu = _expit(off + bias + sum(b * v for b, v in zip(beta, x)))
            r = y - mu
            gb += r
            for j in range(k):
                g[j] += r * x[j]
        bias += lr * gb / n
        for j in range(k):
            beta[j] += lr * g[j] / n
    return bias, beta


def apply_tilt(price: float, bias: float, beta: Sequence[float], x: Sequence[float]) -> float:
    return clip(_expit(_logit(price) + bias + sum(b * v for b, v in zip(beta, x))))


@dataclass(frozen=True)
class ForecasterSpec:
    """A named forecaster and the feature keys it is allowed to see."""

    name: str
    feature_keys: tuple[str, ...]

    def fit(self, train: Sequence[Observation]) -> Predictor:
        """Fit on ``train`` only, with features standardised on ``train`` only.

        Standardisation is not cosmetic. The first Gate-2a run left features raw, and the
        ``maturity`` forecaster — whose inputs are O(10) days and counts while every other
        forecaster's are O(0.01) price deltas — diverged to a log score of **4.82** against a 0.336
        benchmark. Its result was meaningless rather than bad. Statistics come from the training
        split alone, so the transform leaks nothing.
        """
        if not self.feature_keys:  # the market itself
            return lambda o: clip(o.price)
        keys = self.feature_keys
        raw_rows = [[o.features.get(k, 0.0) for k in keys] for o in train]
        centres = [statistics.fmean(col) for col in zip(*raw_rows)]
        scales = [
            (statistics.pstdev(col) or 1.0) for col in zip(*raw_rows)
        ]

        def standardise(row: Sequence[float]) -> list[float]:
            return [(v - c) / s for v, c, s in zip(row, centres, scales)]

        rows = [standardise(r) for r in raw_rows]
        offsets = [_logit(o.price) for o in train]
        outcomes = [o.outcome for o in train]
        bias, beta = fit_logit_tilt(offsets, rows, outcomes)
        return lambda o: apply_tilt(
            o.price, bias, beta, standardise([o.features.get(k, 0.0) for k in keys])
        )


#: Deliberately distinct information sources, so the correlation measurement has something to
#: measure. A momentum and a reversion forecaster would collapse into one under fitting - the sign
#: is estimated, not assumed - so they are one entry, not two.
FORECASTERS: tuple[ForecasterSpec, ...] = (
    ForecasterSpec("market", ()),
    ForecasterSpec("momentum", ("mom_1", "mom_3")),
    ForecasterSpec("drift", ("drift_per_day",)),
    ForecasterSpec("volatility", ("volatility", "range")),
    ForecasterSpec("maturity", ("age_days", "n_before")),
)


def simple_pool(predictions: Sequence[Sequence[float]]) -> list[float]:
    """Arithmetic mean of probabilities — the simplest possible pool."""
    if not predictions:
        raise ValueError("cannot pool zero forecasters")
    n = len(predictions)
    return [clip(sum(col) / n) for col in zip(*predictions)]


def logit_pool(predictions: Sequence[Sequence[float]]) -> list[float]:
    """Mean in logit space. Mixes evidence rather than probabilities."""
    if not predictions:
        raise ValueError("cannot pool zero forecasters")
    n = len(predictions)
    return [clip(_expit(sum(_logit(p) for p in col) / n)) for col in zip(*predictions)]


def _pairwise(series: Mapping[str, Sequence[float]]) -> dict[tuple[str, str], float]:
    names = list(series)
    out: dict[tuple[str, str], float] = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            try:
                out[(a, b)] = statistics.correlation(list(series[a]), list(series[b]))
            except (statistics.StatisticsError, ValueError, ZeroDivisionError):
                out[(a, b)] = float("nan")
    return out


def error_correlations(
    predictions: Mapping[str, Sequence[float]], outcomes: Sequence[float]
) -> dict[tuple[str, str], float]:
    """Pairwise correlation of forecast errors ``p - y`` — the quantity Begin et al. report.

    .. warning::

       For **market-anchored** forecasters this is near-unity almost by construction. Every
       prediction is a small tilt on the same price, so every error is dominated by the shared
       ``q - y`` term. The first Gate-2a run measured 0.999+ between models built on entirely
       different features. That is a property of anchoring, not evidence about the models.

       Use :func:`tilt_correlations` to ask whether the models carry *different information*.
       Report both: error correlation governs how much pooling can help, tilt correlation says
       whether there is anything to pool.
    """
    names = list(predictions)
    return _pairwise({n: [p - y for p, y in zip(predictions[n], outcomes)] for n in names})


def tilt_correlations(
    predictions: Mapping[str, Sequence[float]], market: Sequence[float]
) -> dict[tuple[str, str], float]:
    """Pairwise correlation of the **tilts** ``p - q`` — what each model adds beyond the market.

    This is the diagnostic that survives anchoring. Two forecasters whose tilts correlate at 1.0 are
    the same model wearing two names, whatever their feature lists say.
    """
    names = list(predictions)
    return _pairwise({n: [p - q for p, q in zip(predictions[n], market)] for n in names})


def mean_offdiagonal(correlations: Mapping[tuple[str, str], float]) -> float:
    vals = [v for v in correlations.values() if v == v]  # NaN-safe
    return sum(vals) / len(vals) if vals else float("nan")


def effective_forecasters(n: int, mean_rho: float) -> float:
    """``n / (1 + (n-1) * rho)`` — how many independent opinions ``n`` correlated ones are worth.

    Reproduces Begin et al.'s headline: ten agents at rho = 0.70 give 10/(1+9(0.7)) = **1.37**.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n!r}")
    denom = 1.0 + (n - 1) * mean_rho
    if denom <= 0:
        return float(n)
    return n / denom


def rolling_oos(
    obs: Sequence[Observation],
    clusters: Sequence[str],
    n_folds: int,
    fitters: Mapping[str, Callable[[Sequence[Observation]], Predictor]],
) -> dict[str, list]:
    """Expanding-window out-of-sample predictions, split by **event** and never by row.

    Contracts on one event resolve together, so a row-wise split would put a sibling of the test row
    into the training set. Returns one list per fitter plus ``_outcome`` and ``_cluster``.
    """
    by_cluster: dict[str, list[Observation]] = {}
    for o in obs:
        by_cluster.setdefault(o.cluster_id, []).append(o)

    n = len(clusters)
    start = max(n // 3, 2)
    if n - start < n_folds:
        n_folds = max(1, n - start)
    edges = [start + round(i * (n - start) / n_folds) for i in range(n_folds + 1)]

    preds: dict[str, list] = {name: [] for name in fitters}
    preds["_outcome"] = []
    preds["_cluster"] = []
    for f in range(n_folds):
        lo, hi = edges[f], edges[f + 1]
        if hi <= lo:
            continue
        train = [o for c in clusters[:lo] for o in by_cluster[c]]
        test = [o for c in clusters[lo:hi] for o in by_cluster[c]]
        if len(train) < 20 or not test:
            continue
        fitted = {name: fit(train) for name, fit in fitters.items()}
        for o in test:
            for name in fitters:
                preds[name].append(fitted[name](o))
            preds["_outcome"].append(o.outcome)
            preds["_cluster"].append(o.cluster_id)
    return preds
