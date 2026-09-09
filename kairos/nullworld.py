"""Gate 0: can Kairos correctly discover **nothing** when there is nothing to discover?

``docs/PROTOCOL.md`` Gate 0 ranks above all strategy discovery (``docs/AXIOMS.md`` A7). Before
asking whether this pipeline can find an edge, we ask whether it reliably fails to find one that
does not exist.

**Why a pure false-positive test is not enough.** A pipeline that never reports an edge passes a
null-world gate trivially while being useless. So every null world is paired with a **positive
control** carrying a known, injected edge, and the harness reports statistical power alongside the
false-positive rate. Gate 0 fails in both directions: too many detections, or none.

**Three protocols are compared** so the harness shows *which* discipline fixes *what*:

============== ================================= ==============================================
Protocol       Selection                         Inference
============== ================================= ==============================================
``naive``      best-of-N on all data             IID bootstrap, clustering ignored
``cluster``    best-of-N on all data             cluster-robust bootstrap
``kairos``     best-of-N on dev, **sealed** test  cluster-robust bootstrap on the holdout
============== ================================= ==============================================

``naive`` should blow up. ``cluster`` should improve but still over-reject, because selection bias
survives correct inference. Only ``kairos`` should hold the rejection rate near alpha. That is the
empirical content of AXIOMS C3, C5 and C6, tested against our own code rather than asserted.

**The thresholds below are pre-registered.** Changing one after seeing a result is a new trial and
belongs in ``docs/CORRECTIONS.md``. Do not tune the null worlds to make the gate pass (A8).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from typing import Callable, Sequence

from .forecasters import fit_logit_tilt
from .inference import (
    DEFAULT_ALPHA,
    InferenceError,
    MaxStatisticResult,
    SuperiorityResult,
    cluster_bootstrap_test,
    iid_bootstrap_test,
    max_statistic_test,
    paired_deltas,
    superiority_test,
)

__all__ = [
    "World",
    "fair_market",
    "martingale_market",
    "shuffle_outcomes",
    "time_shift_features",
    "add_noise_features",
    "microstructure_placebo",
    "inject_signal",
    "candidate_forecasters",
    "WorldReport",
    "GateReport",
    "run_gate0",
    "ALPHA",
    "POWER_FLOOR",
    "FPR_TAIL_ALPHA",
]

# ---------------------------------------------------------------------------
# Pre-registered thresholds. Do not adjust after seeing results (AXIOMS A8).
# ---------------------------------------------------------------------------

#: Nominal one-sided significance level of the primary test.
ALPHA = DEFAULT_ALPHA

#: Minimum detection rate on the positive control. Below this the instrument is inert and Gate 0
#: fails even with a perfect false-positive record.
POWER_FLOOR = 0.50

#: A world's false-positive rate fails if the exact binomial tail P(X >= observed | n, ALPHA) falls
#: below this. Uses the exact distribution rather than an invented tolerance (AXIOMS A6).
FPR_TAIL_ALPHA = 0.01

_EPS = 1e-9


def _logit(p: float) -> float:
    p = min(max(p, _EPS), 1.0 - _EPS)
    return math.log(p / (1.0 - p))


def _expit(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass(frozen=True)
class World:
    """One synthetic market universe.

    Attributes:
        name: Identifier for reporting.
        market: Quoted probability per contract - the benchmark to beat.
        outcomes: Realised 0/1 outcome per contract.
        cluster_ids: Event id per contract. Contracts sharing an id resolve together.
        features: Per-contract covariate vectors offered to candidate forecasters.
        truth: True probability per contract where known, else ``None``.
        has_signal: Ground truth. ``False`` means **no** forecaster can beat ``market`` in
            expectation, so any detection is a false positive.
    """

    name: str
    market: list[float]
    outcomes: list[float]
    cluster_ids: list[int]
    features: list[list[float]] = field(default_factory=list)
    truth: list[float] | None = None
    has_signal: bool = False

    def __len__(self) -> int:
        return len(self.market)

    @property
    def n_clusters(self) -> int:
        return len(set(self.cluster_ids))


# ---------------------------------------------------------------------------
# Null-world generators
# ---------------------------------------------------------------------------


def fair_market(
    n_events: int = 40, contracts_per_event: int = 10, *, seed: int = 0
) -> World:
    """A perfectly calibrated market. The strictest null.

    Each event draws a true probability and the market quotes it **exactly**. Because the log score
    is strictly proper, its expectation is uniquely minimised at the true probability, so no
    forecaster can beat this market in expectation - by construction, not by assumption.

    Quoting the truth exactly is deliberate: any price noise would make the market beatable by
    someone who knows the truth, turning the null world into a signal world.
    """
    rng = random.Random(seed)
    market: list[float] = []
    outcomes: list[float] = []
    clusters: list[int] = []
    truth: list[float] = []
    for event in range(n_events):
        pi = rng.uniform(0.05, 0.95)
        y = 1.0 if rng.random() < pi else 0.0  # one event, one resolution
        for _ in range(contracts_per_event):
            market.append(pi)
            truth.append(pi)
            outcomes.append(y)
            clusters.append(event)
    return World("fair_market", market, outcomes, clusters, truth=truth, has_signal=False)


def martingale_market(
    n_events: int = 40, contracts_per_event: int = 10, *, steps: int = 12, seed: int = 0
) -> World:
    """Prices follow a martingale in logit space; the current price is a sufficient statistic.

    The price *path* is exposed as features, so a candidate forecaster may try to extract momentum,
    reversal, or any other history effect. There is none: the outcome depends only on the terminal
    price.
    """
    rng = random.Random(seed)
    market: list[float] = []
    outcomes: list[float] = []
    clusters: list[int] = []
    features: list[list[float]] = []
    truth: list[float] = []
    for event in range(n_events):
        x = _logit(rng.uniform(0.15, 0.85))
        path = [x]
        for _ in range(steps):
            x += rng.gauss(0.0, 0.35)
            path.append(x)
        pi = _expit(path[-1])
        y = 1.0 if rng.random() < pi else 0.0
        history = [_expit(v) for v in path[-5:]]
        for _ in range(contracts_per_event):
            market.append(pi)
            truth.append(pi)
            outcomes.append(y)
            clusters.append(event)
            features.append(list(history))
    return World(
        "martingale_market", market, outcomes, clusters, features, truth=truth, has_signal=False
    )


def shuffle_outcomes(world: World, *, seed: int = 0, n_strata: int = 10) -> World:
    """Permute outcomes **within price strata**, destroying feature-outcome links.

    Stratifying matters. A naive global shuffle would also destroy the market's calibration, which
    would leave the market beatable by anyone who knows the base rate - a signal world wearing a
    null world's name. Shuffling inside price bands keeps the market calibrated while severing any
    relationship between covariates and outcomes.
    """
    rng = random.Random(seed)
    by_stratum: dict[int, list[int]] = {}
    for i, q in enumerate(world.market):
        by_stratum.setdefault(min(int(q * n_strata), n_strata - 1), []).append(i)

    outcomes = list(world.outcomes)
    for indices in by_stratum.values():
        values = [world.outcomes[i] for i in indices]
        rng.shuffle(values)
        for i, v in zip(indices, values):
            outcomes[i] = v
    return replace(
        world, name=f"{world.name}+shuffled", outcomes=outcomes, truth=None, has_signal=False
    )


def time_shift_features(world: World, *, shift: int = 7) -> World:
    """Rotate the feature stream relative to outcomes, breaking temporal alignment."""
    if not world.features:
        raise ValueError(f"world {world.name!r} has no features to shift")
    k = shift % len(world.features)
    rotated = world.features[k:] + world.features[:k]
    return replace(
        world, name=f"{world.name}+timeshift", features=rotated, has_signal=world.has_signal and False
    )


def add_noise_features(
    world: World, *, n_event_features: int = 5, n_contract_features: int = 3, seed: int = 0
) -> World:
    """Append pure-noise covariates at **both** the event and contract level.

    The split matters, and it makes this null world *harder*, not easier. Contract-level noise
    averages out within an event, so it can barely correlate with an outcome that resolves once per
    event - it is nearly harmless. **Event-level** noise is the dangerous kind: with 40 events there
    are only 40 effective outcomes, so a handful of event-constant covariates will fit some of them
    by chance every time. That is the channel through which clustered data actually gets overfit,
    and a harness without it would let the pipeline pass for the wrong reason.
    """
    rng = random.Random(seed)
    per_event: dict[int, list[float]] = {
        c: [rng.gauss(0.0, 1.0) for _ in range(n_event_features)]
        for c in sorted(set(world.cluster_ids))
    }
    features = [
        (world.features[i] if world.features else [])
        + per_event[world.cluster_ids[i]]
        + [rng.gauss(0.0, 1.0) for _ in range(n_contract_features)]
        for i in range(len(world))
    ]
    return replace(world, name=f"{world.name}+noise", features=features)


def microstructure_placebo(
    n_events: int = 40, contracts_per_event: int = 10, *, seed: int = 0
) -> World:
    """A fair market dressed in realistic-looking but uninformative microstructure.

    Spread, depth imbalance and volume are generated independently of the outcome. This is the null
    for "order-book features predict resolution".
    """
    rng = random.Random(seed)
    base = fair_market(n_events, contracts_per_event, seed=seed)
    features: list[list[float]] = []
    for _ in range(len(base)):
        spread = abs(rng.gauss(0.01, 0.004))
        depth_imbalance = rng.gauss(0.0, 1.0)
        volume = abs(rng.gauss(500.0, 200.0))
        trade_intensity = abs(rng.gauss(1.0, 0.4))
        features.append([spread, depth_imbalance, math.log1p(volume), trade_intensity])
    return replace(base, name="microstructure_placebo", features=features)


def inject_signal(
    n_events: int = 40,
    contracts_per_event: int = 10,
    *,
    compression: float = 0.55,
    seed: int = 0,
    n_noise: int = 5,
) -> World:
    """**Positive control.** A market that compresses the truth, plus a feature that reveals it.

    The market quotes ``expit(compression * logit(pi))`` while the first feature is ``logit(pi)``
    with noise. A genuine, learnable edge exists, so the harness *must* detect it. Failure to do so
    means the instrument is inert and Gate 0 fails regardless of its false-positive record.
    """
    rng = random.Random(seed)
    market: list[float] = []
    outcomes: list[float] = []
    clusters: list[int] = []
    features: list[list[float]] = []
    truth: list[float] = []
    for event in range(n_events):
        pi = rng.uniform(0.05, 0.95)
        y = 1.0 if rng.random() < pi else 0.0
        quoted = _expit(compression * _logit(pi))
        informative = _logit(pi) + rng.gauss(0.0, 0.25)
        for _ in range(contracts_per_event):
            market.append(quoted)
            truth.append(pi)
            outcomes.append(y)
            clusters.append(event)
            features.append([informative] + [rng.gauss(0.0, 1.0) for _ in range(n_noise)])
    return World(
        "positive_control", market, outcomes, clusters, features, truth=truth, has_signal=True
    )


def inject_banded_signal(
    n_events: int = 40,
    contracts_per_event: int = 10,
    *,
    bias: float = 0.8,
    band: tuple[float, float] = (0.40, 0.60),
    seed: int = 0,
    n_noise: int = 5,
) -> World:
    """**Positive control with the signal concentrated in one price band.**

    :func:`inject_signal` misprices at every price, so it can only ever say how a protocol behaves
    against a *diffuse* edge. The entire case for stratifying is that a real edge is **not** diffuse
    — the favourite-longshot literature locates bias at particular prices — and a protocol tested
    only against diffuse signal has not been tested against the hypothesis it exists to evaluate.

    Here the market is honest outside ``band`` and shifted by ``bias`` inside it. A shift is used
    rather than the compression of :func:`inject_signal` deliberately: compression pulls toward 0.5
    and so vanishes near 0.5, which would make a mid-band control weakest exactly where it needs to
    be strongest. A shift keeps the mispricing the same size wherever the band is put.

    Note what this does to a **globally** fitted forecaster: the correction it needs to learn is
    ``-bias`` inside the band and ``0`` outside, and one global tilt cannot express that. Losing
    power on this world is the expected behaviour of the unstratified protocol, not a defect.

    **The band is defined on the quoted price, because that is the only thing anything downstream
    can see.** The first version banded on ``pi`` instead, and at ``bias=1.6`` that put a ``pi=0.5``
    contract at a quote of 0.83 — mixed in with honest contracts genuinely worth 0.83. The world
    then held a signal concentrated in a band *nobody could condition on*, and every protocol tested
    against it was being asked to exploit information the world had hidden. A control that does not
    contain the hypothesis it names cannot falsify it.
    """
    rng = random.Random(seed)
    market: list[float] = []
    outcomes: list[float] = []
    clusters: list[int] = []
    features: list[list[float]] = []
    truth: list[float] = []
    lo, hi = band
    for event in range(n_events):
        pi = rng.uniform(0.05, 0.95)
        y = 1.0 if rng.random() < pi else 0.0
        shifted = _expit(_logit(pi) + bias)
        quoted = shifted if lo <= shifted < hi else pi
        informative = _logit(pi) + rng.gauss(0.0, 0.25)
        for _ in range(contracts_per_event):
            market.append(quoted)
            truth.append(pi)
            outcomes.append(y)
            clusters.append(event)
            features.append([informative] + [rng.gauss(0.0, 1.0) for _ in range(n_noise)])
    return World(
        "banded_signal", market, outcomes, clusters, features, truth=truth, has_signal=True
    )


def achievable_oracle(world: World) -> list[float]:
    """Best forecast obtainable from the observable features — the ceiling for **any** world.

    ``expit(feature_0)``, the informative feature read straight off. Unlike
    :func:`oracle_forecast` this makes no assumption about how the market was distorted, so it works
    for banded worlds too. It is a ceiling, never a gate.
    """
    return [_expit(row[0]) for row in world.features]


# ---------------------------------------------------------------------------
# The adaptive search this gate is really testing
# ---------------------------------------------------------------------------


def _fit_tilt(
    world: World,
    fit_indices: Sequence[int],
    feature_idx: Sequence[int],
    *,
    steps: int = 80,
    lr: float = 0.8,
) -> list[float]:
    """Fit ``p = expit(logit(q) + b + sum beta_k x_k)`` by gradient ascent on log-likelihood.

    ``logit(q)`` enters as a fixed offset, so the fitted tilt is exactly "what the model adds to the
    market". Gradient ascent rather than Newton keeps this dependency-free and robust; the harness
    needs a *plausible* fitter, not an optimal one - what matters is that candidates are fitted to
    the selection data, because that is what manufactures adaptive overfitting.
    """
    if not fit_indices:
        raise ValueError("cannot fit on an empty index set")
    # Offsets are computed here with this module's own logit, then handed to the shared fitter.
    # Passing offsets rather than prices keeps the numerics identical to the pre-refactor version
    # regardless of the two modules' differing clip epsilons - verified by an equivalence test.
    offsets = [_logit(world.market[i]) for i in fit_indices]
    xs = [[world.features[i][j] for j in feature_idx] for i in fit_indices]
    ys = [world.outcomes[i] for i in fit_indices]
    bias, beta = fit_logit_tilt(offsets, xs, ys, steps=steps, lr=lr)

    out: list[float] = []
    for i in range(len(world)):
        x = [world.features[i][j] for j in feature_idx]
        out.append(_expit(_logit(world.market[i]) + bias + sum(b * v for b, v in zip(beta, x))))
    return out


def candidate_forecasters(
    world: World, n_candidates: int, fit_indices: Sequence[int], *, seed: int = 0
) -> list[list[float]]:
    """Generate candidate forecasts by **fitting** market-anchored tilts on random feature subsets.

    Each candidate picks a random subset of the available covariates and fits its coefficients on
    ``fit_indices``. This stands in for an LLM research loop: a cheap generator of many plausible
    hypotheses, each estimated against the same data. It reproduces adaptive overfitting *without*
    needing an LLM in the loop, because the danger Dwork et al. identify is a property of adaptive
    reuse, not of the generator's intelligence (``docs/AXIOMS.md`` C5).

    Fitting is essential. Randomly-guessed coefficients on a calibrated market almost always lose,
    which would make the harness pass for the wrong reason - it would be measuring a search too weak
    to overfit rather than a protocol strong enough to resist it.
    """
    if n_candidates < 1:
        raise ValueError(f"n_candidates must be >= 1, got {n_candidates!r}")
    width = len(world.features[0]) if world.features else 0
    if width == 0:
        raise ValueError(
            f"world {world.name!r} has no features; a candidate search needs something to search"
        )
    rng = random.Random(seed)
    out: list[list[float]] = []
    for _ in range(n_candidates):
        size = rng.randint(1, min(4, width))
        subset = rng.sample(range(width), size)
        out.append(_fit_tilt(world, fit_indices, subset))
    return out


def _split_by_cluster(world: World, *, seed: int = 0) -> tuple[list[int], list[int], list[int]]:
    """Split indices into fit / select / sealed-holdout **by event**, never by row.

    Three ways, not two. The first version of this harness split dev/holdout and then chose the best
    candidate by its *fit-set* score - and the positive control went undetected, because an overfit
    noise candidate always beats the true one in sample. Gate 0 caught that, which is what it is
    for. Selection now happens on data the candidate was not fitted on, matching the
    development -> validation -> sealed-holdout ladder already registered in ``docs/PROTOCOL.md``.

    Splitting by row rather than by event would leak outright: contracts on the same event resolve
    together, so a candidate fitted on one contract has already seen its sibling's outcome.
    """
    rng = random.Random(seed)
    clusters = sorted(set(world.cluster_ids))
    rng.shuffle(clusters)
    n = len(clusters)
    a, b = n // 3, (2 * n) // 3
    fit_c, sel_c = set(clusters[:a]), set(clusters[a:b])
    fit, select, holdout = [], [], []
    for i, c in enumerate(world.cluster_ids):
        (fit if c in fit_c else select if c in sel_c else holdout).append(i)
    return fit, select, holdout


def _subset(values: Sequence, indices: Sequence[int]) -> list:
    return [values[i] for i in indices]


def _best_candidate(
    candidates: Sequence[Sequence[float]],
    world: World,
    indices: Sequence[int],
) -> int:
    """Index of the candidate with the highest mean score advantage on ``indices``."""
    market = _subset(world.market, indices)
    outcomes = _subset(world.outcomes, indices)
    best_i, best_score = 0, -math.inf
    for i, cand in enumerate(candidates):
        deltas = paired_deltas(_subset(cand, indices), market, outcomes)
        mean = sum(deltas) / len(deltas)
        if mean > best_score:
            best_i, best_score = i, mean
    return best_i


#: Price bands, **pre-registered from the literature and never from the data**.
#:
#: The favourite-longshot bias is defined on price, so price is where the published claims live and
#: the partition is not ours to choose. The extremes are split off because a contract at 0.03 with a
#: 0.033 base rate carries almost no available information: the market is nearly certain and nearly
#: right, and rows like that dilute a mean score difference toward zero without contributing
#: evidence either way. Restocchi et al. and Whelan both locate the bias at the ends; Page et al.
#: locate a horizon effect independently, which is why lead time is a separate axis and not folded
#: in here.
#:
#: These bounds are frozen. Moving them after seeing a result converts the test into a search over
#: cut points, which the max-t correction does **not** cover (``docs/AXIOMS.md`` A8, C7).
PRICE_STRATA: tuple[tuple[str, float, float], ...] = (
    ("longshot", 0.02, 0.15),
    ("lowmid", 0.15, 0.40),
    ("mid", 0.40, 0.60),
    ("highmid", 0.60, 0.85),
    ("favourite", 0.85, 0.98),
)


def stratify_by_price(prices: Sequence[float]) -> list[str]:
    """Label each observation with its pre-registered price band.

    Prices outside every band get ``"unbanded"``, which the minimum-cluster rule then usually drops.
    Silently folding them into a neighbour would move a frozen boundary.
    """
    out: list[str] = []
    for p in prices:
        label = "unbanded"
        for name, lo, hi in PRICE_STRATA:
            if lo <= p < hi:
                label = name
                break
        out.append(label)
    return out


@dataclass(frozen=True)
class _AsUncorrected:
    """Adapter exposing the uncorrected verdict of a stratified search as ``significant``.

    Lets the harness count how often reporting the winning stratum's own p-value would have declared
    an edge in a world built to contain none.
    """

    inner: MaxStatisticResult

    @property
    def significant(self) -> bool:
        return self.inner.significant_uncorrected


def oracle_forecast(world: World, compression: float) -> list[float]:
    """The best forecast obtainable in a positive-control world - the power **ceiling**.

    Uses the world's own generating parameters, so no method can beat it. Its detection rate answers
    the question that separates a broken pipeline from an undersized sample: if the oracle cannot be
    detected, nothing can, and the correct conclusion is "gather more events", never "the pipeline
    is inert". Reporting it is what makes a power failure interpretable (``docs/AXIOMS.md`` A1).
    """
    if world.truth is None:
        raise ValueError(f"world {world.name!r} has no truth to build an oracle from")
    return [
        _expit(_logit(world.market[i]) + (1.0 - compression) * world.features[i][0])
        for i in range(len(world))
    ]


def run_all_protocols(
    world: World,
    *,
    n_candidates: int,
    alpha: float,
    n_boot: int,
    seed: int,
    compression: float | None = None,
) -> dict[str, object]:
    """Run every protocol on one world, sharing the expensive candidate fits.

    ``naive`` and ``cluster`` differ only in their inference, so they share one in-sample candidate
    set; ``kairos`` needs its own, fitted on the fit split alone. When ``compression`` is supplied
    the oracle ceiling is measured on the same sealed holdout, making the two power numbers directly
    comparable.
    """
    all_idx = list(range(len(world)))

    in_sample = candidate_forecasters(world, n_candidates, all_idx, seed=seed)
    best_in = _best_candidate(in_sample, world, all_idx)
    deltas = paired_deltas(in_sample[best_in], world.market, world.outcomes)

    fit, select, holdout = _split_by_cluster(world, seed=seed)
    sealed = candidate_forecasters(world, n_candidates, fit, seed=seed)
    best_sealed = _best_candidate(sealed, world, select)

    out = {
        "naive": iid_bootstrap_test(deltas, alpha=alpha, n_boot=n_boot, seed=seed),
        "cluster": cluster_bootstrap_test(
            deltas, world.cluster_ids, alpha=alpha, n_boot=n_boot, seed=seed
        ),
        "kairos": superiority_test(
            _subset(sealed[best_sealed], holdout),
            _subset(world.market, holdout),
            _subset(world.outcomes, holdout),
            _subset(world.cluster_ids, holdout),
            alpha=alpha,
            n_boot=n_boot,
            seed=seed,
        ),
    }
    # ---- the stratified search, and the price of running it ----
    # Same sealed candidate, same sealed holdout. The only thing added is that the holdout is cut
    # into pre-registered price bands and the best band is reported, which is a search whether or
    # not it is described as one. `strat_naive` reports the winner's own p-value and is expected to
    # over-reject; `strat_maxt` prices the search against the distribution of the maximum.
    try:
        strat = max_statistic_test(
            paired_deltas(
                _subset(sealed[best_sealed], holdout),
                _subset(world.market, holdout),
                _subset(world.outcomes, holdout),
            ),
            _subset(world.cluster_ids, holdout),
            stratify_by_price(_subset(world.market, holdout)),
            alpha=alpha,
            n_boot=n_boot,
            seed=seed,
        )
    except InferenceError:
        # No band reached the minimum event count. Recording nothing is correct; recording a
        # non-detection would quietly credit the protocol with a true negative it never earned.
        pass
    else:
        out["strat_naive"] = _AsUncorrected(strat)
        out["strat_maxt"] = strat

    if compression is not None and world.truth is not None:
        orc = oracle_forecast(world, compression)
        out["oracle"] = superiority_test(
            _subset(orc, holdout),
            _subset(world.market, holdout),
            _subset(world.outcomes, holdout),
            _subset(world.cluster_ids, holdout),
            alpha=alpha,
            n_boot=n_boot,
            seed=seed,
        )
    return out


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _binomial_tail(k: int, n: int, p: float) -> float:
    """Exact P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * p**i * (1.0 - p) ** (n - i) for i in range(k, n + 1))


