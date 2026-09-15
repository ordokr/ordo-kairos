"""The primary statistical test: is the forecaster better than the benchmark?

Pre-registered in ``docs/PROTOCOL.md`` §0. The hypothesis is a **paired forecast comparison**::

    H0:  E[ S(q_ref, y) - S(p, y) ] <= 0        (the forecaster adds nothing)
    H1:  E[ S(q_ref, y) - S(p, y) ]  > 0        (the forecaster adds information)

with ``S`` the log score. Positive ``delta`` means ``p`` beat ``q_ref`` on that observation.

**Why not a Sharpe statistic.** Deflated Sharpe corrects selection bias and non-normality, and it
stays as a secondary diagnostic - but the object under test here is a sequence of paired score
differences with strong event-level dependence, not a return series. Forecast-superiority testing
with dependent errors is its own literature (Corradi, Jin & Swanson 2023, `10.2139/ssrn.3538905`),
and the right instrument is a dependence-aware resample of the differences themselves
(``docs/AXIOMS.md`` C4).

**Why clustering is not optional.** Twenty contracts on one election are one observation. Treating
them as twenty inflates the effective sample by 20x and the t-statistic by roughly sqrt(20). The
IID test in this module exists **only** so the null-world harness can demonstrate that failure
empirically; it must never be used to decide anything.

Two cluster-robust procedures, both standard:

- **Pairs cluster bootstrap** - resample whole clusters with replacement. Good when clusters are
  many. Supplies the confidence interval.
- **Wild cluster bootstrap (Rademacher, null imposed)** - the recommended procedure when clusters
  are *few*, where the pairs bootstrap under-rejects or fails outright
  (Joshi, Pustejovsky & Beretvas 2021, `10.1002/jrsm.1554`).

Nothing here is validated until it survives ``docs/PROTOCOL.md`` Gate 0.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Sequence

from .score import log_score_pointwise

__all__ = [
    "InferenceError",
    "SuperiorityResult",
    "paired_deltas",
    "cluster_mean_and_se",
    "cluster_bootstrap_test",
    "wild_cluster_bootstrap_test",
    "iid_bootstrap_test",
    "superiority_test",
    "StratumResult",
    "MaxStatisticResult",
    "max_statistic_test",
    "weighted_share_ci",
]


DEFAULT_ALPHA = 0.05
DEFAULT_BOOTSTRAP = 2000

#: Below this many clusters, the pairs bootstrap is unreliable and the wild cluster bootstrap is
#: used instead. Cameron/Gelbach/Miller-style guidance; the harness reports which fired.
FEW_CLUSTERS = 30

#: A stratum with fewer clusters than this is not tested at all. Reporting a nominal p-value from
#: three events is not a weak result, it is not a result; excluding up front is honest where
#: excluding after seeing the answer would not be.
MIN_STRATUM_CLUSTERS = 20


class InferenceError(ValueError):
    """Raised when a test cannot be computed from the inputs given."""


@dataclass(frozen=True)
class SuperiorityResult:
    """Outcome of one paired forecast-superiority test."""

    mean_delta: float
    n_observations: int
    n_clusters: int
    p_value: float
    ci_low: float
    ci_high: float
    alpha: float
    method: str
    cluster_se: float

    @property
    def significant(self) -> bool:
        """One-sided rejection of H0 at ``alpha``. **Not** a synonym for 'we have an edge'."""
        return self.p_value < self.alpha and self.mean_delta > 0.0

    def explain(self) -> str:
        verdict = "SUPERIOR" if self.significant else "not distinguishable from the benchmark"
        return (
            f"{verdict}: mean delta {self.mean_delta:+.5f} "
            f"(95% CI [{self.ci_low:+.5f}, {self.ci_high:+.5f}]), "
            f"p={self.p_value:.4f}, {self.n_observations} obs in {self.n_clusters} clusters, "
            f"cluster SE {self.cluster_se:.5f}, method={self.method}"
        )


def paired_deltas(
    forecasts: Sequence[float],
    benchmark: Sequence[float],
    outcomes: Sequence[float],
    scorer: Callable[[Sequence[float], Sequence[float]], list[float]] = log_score_pointwise,
) -> list[float]:
    """Per-observation score advantage of ``forecasts`` over ``benchmark``.

    Positive means the forecaster did better on that observation, since the scorers here are
    negatively oriented (lower is better).
    """
    if not (len(forecasts) == len(benchmark) == len(outcomes)):
        raise InferenceError(
            f"forecasts, benchmark and outcomes must be the same length, got "
            f"{len(forecasts)}, {len(benchmark)} and {len(outcomes)}"
        )
    s_p = scorer(forecasts, outcomes)
    s_q = scorer(benchmark, outcomes)
    return [q - p for p, q in zip(s_p, s_q)]


def cluster_mean_and_se(
    deltas: Sequence[float], cluster_ids: Sequence[object]
) -> tuple[float, float, int]:
    """Mean and cluster-robust standard error of the mean, with the usual G/(G-1) correction."""
    if len(deltas) != len(cluster_ids):
        raise InferenceError(
            f"deltas and cluster_ids must be the same length, got "
            f"{len(deltas)} and {len(cluster_ids)}"
        )
    if not deltas:
        raise InferenceError("cannot test zero observations")
    n = len(deltas)
    mean = sum(deltas) / n
    sums: dict[object, float] = defaultdict(float)
    for d, c in zip(deltas, cluster_ids):
        sums[c] += d - mean
    g = len(sums)
    ss = sum(s * s for s in sums.values())
    correction = g / (g - 1.0) if g > 1 else 1.0
    var = correction * ss / (n * n)
    return mean, math.sqrt(max(var, 0.0)), g


def _group(deltas: Sequence[float], cluster_ids: Sequence[object]) -> list[list[float]]:
    groups: dict[object, list[float]] = defaultdict(list)
    for d, c in zip(deltas, cluster_ids):
        groups[c].append(d)
    return list(groups.values())


def _one_sided_p(bootstrap_stats: Sequence[float], observed: float) -> float:
    """Centred one-sided bootstrap p-value with the +1 correction (never returns exactly 0)."""
    exceed = sum(1 for s in bootstrap_stats if s >= observed)
    return (1.0 + exceed) / (len(bootstrap_stats) + 1.0)


def cluster_bootstrap_test(
    deltas: Sequence[float],
    cluster_ids: Sequence[object],
    *,
    alpha: float = DEFAULT_ALPHA,
    n_boot: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
) -> SuperiorityResult:
    """Pairs cluster bootstrap: resample whole clusters with replacement."""
    mean, se, g = cluster_mean_and_se(deltas, cluster_ids)
    if g < 2:
        raise InferenceError(
            f"need at least 2 clusters to resample, got {g}; a single cluster carries one "
            f"observation's worth of information"
        )
    groups = _group(deltas, cluster_ids)
    rng = random.Random(seed)

    means: list[float] = []
    for _ in range(n_boot):
        total = 0.0
        count = 0
        for _ in range(g):
            grp = groups[rng.randrange(g)]
            total += sum(grp)
            count += len(grp)
        means.append(total / count)

    means.sort()
    lo = means[max(0, int((alpha / 2) * len(means)) - 1)]
    hi = means[min(len(means) - 1, int((1 - alpha / 2) * len(means)))]
    p = _one_sided_p([m - mean for m in means], mean)
    return SuperiorityResult(
        mean_delta=mean,
        n_observations=len(deltas),
        n_clusters=g,
        p_value=p,
        ci_low=lo,
        ci_high=hi,
        alpha=alpha,
        method="pairs-cluster-bootstrap",
        cluster_se=se,
    )


def wild_cluster_bootstrap_test(
    deltas: Sequence[float],
    cluster_ids: Sequence[object],
    *,
    alpha: float = DEFAULT_ALPHA,
    n_boot: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
) -> SuperiorityResult:
    """Wild cluster bootstrap with Rademacher weights and the null imposed.

    Under H0 the mean is zero, so the restricted residual of each observation is the observation
    itself. Each cluster is multiplied by an independent +/-1 draw and the cluster-robust
    t-statistic is recomputed, giving a reference distribution valid with few clusters.
    """
    mean, se, g = cluster_mean_and_se(deltas, cluster_ids)
    if g < 2:
        raise InferenceError(f"need at least 2 clusters, got {g}")
    if se <= 0.0:
        raise InferenceError(
            "cluster-robust standard error is zero; the score differences carry no "
            "between-cluster variation and no test is possible"
        )
    t_hat = mean / se
    rng = random.Random(seed)
    unique = list(dict.fromkeys(cluster_ids))

    t_stats: list[float] = []
    for _ in range(n_boot):
        weights = {c: (1.0 if rng.random() < 0.5 else -1.0) for c in unique}
        boot = [weights[c] * d for d, c in zip(deltas, cluster_ids)]
        b_mean, b_se, _ = cluster_mean_and_se(boot, cluster_ids)
        t_stats.append(b_mean / b_se if b_se > 0 else 0.0)

    p = _one_sided_p(t_stats, t_hat)
    half = 1.959963984540054 * se  # normal approximation, reported for orientation only
    return SuperiorityResult(
        mean_delta=mean,
        n_observations=len(deltas),
        n_clusters=g,
        p_value=p,
        ci_low=mean - half,
        ci_high=mean + half,
        alpha=alpha,
        method="wild-cluster-bootstrap",
        cluster_se=se,
    )


def iid_bootstrap_test(
    deltas: Sequence[float],
    *,
    alpha: float = DEFAULT_ALPHA,
    n_boot: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
) -> SuperiorityResult:
    """Naive IID bootstrap, ignoring clustering.

    .. warning::

       **Never use this to decide anything.** It exists so the Gate-0 harness can demonstrate,
       against known nulls, how badly ignoring event structure inflates the rejection rate. It is a
       exhibit, not an instrument (``docs/AXIOMS.md`` C3).
    """
    if not deltas:
        raise InferenceError("cannot test zero observations")
    n = len(deltas)
    mean = sum(deltas) / n
    rng = random.Random(seed)
    means = [sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot)]
    means.sort()
    lo = means[max(0, int((alpha / 2) * len(means)) - 1)]
    hi = means[min(len(means) - 1, int((1 - alpha / 2) * len(means)))]
    p = _one_sided_p([m - mean for m in means], mean)
    sd = math.sqrt(sum((d - mean) ** 2 for d in deltas) / max(n - 1, 1))
    return SuperiorityResult(
        mean_delta=mean,
        n_observations=n,
        n_clusters=n,
        p_value=p,
        ci_low=lo,
        ci_high=hi,
        alpha=alpha,
        method="iid-bootstrap-INVALID-FOR-DECISIONS",
        cluster_se=sd / math.sqrt(n),
    )


@dataclass(frozen=True)
class StratumResult:
    """One stratum's studentised statistic, before any multiplicity correction."""

    name: str
    mean_delta: float
    cluster_se: float
    t_stat: float
    n_observations: int
    n_clusters: int


