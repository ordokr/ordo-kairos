"""Gate 1 — does ``q_ref`` earn its existence?

    python gate1.py [--pages N] [--limit M] [--lead-hours H]

``docs/PROTOCOL.md`` Gate 1. Four frozen baselines, each fitted **strictly on events that resolved
earlier** and evaluated on later ones, with a sealed final holdout queried exactly once:

===========  ============================================================
``A_raw``    the quoted price, untransformed
``B_settle`` settlement un-discounting only
``C_logit``  logistic (logit-space) recalibration only
``C_iso``    isotonic recalibration only — the competing family
``D_both``   settlement + logistic recalibration
===========  ============================================================

**The simplest survivor wins** (AXIOMS C9). A more complex baseline is kept only if it shows a
reproducible out-of-sample gain over ``A_raw`` on the rolling folds *and* survives the sealed
holdout. Anything that does not is deleted, not retained "for later".

This gate also settles the double-counting question that code order cannot (AXIOMS C7): if
``B_settle`` and ``D_both`` are indistinguishable, the recalibration is re-learning what the
settlement adjustment already removed, and one of them goes.

No forecaster is involved. Gate 1 asks only whether *transforming the market price* predicts
outcomes better than the raw price.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from typing import Callable, Sequence

from kairos.baseline import LogitRecalibration, MarketBaseline, SettlementTerms
from kairos.calibration import IsotonicCalibrator
from kairos.economics import effective_sample_size
from kairos.inference import superiority_test
from kairos.polymarket import Observation, build_dataset, fetch_resolved_markets
from kairos.score import log_score

#: Gate 0's measured requirement. Below this the gate reports INSUFFICIENT rather than a verdict.
REQUIRED_EVENTS = 300

#: Probabilities are clipped into this band before scoring. Settlement un-discounting saturates at
#: 1.0, and an unclipped 1.0 against a 0 outcome contributes ~34 nats — one such row would dominate
#: every comparison and the result would measure the clip, not the baseline.
EPS = 1e-4

ALPHA = 0.05

#: A survivor must clear BOTH significance and materiality: its log-score gain must be at least
#: this fraction of the benchmark's own log score.
#:
#: Added after Gate-1 run 1, where ``B_settle`` was declared a survivor on p=0.0005 with a mean
#: gain of **+0.00008 nats** - 0.024% of a 0.336 benchmark. It was significant because the
#: settlement adjustment is a tiny, deterministic, monotone transform, so the paired differences
#: have almost no variance (cluster SE 0.00002). Significance without materiality.
#:
#: **This change does not alter run 1's verdict.** With the threshold applied, ``B_settle`` is
#: excluded on materiality; ``C_logit``/``D_both`` are already excluded on significance (p≈0.11);
#: no survivors remain, ``A_raw`` is chosen, and the verdict is q_ref REJECTED either way. Recorded
#: in docs/CORRECTIONS.md so the rule change is not mistaken for a post-hoc rescue.
MIN_RELATIVE_GAIN = 0.01


def clip(p: float) -> float:
    return min(max(p, EPS), 1.0 - EPS)


Predictor = Callable[[Observation], float]


@dataclass(frozen=True)
class BaselineSpec:
    name: str
    complexity: int
    fit: Callable[[Sequence[Observation]], Predictor]

    def __str__(self) -> str:
        return self.name


def _fit_raw(_train: Sequence[Observation]) -> Predictor:
    return lambda o: clip(o.price)


def _fit_settle(_train: Sequence[Observation]) -> Predictor:
    # Deterministic given the wedge; nothing is learned from the training set, which is exactly
    # why it must still be tested — an unlearned transformation can still be wrong.
    return lambda o: clip(
        SettlementTerms(days_to_settlement=o.days_to_resolution).undiscount(o.price)
    )


def _fit_logit(train: Sequence[Observation]) -> Predictor:
    cal = LogitRecalibration.fit([o.price for o in train], [o.outcome for o in train])
    return lambda o: clip(cal.apply(o.price))


def _fit_iso(train: Sequence[Observation]) -> Predictor:
    cal = IsotonicCalibrator().fit([o.price for o in train], [o.outcome for o in train])
    return lambda o: clip(cal.predict(o.price))


def _fit_both(train: Sequence[Observation]) -> Predictor:
    base = MarketBaseline.fit(
        [o.price for o in train],
        [o.outcome for o in train],
        [o.days_to_resolution for o in train],
    )
    return lambda o: clip(base.fair_probability(o.price, o.days_to_resolution))


BASELINES: tuple[BaselineSpec, ...] = (
    BaselineSpec("A_raw", 0, _fit_raw),
    BaselineSpec("B_settle", 1, _fit_settle),
    BaselineSpec("C_logit", 1, _fit_logit),
    BaselineSpec("C_iso", 1, _fit_iso),
    BaselineSpec("D_both", 2, _fit_both),
)


def cluster_order(obs: Sequence[Observation]) -> list[str]:
    """Event clusters in chronological order of their *earliest* resolution."""
    first: dict[str, int] = {}
    for o in obs:
        first.setdefault(o.cluster_id, o.resolution_ts)
        first[o.cluster_id] = min(first[o.cluster_id], o.resolution_ts)
    return sorted(first, key=lambda c: first[c])


def rolling_oos(
    obs: Sequence[Observation], clusters: Sequence[str], n_folds: int
) -> dict[str, list[float]]:
    """Expanding-window predictions. Every prediction is made by a model fitted only on the past.

    Splitting by cluster rather than by row is not a nicety: contracts on one event resolve
    together, so a row-wise split would put a sibling of the test row in the training set.
    """
    by_cluster: dict[str, list[Observation]] = {}
    for o in obs:
        by_cluster.setdefault(o.cluster_id, []).append(o)

    n = len(clusters)
    start = max(n // 3, 2)  # first third seeds the initial fit
    if n - start < n_folds:
        n_folds = max(1, n - start)
    edges = [start + round(i * (n - start) / n_folds) for i in range(n_folds + 1)]

    preds: dict[str, list[float]] = {b.name: [] for b in BASELINES}
    preds["_outcome"] = []
    preds["_cluster"] = []  # type: ignore[assignment]

    for f in range(n_folds):
        lo, hi = edges[f], edges[f + 1]
        if hi <= lo:
            continue
        train = [o for c in clusters[:lo] for o in by_cluster[c]]
        test = [o for c in clusters[lo:hi] for o in by_cluster[c]]
        if len(train) < 20 or not test:
            continue
        fitted = {b.name: b.fit(train) for b in BASELINES}
        for o in test:
            for b in BASELINES:
                preds[b.name].append(fitted[b.name](o))
            preds["_outcome"].append(o.outcome)
            preds["_cluster"].append(o.cluster_id)  # type: ignore[arg-type]
    return preds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=40)
    ap.add_argument("--limit", type=int, default=900)
    ap.add_argument("--lead-hours", type=float, default=24.0)
    ap.add_argument("--min-points", type=int, default=5)
    ap.add_argument("--folds", type=int, default=6)
    ap.add_argument("--holdout-frac", type=float, default=0.25)
    args = ap.parse_args()

    print("=" * 82)
    print("GATE 1 - DOES q_ref EARN ITS EXISTENCE?")
    print("=" * 82)
    print("\nFetching resolved markets (cached outside the repo)...", flush=True)
    markets = fetch_resolved_markets(args.pages)
    print(f"  markets available: {len(markets)}")
    if not markets:
        print("No market data. Gate 1 cannot run.")
        return 1

    print("\nBuilding dataset (admission by MEASURED history density)...", flush=True)
    obs, reasons = build_dataset(
        markets,
        min_points=args.min_points,
        lead_hours=args.lead_hours,
        limit=args.limit,
        progress=lambda s: print(f"  {s}", flush=True),
    )
    print("\n  admission census:")
    for k, v in reasons.items():
        print(f"    {k:28s} {v}")

    clusters = cluster_order(obs)
    n_eff = effective_sample_size([sum(1 for o in obs if o.cluster_id == c) for c in clusters]) \
        if clusters else 0.0
    print(f"\n  observations           {len(obs)}")
    print(f"  independent events     {len(clusters)}  (effective n {n_eff:.0f})")
    print(f"  Gate-0 requirement     {REQUIRED_EVENTS}")

    if len(clusters) < REQUIRED_EVENTS:
        print(f"\n  -> INSUFFICIENT. {len(clusters)} events is below the measured power")
        print("     requirement. Gate 1 reports no verdict: 'not enough evidence' is not")
        print("     'no effect' (docs/AXIOMS.md A1). Raise --pages/--limit and re-run.")
        return 2

    # Sealed final holdout: the most recent events, untouched until the single query at the end.
    cut = int(len(clusters) * (1 - args.holdout_frac))
    dev_clusters, sealed_clusters = clusters[:cut], clusters[cut:]
    dev = [o for o in obs if o.cluster_id in set(dev_clusters)]
    sealed = [o for o in obs if o.cluster_id in set(sealed_clusters)]
    print(f"\n  development events     {len(dev_clusters)}  ({len(dev)} rows)")
    print(f"  SEALED holdout events  {len(sealed_clusters)}  ({len(sealed)} rows) - queried once")

    print(f"\n{'=' * 82}\nROLLING EXPANDING-WINDOW FOLDS (development only)\n{'=' * 82}")
    preds = rolling_oos(dev, dev_clusters, args.folds)
    outcomes = preds["_outcome"]
    cl = preds["_cluster"]
    if not outcomes:
        print("No out-of-sample predictions produced. Gate 1 inconclusive.")
        return 1
    print(f"  out-of-sample predictions: {len(outcomes)} rows in {len(set(cl))} events\n")

    raw = preds["A_raw"]
    print(f"  {'baseline':<10} {'complexity':>10} {'log score':>10} {'vs A_raw':>10} "
          f"{'p':>8}   verdict")
    print(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*8}   {'-'*22}")
    results = {}
    for b in BASELINES:
        p = preds[b.name]
        ls = log_score(p, outcomes)
        if b.name == "A_raw":
            print(f"  {b.name:<10} {b.complexity:>10} {ls:>10.5f} {'-':>10} {'-':>8}   benchmark")
            results[b.name] = (ls, 0.0, 1.0, False)
            continue
        r = superiority_test(p, raw, outcomes, cl, alpha=ALPHA, n_boot=2000, seed=1)
        material = r.mean_delta >= MIN_RELATIVE_GAIN * results["A_raw"][0]
        beats = r.significant and material
        if r.significant and not material:
            note = f"significant but immaterial ({r.mean_delta / results['A_raw'][0]:.2%})"
        elif beats:
            note = "BEATS RAW"
        else:
            note = "no reproducible gain"
        results[b.name] = (ls, r.mean_delta, r.p_value, beats)
        print(f"  {b.name:<10} {b.complexity:>10} {ls:>10.5f} {r.mean_delta:>+10.5f} "
              f"{r.p_value:>8.4f}   {note}")

    survivors = [b for b in BASELINES if b.name != "A_raw" and results[b.name][3]]
    print(f"\n{'=' * 82}\nSELECTION (simplest survivor - AXIOMS C9)\n{'=' * 82}")
    if not survivors:
        chosen = BASELINES[0]
        print("  No transformation beat the raw quote out of sample.")
        print("  -> q_ref does NOT earn its existence. Keep A_raw; delete the rest.")
    else:
        chosen = min(survivors, key=lambda b: (b.complexity, -results[b.name][1]))
        print(f"  survivors: {', '.join(s.name for s in survivors)}")
        print(f"  -> simplest survivor: {chosen.name}")

    # Double-counting check (AXIOMS C7): code order cannot establish orthogonality; this can.
    if results.get("B_settle") and results.get("D_both"):
        gap = results["D_both"][0] - results["B_settle"][0]
        print(f"\n  double-counting check: log score D_both - B_settle = {gap:+.5f}")
        if abs(gap) < 1e-3:
            print("    indistinguishable -> the recalibration is re-learning the settlement")
            print("    adjustment. One of them must go.")

    print(f"\n{'=' * 82}\nSEALED HOLDOUT - QUERIED ONCE\n{'=' * 82}")
    fitted_dev = chosen.fit(dev)
    fitted_raw = BASELINES[0].fit(dev)
    hp = [fitted_dev(o) for o in sealed]
    hr = [fitted_raw(o) for o in sealed]
    ho = [o.outcome for o in sealed]
    hc = [o.cluster_id for o in sealed]
    if chosen.name == "A_raw":
        print("  Chosen baseline IS the raw quote; no confirmation needed.")
        print(f"  holdout log score (raw): {log_score(hr, ho):.5f}")
        verdict = "q_ref REJECTED - the raw market quote is the benchmark"
    else:
        r = superiority_test(hp, hr, ho, hc, alpha=ALPHA, n_boot=2000, seed=2)
        print(f"  {chosen.name} vs A_raw on {len(ho)} rows / {len(set(hc))} events")
        print(f"  {r.explain()}")
        verdict = (
            f"q_ref CONFIRMED as {chosen.name}" if r.significant
            else f"{chosen.name} won on development but FAILED the sealed holdout - q_ref REJECTED"
        )

    print(f"\n{'=' * 82}\nGATE 1 VERDICT: {verdict}\n{'=' * 82}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