@dataclass(frozen=True)
class WorldReport:
    world: str
    has_signal: bool
    protocol: str
    replications: int
    detections: int

    @property
    def rate(self) -> float:
        return self.detections / self.replications

    @property
    def binomial_tail(self) -> float:
        """P(at least this many detections | true rate = ALPHA)."""
        return _binomial_tail(self.detections, self.replications, ALPHA)

    @property
    def is_gate_condition(self) -> bool:
        """Only sealed protocols are gated, and only the strong signal gates power.

        ``naive``, ``cluster`` and ``strat_naive`` are exhibits: they exist to show what the
        discipline is buying, and they are *expected* to fail. ``oracle`` is a diagnostic ceiling,
        not a gate. The moderate and weak controls document the power curve.

        ``strat_maxt`` **was** gated on both counts while the decision to adopt stratification was
        live: a correction that restores the false-positive rate by making the test unable to detect
        anything has not fixed the search, and only a power floor catches that.

        **Demoted to an exhibit 2026-09-09, and the reason matters because this looks like A8.**
        Gate 0b answered the question `strat_maxt` was added to answer: test-only stratification
        detects *less* than not stratifying on both signal shapes, and no stratified result may be
        reported. It is a **rejected candidate protocol, not part of the pipeline**. Leaving it as a
        gate condition meant Gate 0 reported ``FAIL`` for the pipeline actually in use — on the
        strength of a protocol deliberately not used — while ``kairos`` passed at 0.667 against a
        0.500 floor with a worst null rate of 0.083.

        This is not tuning a falsifier until the system passes it. Nothing about the stratified
        protocol is rescued: it stays rejected, its numbers stay printed, and it simply stops
        vetoing a verdict on a different protocol. Recorded in ``docs/CORRECTIONS.md`` Pass 15
        precisely because the shape of the change resembles the thing A8 forbids.
        """
        if self.protocol != "kairos":
            return False
        return (not self.has_signal) or self.world == "signal_strong"

    @property
    def verdict(self) -> str:
        if not self.is_gate_condition:
            return "exhibit"
        if self.has_signal:
            return "PASS" if self.rate >= POWER_FLOOR else "FAIL (inert)"
        return "PASS" if self.binomial_tail >= FPR_TAIL_ALPHA else "FAIL (over-rejects)"