@dataclass(frozen=True)
class MaxStatisticResult:
    """Outcome of testing several strata and keeping the best one."""

    best: StratumResult
    strata: tuple[StratumResult, ...]
    excluded: tuple[tuple[str, int], ...]
    p_corrected: float
    p_uncorrected: float
    n_tested: int
    alpha: float
    method: str

    @property
    def significant(self) -> bool:
        return self.p_corrected < self.alpha and self.best.mean_delta > 0.0

    @property
    def significant_uncorrected(self) -> bool:
        """What reporting the winning stratum's own p-value would have concluded.

        Exposed so the harness can measure the false-positive rate of the uncorrected search rather
        than assert it. Never use it to decide anything (``docs/AXIOMS.md`` C3).
        """
        return self.p_uncorrected < self.alpha and self.best.mean_delta > 0.0

    def explain(self) -> str:
        verdict = "SUPERIOR" if self.significant else "not distinguishable from the benchmark"
        return (
            f"{verdict} in stratum {self.best.name!r}: mean delta {self.best.mean_delta:+.5f}, "
            f"t={self.best.t_stat:+.3f}, p_corrected={self.p_corrected:.4f} "
            f"(uncorrected {self.p_uncorrected:.4f}) over {self.n_tested} strata, "
            f"{self.best.n_observations} obs in {self.best.n_clusters} clusters"
        )


