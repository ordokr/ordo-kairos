"""Gate 2a — can any forecaster add information beyond the market price?

    python gate2.py [--pages N] [--limit M]

``docs/PROTOCOL.md`` Gate 2, ensemble sub-protocol, run **in the registered order and stopping at
the first rung that is not beaten**:

1. market alone
2. best single model
3. simplest cross-model pool
4. market-anchored simple pool

Pairwise forecast-error correlation is measured **before** any pooling, because pooling correlated
opinions is not diversification (AXIOMS C8).

**This is Gate 2a: leakage-free forecasters only.** Every model here sees the decision price and
price-path features computed strictly before the decision point — never the question text. An LLM
forecaster is **Gate 2b** and cannot run on this dataset: these markets resolved inside frontier
model training windows, so any LLM score would measure recall, not foresight. That is the exact
failure Hindcast, KTD-Fin and PolyBench were built to prevent.

Gate 1 established the benchmark: **raw market price**. `q_ref` was rejected.
"""

from __future__ import annotations

import argparse
import itertools

from kairos.forecasters import (
    FORECASTERS,
    ForecasterSpec,
    effective_forecasters,
    error_correlations,
    tilt_correlations,
    logit_pool,
    mean_offdiagonal,
    rolling_oos,
    simple_pool,
)
from kairos.inference import superiority_test
from kairos.polymarket import build_dataset, fetch_resolved_markets
from kairos.score import log_score

REQUIRED_EVENTS = 300
ALPHA = 0.05
#: Same materiality floor Gate 1 adopted after a p=0.0005 win worth 0.02% of the benchmark.
MIN_RELATIVE_GAIN = 0.01


def cluster_order(obs):
    first = {}
    for o in obs:
        first[o.cluster_id] = min(first.get(o.cluster_id, o.resolution_ts), o.resolution_ts)
    return sorted(first, key=lambda c: first[c])