@dataclass(frozen=True)
class GateReport:
    reports: tuple[WorldReport, ...]

    @property
    def gate_conditions(self) -> tuple[WorldReport, ...]:
        return tuple(r for r in self.reports if r.is_gate_condition)

    @property
    def passed(self) -> bool:
        conditions = self.gate_conditions
        return bool(conditions) and all(r.verdict == "PASS" for r in conditions)

    @property
    def power_curve(self) -> tuple[tuple[str, float, float], ...]:
        """``(world, kairos power, oracle ceiling)`` for each positive control."""
        oracle = {
            r.world: r.rate for r in self.reports if r.protocol == "oracle"
        }
        return tuple(
            (r.world, r.rate, oracle.get(r.world, float("nan")))
            for r in self.reports
            if r.has_signal and r.protocol == "kairos"
        )

    @property
    def oracle_power(self) -> float:
        """Detection rate of the best possible forecaster on the strong control."""
        for r in self.reports:
            if r.protocol == "oracle" and r.world == "signal_strong":
                return r.rate
        return float("nan")

    @property
    def harness_valid(self) -> bool:
        """Whether the harness itself can detect an oracle at this sample size.

        If this is False, a power failure is a statement about the **harness**, not the pipeline,
        and the honest response is more events - not a verdict about Kairos.
        """
        power = self.oracle_power
        return power == power and power >= POWER_FLOOR  # NaN-safe

    @property
    def worst_null_rate(self) -> float:
        nulls = [r.rate for r in self.reports if not r.has_signal and r.protocol == "kairos"]
        return max(nulls) if nulls else 0.0

    def explain(self) -> str:
        lines = [
            f"{'world':<30} {'protocol':<9} {'signal':<7} {'rate':>7} {'binom p':>9}  verdict",
            "-" * 86,
        ]
        for r in self.reports:
            tail = f"{r.binomial_tail:9.4f}" if r.is_gate_condition and not r.has_signal else "-"
            lines.append(
                f"{r.world:<30} {r.protocol:<9} {str(r.has_signal):<7} "
                f"{r.rate:7.3f} {tail:>9}  {r.verdict}"
            )
        lines.append("-" * 86)
        lines.append(f"{'power curve':<24} {'kairos':>8} {'oracle':>8}   (oracle = ceiling)")
        for world, rate, ceiling in self.power_curve:
            flag = "  <- gate condition" if world == "signal_strong" else ""
            lines.append(f"    {world:<20} {rate:8.3f} {ceiling:8.3f}{flag}")
        lines.append("-" * 86)
        if not self.harness_valid:
            lines.append(
                f"HARNESS UNDERPOWERED: the oracle itself is only detected "
                f"{self.oracle_power:.3f} of the time on the strong control. A power failure here "
                f"is a statement about sample size, NOT about the pipeline. Increase N_EVENTS."
            )
        lines.append(
            f"GATE 0: {'PASS' if self.passed else 'FAIL'}   "
            f"(alpha={ALPHA}, power floor={POWER_FLOOR}, "
            f"worst null rate={self.worst_null_rate:.3f}, oracle ceiling={self.oracle_power:.3f})"
        )
        return "\n".join(lines)