def max_statistic_test(
    deltas: Sequence[float],
    cluster_ids: Sequence[object],
    strata: Sequence[object],
    *,
    alpha: float = DEFAULT_ALPHA,
    n_boot: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
    min_clusters: int = MIN_STRATUM_CLUSTERS,
) -> MaxStatisticResult:
    """Test every stratum, keep the best, and price the keeping.

    Splitting a sample into strata and reporting whichever one wins is a search, and its nominal
    p-value is not a p-value. The reference distribution here is the distribution of the **maximum**
    statistic under the null, which is what the search actually samples from.

    Two construction details carry the validity:

    - **One shared cluster resample per replicate**, from which every stratum's statistic is
      recomputed. Strata cut the same events, so their statistics are correlated; a Bonferroni
      correction assumes they are not and over-corrects, while per-stratum bootstraps assume it away
      entirely. Resampling once and letting each stratum inherit the same draw preserves whatever
      correlation is actually there (Westfall & Young's step-down construction, single-step form).
    - **Studentised statistics.** A stratum with few events has a noisier mean, so comparing raw
      means would hand the maximum to the smallest stratum by construction. ``mean / cluster_se``
      makes them comparable, which is the whole reason max-t is stated in t.

    Strata with fewer than ``min_clusters`` events are excluded before anything is computed, and
    reported in ``excluded`` so the exclusion is auditable rather than silent.
    """
    if not (len(deltas) == len(cluster_ids) == len(strata)):
        raise InferenceError(
            f"deltas, cluster_ids and strata must be the same length, got "
            f"{len(deltas)}, {len(cluster_ids)} and {len(strata)}"
        )
    if not deltas:
        raise InferenceError("cannot test zero observations")

    by_stratum: dict[object, list[int]] = defaultdict(list)
    for i, s in enumerate(strata):
        by_stratum[s].append(i)

    tested: dict[object, list[int]] = {}
    excluded: list[tuple[str, int]] = []
    for s, idx in sorted(by_stratum.items(), key=lambda kv: str(kv[0])):
        g = len({cluster_ids[i] for i in idx})
        if g < min_clusters:
            excluded.append((str(s), g))
        else:
            tested[s] = idx
    if not tested:
        raise InferenceError(
            f"no stratum reached {min_clusters} clusters; largest had "
            f"{max((g for _, g in excluded), default=0)}"
        )

    observed: dict[object, StratumResult] = {}
    for s, idx in tested.items():
        mean, se, g = cluster_mean_and_se([deltas[i] for i in idx], [cluster_ids[i] for i in idx])
        observed[s] = StratumResult(
            name=str(s),
            mean_delta=mean,
            cluster_se=se,
            t_stat=mean / se if se > 0.0 else 0.0,
            n_observations=len(idx),
            n_clusters=g,
        )
    best_key = max(observed, key=lambda s: observed[s].t_stat)
    t_max = observed[best_key].t_stat

    # Cluster universe, and each cluster's rows split by stratum, so a resample is a cheap regroup.
    universe = list(dict.fromkeys(cluster_ids))
    rows: dict[object, dict[object, list[float]]] = defaultdict(lambda: defaultdict(list))
    for d, c, s in zip(deltas, cluster_ids, strata):
        if s in tested:
            rows[c][s].append(d)

    rng = random.Random(seed)
    g_total = len(universe)
    boot_max: list[float] = []
    for _ in range(n_boot):
        draw = [universe[rng.randrange(g_total)] for _ in range(g_total)]
        best_t = -math.inf
        for s in tested:
            vals: list[float] = []
            cids: list[int] = []
            for j, c in enumerate(draw):
                got = rows[c].get(s)
                if got:
                    vals.extend(got)
                    cids.extend([j] * len(got))
            if len({*cids}) < 2:
                continue
            b_mean, b_se, _ = cluster_mean_and_se(vals, cids)
            if b_se <= 0.0:
                continue
            # Centre on the observed stratum mean: the null is "no advantage", imposed by shifting.
            t = (b_mean - observed[s].mean_delta) / b_se
            best_t = max(best_t, t)
        if best_t > -math.inf:
            boot_max.append(best_t)

    if not boot_max:
        raise InferenceError(
            "every bootstrap replicate degenerated; the strata carry no between-cluster variation"
        )

    p_corrected = _one_sided_p(boot_max, t_max)
    p_uncorrected = _one_sided_p(
        _single_stratum_null(rows, observed, best_key, universe, n_boot, seed), t_max
    )
    return MaxStatisticResult(
        best=observed[best_key],
        strata=tuple(observed[s] for s in sorted(observed, key=lambda s: -observed[s].t_stat)),
        excluded=tuple(excluded),
        p_corrected=p_corrected,
        p_uncorrected=p_uncorrected,
        n_tested=len(tested),
        alpha=alpha,
        method="max-t-cluster-bootstrap",
    )