def verdict(name, preds, raw, outcomes, clusters, benchmark_score, seed=1):
    """Significance AND materiality, as Gate 1's correction requires."""
    r = superiority_test(preds, raw, outcomes, clusters, alpha=ALPHA, n_boot=2000, seed=seed)
    material = r.mean_delta >= MIN_RELATIVE_GAIN * benchmark_score
    beats = r.significant and material
    if r.significant and not material:
        note = f"significant but immaterial ({r.mean_delta / benchmark_score:.2%})"
    else:
        note = "BEATS MARKET" if beats else "no reproducible gain"
    return r, beats, note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--limit", type=int, default=900)
    ap.add_argument("--folds", type=int, default=6)
    ap.add_argument("--holdout-frac", type=float, default=0.25)
    args = ap.parse_args()

    print("=" * 84)
    print("GATE 2a - CAN ANY LEAKAGE-FREE FORECASTER BEAT THE MARKET PRICE?")
    print("=" * 84)
    markets = fetch_resolved_markets(args.pages)
    obs, reasons = build_dataset(markets, limit=args.limit)
    clusters = cluster_order(obs)
    print(f"\n  observations {len(obs)}   independent events {len(clusters)}"
          f"   (requirement {REQUIRED_EVENTS})")
    if len(clusters) < REQUIRED_EVENTS:
        print("  -> INSUFFICIENT. No verdict (AXIOMS A1).")
        return 2

    cut = int(len(clusters) * (1 - args.holdout_frac))
    dev_c, sealed_c = clusters[:cut], clusters[cut:]
    dev = [o for o in obs if o.cluster_id in set(dev_c)]
    sealed = [o for o in obs if o.cluster_id in set(sealed_c)]
    print(f"  development {len(dev_c)} events / SEALED holdout {len(sealed_c)} events")

    fitters = {f.name: f.fit for f in FORECASTERS}
    preds = rolling_oos(dev, dev_c, args.folds, fitters)
    outcomes, cl = preds["_outcome"], preds["_cluster"]
    if not outcomes:
        print("  No out-of-sample predictions. Inconclusive.")
        return 1
    raw = preds["market"]
    bench = log_score(raw, outcomes)
    print(f"  out-of-sample: {len(outcomes)} rows in {len(set(cl))} events\n")

    # ---- correlation FIRST, before any pooling machinery exists (AXIOMS C8) ----
    print("=" * 84)
    print("FORECAST-ERROR CORRELATION (measured before pooling)")
    print("=" * 84)
    models = [f.name for f in FORECASTERS if f.name != "market"]
    err = error_correlations({m: preds[m] for m in models}, outcomes)
    tilt = tilt_correlations({m: preds[m] for m in models}, raw)
    print(f"  {'pair':<26} {'rho(error)':>11} {'rho(tilt)':>11}")
    print(f"  {'-' * 26} {'-' * 11} {'-' * 11}")
    for key in sorted(err, key=lambda k: -abs(tilt.get(k, 0.0))):
        a, b = key
        print(f"  {a + ' / ' + b:<26} {err[key]:>+11.4f} {tilt.get(key, float('nan')):>+11.4f}")
    rho_e, rho_t = mean_offdiagonal(err), mean_offdiagonal(tilt)
    print(f"\n  mean rho(error) {rho_e:+.4f}  -> effective forecasters "
          f"{effective_forecasters(len(models), rho_e):.2f}")
    print(f"  mean rho(tilt)  {rho_t:+.4f}  -> effective forecasters "
          f"{effective_forecasters(len(models), rho_t):.2f}")
    print("\n  rho(error) is near-unity BY CONSTRUCTION for market-anchored models: every error is")
    print("  dominated by the shared (q - y) term. rho(tilt) is the diagnostic that survives")
    print("  anchoring - it asks whether the models carry different information (AXIOMS C8).")
    if effective_forecasters(len(models), rho_t) < 2.0:
        print("  -> Naming N models is not having N opinions. Pooling cannot diversify this much.")

    # ---- the ladder, in order, stopping at the first rung not beaten ----
    print(f"\n{'=' * 84}\nENSEMBLE LADDER (stop at the first rung not beaten)\n{'=' * 84}")
    print(f"  rung 1  market alone       log score {bench:.5f}   (benchmark)")

    print(f"\n  rung 2  best single model")
    best_name, best_r, best_beats = None, None, False
    for m in models:
        r, beats, note = verdict(m, preds[m], raw, outcomes, cl, bench)
        print(f"          {m:<12} log {log_score(preds[m], outcomes):.5f}  "
              f"delta {r.mean_delta:+.5f}  p {r.p_value:.4f}   {note}")
        if best_r is None or r.mean_delta > best_r.mean_delta:
            best_name, best_r, best_beats = m, r, beats

    stopped_at = None
    if not best_beats:
        stopped_at = ("rung 2", f"best single model ({best_name}) did not beat the market")
    else:
        pool = simple_pool([preds[m] for m in models])
        r3, beats3, note3 = verdict("simple_pool", pool, raw, outcomes, cl, bench, seed=3)
        print(f"\n  rung 3  simple pool        log {log_score(pool, outcomes):.5f}  "
              f"delta {r3.mean_delta:+.5f}  p {r3.p_value:.4f}   {note3}")
        if not beats3:
            stopped_at = ("rung 3", "simple pool did not beat the market")
        else:
            anchored = logit_pool([raw, pool])
            r4, beats4, note4 = verdict(
                "anchored", anchored, raw, outcomes, cl, bench, seed=4
            )
            print(f"\n  rung 4  anchored pool      log {log_score(anchored, outcomes):.5f}  "
                  f"delta {r4.mean_delta:+.5f}  p {r4.p_value:.4f}   {note4}")
            stopped_at = (
                ("rung 4", "anchored pool did not beat the market") if not beats4 else None
            )

    print(f"\n{'=' * 84}\nVERDICT\n{'=' * 84}")
    if stopped_at:
        rung, why = stopped_at
        print(f"  Ladder stopped at {rung}: {why}.")
        print("  -> No leakage-free forecaster adds information beyond the market price.")
        print("  -> Sophisticated weighting is NOT built (AXIOMS C9, E1).")
        print("  -> The market remains the benchmark. Gate 2a does not license Gate 2b.")
    else:
        print("  All rungs beaten on development. Confirming once on the SEALED holdout...")
        fitted = {f.name: f.fit(dev) for f in FORECASTERS}
        hp = logit_pool([
            [fitted["market"](o) for o in sealed],
            simple_pool([[fitted[m](o) for o in sealed] for m in models]),
        ])
        hr = [fitted["market"](o) for o in sealed]
        ho = [o.outcome for o in sealed]
        hc = [o.cluster_id for o in sealed]
        r, beats, note = verdict("sealed", hp, hr, ho, hc, log_score(hr, ho), seed=5)
        print(f"  {r.explain()}")
        print(f"  -> {'CONFIRMED' if beats else 'FAILED the sealed holdout'}")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