#: World size. Set from a **measurement**, not a guess: the oracle power curve below shows that a
#: perfect forecaster facing a badly-miscalibrated market reaches only 18% power at 20 independent
#: events, 50% at 80, and 93% at 320. A harness whose test split cannot detect an oracle cannot
#: distinguish "the pipeline is inert" from "the sample is too small", so the split is sized above
#: that threshold. See ``docs/EVIDENCE.md`` and ``docs/CORRECTIONS.md`` (Gate 0 findings).
#:
#: Measured oracle power (compression 0.35, one-sided alpha=0.05):
#:
#: ===========  ======  ======  ======  ======  ======  ======
#: test events      20      40      80     160     320     640
#: oracle power  0.183   0.333   0.500   0.667   0.933   1.000
#: ===========  ======  ======  ======  ======  ======  ======
N_EVENTS = 750
CONTRACTS_PER_EVENT = 4

#: Positive controls at three signal strengths. Lower ``compression`` = larger market error = easier
#: edge. The **gate condition is the strong control only**; the others document where sensitivity
#: dies, which is more useful than a single pass/fail and keeps us honest about power (AXIOMS A1).
SIGNAL_LADDER: tuple[tuple[str, float, float], ...] = (
    ("signal_strong", 0.35, 0.15),
    ("signal_moderate", 0.55, 0.25),
    ("signal_weak", 0.75, 0.35),
)