def _single_stratum_null(
    rows: dict, observed: dict, key: object,
    universe: Sequence[object], n_boot: int, seed: int,
) -> list[float]:
    """Null distribution for one stratum alone — what a naive per-stratum test would have used.

    Reported next to the corrected p-value so the size of the multiplicity penalty is visible rather
    than asserted.
    """
    rng = random.Random(seed + 977)
    g_total = len(universe)
    out: list[float] = []
    for _ in range(n_boot):
        draw = [universe[rng.randrange(g_total)] for _ in range(g_total)]
        vals: list[float] = []
        cids: list[int] = []
        for j, c in enumerate(draw):
            got = rows[c].get(key)
            if got:
                vals.extend(got)
                cids.extend([j] * len(got))
        if len({*cids}) < 2:
            continue
        b_mean, b_se, _ = cluster_mean_and_se(vals, cids)
        if b_se > 0.0:
            out.append((b_mean - observed[key].mean_delta) / b_se)
    return out


def superiority_test(
    forecasts: Sequence[float],
    benchmark: Sequence[float],
    outcomes: Sequence[float],
    cluster_ids: Sequence[object],
    *,
    alpha: float = DEFAULT_ALPHA,
    n_boot: int = DEFAULT_BOOTSTRAP,
    seed: int = 0,
    scorer: Callable[[Sequence[float], Sequence[float]], list[float]] = log_score_pointwise,
) -> SuperiorityResult:
    """The pre-registered primary test. Picks the cluster-robust procedure by cluster count.

    Returns a :class:`SuperiorityResult`; ``significant`` is a one-sided rejection at ``alpha``,
    which is a statement about this sample and not a licence to trade.
    """
    deltas = paired_deltas(forecasts, benchmark, outcomes, scorer)
    _, _, g = cluster_mean_and_se(deltas, cluster_ids)
    if g < FEW_CLUSTERS:
        return wild_cluster_bootstrap_test(
            deltas, cluster_ids, alpha=alpha, n_boot=n_boot, seed=seed
        )
    return cluster_bootstrap_test(deltas, cluster_ids, alpha=alpha, n_boot=n_boot, seed=seed)


#: Below this many independent units a percentile bootstrap of a share is not worth reporting.
MIN_SHARE_UNITS = 30


def weighted_share_ci(flags: Sequence[bool], weights: Sequence[float], *,
                      seed: int = 0, draws: int = 2000,
                      alpha: float = DEFAULT_ALPHA) -> tuple[float, float] | None:
    """Percentile interval for a **weighted share** ``sum(w where flag) / sum(w)``.

    The resampled unit is the observation itself — a market, not a time block — because markets are
    the independent units and there is no serial structure to preserve. Distinct from
    :func:`kairos.microstructure.bootstrap_ci`, which blocks a time series.

    Exists because Gate K.0 compares a measured share against another venue's measured share, and
    two bare point estimates are not a comparison (``CORRECTIONS.md`` Pass 29).
    """
    if len(flags) != len(weights):
        raise ValueError(f"{len(flags)} flags against {len(weights)} weights")
    if any(w < 0.0 for w in weights):
        raise ValueError("weights must be non-negative")
    n = len(flags)
    if n < MIN_SHARE_UNITS or sum(weights) <= 0.0:
        return None
    rng = random.Random(seed)
    stats = []
    for _ in range(draws):
        num = den = 0.0
        for _ in range(n):
            i = rng.randrange(n)
            den += weights[i]
            if flags[i]:
                num += weights[i]
        stats.append(num / den if den > 0.0 else 0.0)
    stats.sort()
    lo = stats[max(0, int((alpha / 2.0) * draws) - 1)]
    hi = stats[min(draws - 1, int((1.0 - alpha / 2.0) * draws))]
    return lo, hi