def _null_world_builders() -> list[Callable[[int], World]]:
    size = dict(n_events=N_EVENTS, contracts_per_event=CONTRACTS_PER_EVENT)
    return [
        lambda s: add_noise_features(fair_market(**size, seed=s), seed=s),
        lambda s: add_noise_features(martingale_market(**size, seed=s), seed=s),
        lambda s: add_noise_features(
            shuffle_outcomes(fair_market(**size, seed=s), seed=s + 1), seed=s
        ),
        lambda s: time_shift_features(add_noise_features(fair_market(**size, seed=s), seed=s)),
        lambda s: add_noise_features(microstructure_placebo(**size, seed=s), seed=s),
    ]


def _signal_world_builders() -> list[tuple[str, Callable[[int], World]]]:
    def make(compression: float, noise: float) -> Callable[[int], World]:
        def build(s: int) -> World:
            rng_seed = s
            world = inject_signal(
                n_events=N_EVENTS,
                contracts_per_event=CONTRACTS_PER_EVENT,
                compression=compression,
                seed=rng_seed,
            )
            return replace(world, features=_renoise(world, noise, rng_seed))

        return build

    return [(name, make(c, n)) for name, c, n in SIGNAL_LADDER]


def _renoise(world: World, noise: float, seed: int) -> list[list[float]]:
    """Re-draw the informative feature's observation noise at the requested level."""
    rng = random.Random(seed + 7717)
    assert world.truth is not None
    out: list[list[float]] = []
    per_event: dict[int, float] = {}
    for i, row in enumerate(world.features):
        c = world.cluster_ids[i]
        if c not in per_event:
            per_event[c] = _logit(world.truth[i]) + rng.gauss(0.0, noise)
        out.append([per_event[c]] + list(row[1:]))
    return out


def run_gate0(
    *,
    replications: int = 40,
    n_candidates: int = 16,
    n_boot: int = 250,
    alpha: float = ALPHA,
    seed: int = 20260908,
    progress: Callable[[str], None] | None = None,
) -> GateReport:
    """Run the full Gate-0 harness.

    Each world is rebuilt with a fresh seed per replication, a fitted candidate search runs on it,
    and every protocol is asked whether it found an edge. Detections in a null world are false
    positives; detections in a positive control are power.
    """
    reports: list[WorldReport] = []
    jobs: list[tuple[str, bool, Callable[[int], World]]] = [
        (build(seed).name, False, build) for build in _null_world_builders()
    ] + [(name, True, build) for name, build in _signal_world_builders()]

    compressions = {name: c for name, c, _ in SIGNAL_LADDER}

    for name, has_signal, build in jobs:
        hits: dict[str, int] = {}
        tries: dict[str, int] = {}
        for r in range(replications):
            world = build(seed + r * 101)
            results = run_all_protocols(
                world,
                n_candidates=n_candidates,
                alpha=alpha,
                n_boot=n_boot,
                seed=seed + r * 101,
                compression=compressions.get(name),
            )
            for protocol, result in results.items():
                hits[protocol] = hits.get(protocol, 0) + result.significant
                tries[protocol] = tries.get(protocol, 0) + 1
        for protocol, count in hits.items():
            # Denominator is attempts, not replications: a protocol that could not run in some
            # replication must not be credited with a true negative it never produced (AXIOMS A6).
            reports.append(WorldReport(name, has_signal, protocol, tries[protocol], count))
        if progress:
            progress(f"{name}: {hits}")

    return GateReport(tuple(reports))
