"""Replication of the two look-#1 near-misses on **disjoint** events.

    python replicate.py              # Look 2: offset pagination
    python replicate.py --windowed   # Look 3: date windows, escaping the 2100-offset ceiling

Registered in ``docs/PROTOCOL.md`` ("Look 2" and "Look 3") **before the corresponding data was
fetched**. Nothing here may be changed to accommodate a result; if something must change, the run is
void and the registration is rewritten and re-run from scratch.

**Look 2 ran and returned WITHHELD** — it required 700 fresh events and the universe reachable by
offset pagination yielded 115. That is an apparatus ceiling, not a shortage of markets: Gamma
refuses ``offset`` past 2100 with HTTP 422 for every ordering, while the same query inside an
``end_date_min``/``end_date_max`` window gets its own budget, and a quarterly sweep reaches **26,143**
resolved markets. Look 3 is the same test on the universe that ceiling was hiding. It is *not*
"fetch more because the p-value disappointed": the registered sample size was never reachable by the
registered method, and Look 2's 115 events are **excluded** from Look 3 because their numbers have
now been read.

Why a replication rather than an alpha-spent second look: look #1 was conducted at the full nominal
``alpha = 0.05`` with no registered boundary, so no spending function can honestly be retrofitted —
choosing O'Brien-Fleming *now*, because it happens to spend almost nothing early and would leave
today's test nearly the whole budget, is picking the schedule after seeing the first look fail (A8).
Testing on events look #1 never saw sidesteps this entirely: these observations have never been
tested, so the full alpha is genuinely available.

**Exactly two hypotheses, named in the registration:**

===========  ====================================================  ==================
``C_logit``  logit-space logistic recalibration of the quote        look #1: +0.01341, p=0.1139
``drift``    the ``drift_per_day`` price-path forecaster           look #1: +0.01193, p=0.1174
===========  ====================================================  ==================

The rest of the Gate-1 family and the Gate-2a ladder are **not** re-tested. Running 5 + 4 models and
reporting the best is the search that made look #1's effect an upper bound in the first place; they
appear below only as descriptive context, explicitly labelled non-inferential.
"""

from __future__ import annotations

import argparse
import sys

# The literal implementations look #1 ran. Imported rather than reimplemented so that "the same
# hypothesis" is enforced by the module system instead of by a comment.
from gate1 import _fit_logit, _fit_raw
from kairos.forecasters import FORECASTERS, rolling_oos
from kairos.inference import superiority_test
from kairos.polymarket import (
    build_dataset,
    fetch_resolved_markets,
    fetch_window,
    quarterly_windows,
)
from kairos.score import log_score

# ---------------------------------------------------------------------------
# Frozen by the registration. Changing any of these voids the run.
# ---------------------------------------------------------------------------

#: Look #1 was `--pages 20 --limit 900`, giving 900 observations in 731 events.
LOOK1_PAGES = 20
LOOK1_LIMIT = 900
LOOK1_EVENTS = 731

#: Identical to look #1. 72 h yields more events but would make this a different experiment.
LEAD_HOURS = 24.0
MIN_POINTS = 5

#: Two pre-specified tests, so the one-sided 0.05 is split between them.
ALPHA = 0.025
MIN_RELATIVE_GAIN = 0.01

#: Below this the verdict is withheld as underpowered — never reported as "no effect" (A1).
REQUIRED_FRESH_EVENTS = 700

#: Look 3 only. Sweep windows until this many fresh events are admitted, then stop. A **sample-size**
#: target, fixed before the data existed, from Gates 1 and 2a independently sizing the re-test at
#: 1,400–1,900 events. Not a significance target: the sweep stops here whatever the p-values do.
LOOK3_TARGET_EVENTS = 1500

#: Look 2 swept `--pages 60`, which the API silently truncates to 21 pages / 2,100 markets.
LOOK2_PAGES = 60

HOLDOUT_FRAC = 0.25
FOLDS = 6


def cluster_order(obs):
    first = {}
    for o in obs:
        first[o.cluster_id] = min(first.get(o.cluster_id, o.resolution_ts), o.resolution_ts)
    return sorted(first, key=lambda c: first[c])


def look1_event_ids() -> set[str]:
    """Reconstruct look #1's exact event set, and refuse to continue if it does not reproduce.

    Every disjointness claim in this run rests on this set being right. It is rebuilt from the same
    cached pages with the same arguments and checked against the event count recorded in
    ``docs/GATE1-RESULTS.md``. A silent mismatch here would let look-#1 events back into the test
    set and quietly turn the replication into a re-test of data that has already been looked at.
    """
    markets = fetch_resolved_markets(LOOK1_PAGES)
    obs, _ = build_dataset(
        markets, min_points=MIN_POINTS, lead_hours=LEAD_HOURS, limit=LOOK1_LIMIT
    )
    ids = {o.cluster_id for o in obs}
    if len(ids) != LOOK1_EVENTS:
        raise SystemExit(
            f"look #1 did not reproduce: rebuilt {len(ids)} events, recorded {LOOK1_EVENTS}. "
            f"The disjointness guarantee cannot be established, so this run is void. "
            f"Do not 'fix' this by relaxing the check."
        )
    return ids


def look2_event_ids(look1: set[str]) -> set[str]:
    """The 115 events Look 2 tested. Spent, because their numbers have been read.

    Reusing them in Look 3 would make Look 3 a second look on part of its own sample — the exact
    failure the disjointness design exists to prevent, reintroduced one level up.
    """
    obs, _ = build_dataset(
        fetch_resolved_markets(LOOK2_PAGES), min_points=MIN_POINTS,
        lead_hours=LEAD_HOURS, limit=None,
    )
    return {o.cluster_id for o in obs} - look1


def collect_fresh(seen: set[str], target: int, progress):
    """Sweep quarterly windows newest-first until ``target`` fresh events are admitted.

    Stops on a **count of events**, never on a p-value, and the count was frozen in the
    registration before this data existed. Windows are taken in date order rather than by yield, so
    which windows enter the sample cannot depend on anything measured in them.
    """
    fresh: list = []
    have: set[str] = set()
    gaps: list[tuple[str, str, list[int]]] = []
    for lo, hi in quarterly_windows():
        markets, failed = fetch_window(lo, hi)
        if failed:
            # Recorded, never silent. Two quarters are permanently HTTP 500 upstream; a hole in the
            # sample's calendar coverage has to reach the results doc as a stated limitation, not
            # disappear into an empty list (AXIOMS A6).
            gaps.append((lo, hi, failed))
        if not markets:
            progress(f"{lo}..{hi}: NO MARKETS"
                     + (f" - UNREACHABLE, offsets {failed}" if failed else ""))
            continue
        obs, _ = build_dataset(
            markets, min_points=MIN_POINTS, lead_hours=LEAD_HOURS, limit=None
        )
        added = 0
        for o in obs:
            if o.cluster_id not in seen:
                fresh.append(o)
                if o.cluster_id not in have:
                    have.add(o.cluster_id)
                    added += 1
        note = f"  [PARTIAL: offsets {failed} unreachable]" if failed else ""
        progress(f"{lo}..{hi}: {len(markets):>5} markets -> +{added:>4} fresh events "
                 f"(total {len(have)}/{target}){note}")
        if len(have) >= target:
            progress("target reached, stopping the sweep as registered")
            break
    return fresh, gaps


def report(name, preds, raw, outcomes, clusters, bench, seed):
    r = superiority_test(preds, raw, outcomes, clusters, alpha=ALPHA, n_boot=2000, seed=seed)
    material = r.mean_delta >= MIN_RELATIVE_GAIN * bench
    passes = r.significant and material
    if r.significant and not material:
        note = f"significant but immaterial ({r.mean_delta / bench:.2%})"
    else:
        note = "REPLICATES" if passes else "does not replicate"
    return r, passes, note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=60)
    ap.add_argument("--windowed", action="store_true",
                    help="Look 3: sweep date windows, escaping the 2100-offset ceiling")
    args = ap.parse_args()

    look = 3 if args.windowed else 2
    print("=" * 84)
    print(f"LOOK {look} - REPLICATION ON DISJOINT EVENTS"
          + (" (WINDOWED RETRIEVAL)" if args.windowed else ""))
    print("=" * 84)
    print(f"  registered in docs/PROTOCOL.md before this data existed")
    print(f"  lead {LEAD_HOURS:.0f}h (same as look #1) | alpha {ALPHA} x2 (Bonferroni) | "
          f"materiality {MIN_RELATIVE_GAIN:.0%}")

    print("\n[1/4] Reconstructing look #1's event set...", flush=True)
    seen = look1_event_ids()
    print(f"      {len(seen)} events reproduced exactly - disjointness can be enforced")

    if args.windowed:
        print("\n[2/4] Reconstructing look #2's spent events...", flush=True)
        spent = look2_event_ids(seen)
        seen = seen | spent
        print(f"      {len(spent)} events already tested and read - excluded")
        print(f"      {len(seen)} events excluded in total")
        print(f"\n[3/4] Sweeping quarterly windows newest-first "
              f"(target {LOOK3_TARGET_EVENTS} fresh events)...", flush=True)
        fresh, gaps = collect_fresh(seen, LOOK3_TARGET_EVENTS,
                                    lambda s: print(f"      {s}", flush=True))
        required = LOOK3_TARGET_EVENTS
        if gaps:
            print("\n      COVERAGE GAPS - these quarters could not be fully retrieved:")
            for lo, hi, off in gaps:
                print(f"        {lo}..{hi}  unreachable offsets {off}")
            print("      Recorded as a limitation. The sample has a hole in calendar time.")
    else:
        print(f"\n[2/4] Fetching {args.pages} pages (look #1 used {LOOK1_PAGES})...", flush=True)
        markets = fetch_resolved_markets(args.pages)
        print(f"      {len(markets)} markets available")

        print("\n[3/4] Building the uncapped dataset...", flush=True)
        obs, reasons = build_dataset(
            markets, min_points=MIN_POINTS, lead_hours=LEAD_HOURS, limit=None,
            progress=lambda s: print(f"      {s}", flush=True),
        )
        print("\n      admission census:")
        for k, v in reasons.items():
            print(f"        {k:28s} {v}")
        fresh = [o for o in obs if o.cluster_id not in seen]
        gaps = []
        required = REQUIRED_FRESH_EVENTS

    fresh_clusters = cluster_order(fresh)
    print(f"\n      FRESH observations      {len(fresh)}  in {len(fresh_clusters)} events")
    print(f"      registered requirement  {required} fresh events")

    if not fresh_clusters:
        print("\n  No fresh events. Nothing to replicate on.")
        return 1

    underpowered = len(fresh_clusters) < required
    if underpowered:
        print(f"\n      -> SHORTFALL. Proceeding as registered, verdict will be WITHHELD.")
        print("         (The registration forbids fetching more because the result disappoints.)")

    cut = int(len(fresh_clusters) * (1 - HOLDOUT_FRAC))
    dev_c, sealed_c = fresh_clusters[:cut], fresh_clusters[cut:]
    dev = [o for o in fresh if o.cluster_id in set(dev_c)]
    sealed = [o for o in fresh if o.cluster_id in set(sealed_c)]
    print(f"\n      development {len(dev_c)} events / SEALED {len(sealed_c)} events (queried once)")

    print(f"\n[4/4] Rolling expanding-window folds on the fresh development set...", flush=True)
    market_spec = next(f for f in FORECASTERS if f.name == "market")
    drift_spec = next(f for f in FORECASTERS if f.name == "drift")
    fitters = {
        "market": market_spec.fit,
        "C_logit": _fit_logit,
        "drift": drift_spec.fit,
    }
    preds = rolling_oos(dev, dev_c, FOLDS, fitters)
    outcomes, cl = preds["_outcome"], preds["_cluster"]
    if not outcomes:
        print("      No out-of-sample predictions. Inconclusive.")
        return 1
    raw = preds["market"]
    bench = log_score(raw, outcomes)
    print(f"      out-of-sample: {len(outcomes)} rows in {len(set(cl))} events")

    print(f"\n{'=' * 84}\nTHE TWO PRE-SPECIFIED TESTS\n{'=' * 84}")
    print(f"  {'hypothesis':<10} {'log score':>10} {'vs market':>11} {'p':>8} "
          f"{'look #1':>10}   verdict")
    print(f"  {'-'*10} {'-'*10} {'-'*11} {'-'*8} {'-'*10}   {'-'*22}")
    print(f"  {'market':<10} {bench:>10.5f} {'-':>11} {'-':>8} {'-':>10}   benchmark")

    look1 = {"C_logit": +0.01341, "drift": +0.01193}
    outcome_dev = {}
    for i, name in enumerate(("C_logit", "drift")):
        r, passes, note = report(name, preds[name], raw, outcomes, cl, bench, seed=11 + i)
        outcome_dev[name] = (r, passes)
        print(f"  {name:<10} {log_score(preds[name], outcomes):>10.5f} {r.mean_delta:>+11.5f} "
              f"{r.p_value:>8.4f} {look1[name]:>+10.5f}   {note}")

    replicated = [n for n, (_, ok) in outcome_dev.items() if ok]

    print(f"\n{'=' * 84}\nSEALED HOLDOUT - QUERIED ONCE\n{'=' * 84}")
    confirmed: list[str] = []
    if not replicated:
        print("  Neither hypothesis cleared development. The sealed holdout is NOT queried:")
        print("  spending it on a hypothesis that already failed would burn the one query for")
        print("  nothing (AXIOMS C6). It remains sealed for a future, differently-designed run.")
    else:
        fitted = {name: fitters[name](dev) for name in ["market", *replicated]}
        hr = [fitted["market"](o) for o in sealed]
        ho = [o.outcome for o in sealed]
        hc = [o.cluster_id for o in sealed]
        hbench = log_score(hr, ho)
        for i, name in enumerate(replicated):
            hp = [fitted[name](o) for o in sealed]
            r, passes, note = report(name, hp, hr, ho, hc, hbench, seed=31 + i)
            print(f"  {name}: {r.explain()}")
            print(f"    -> {note}")
            if passes:
                confirmed.append(name)

    print(f"\n{'=' * 84}\nVERDICT\n{'=' * 84}")
    if underpowered:
        print(f"  WITHHELD. {len(fresh_clusters)} fresh events is below the registered "
              f"{required}.")
        print("  Under AXIOMS A1 this is 'not enough evidence', NOT 'no effect'. The registered")
        print("  next move is a different venue or a forward paper test - not another re-test of")
        print("  this same universe with more pages.")
        for name, (r, _) in outcome_dev.items():
            print(f"    {name}: {r.mean_delta:+.5f} (look #1 {look1[name]:+.5f}), p={r.p_value:.4f}")
    elif confirmed:
        print(f"  REPLICATED and CONFIRMED: {', '.join(confirmed)}")
        print("  -> proceeds to Gate 3 (execution realism). The other hypothesis does not,")
        print("     whatever it scored.")
    else:
        print("  NEITHER hypothesis replicated on disjoint events.")
        print("  -> Class A forecasting edge is REJECTED at this venue and scale.")
        print("     No further model work is done on Polymarket resolved markets.")
        print("     The registration said 'baseline.py is deleted'. AMENDED 2026-09-08: that clause")
        print("     used a FILE as a proxy for a HYPOTHESIS. The same module holds SettlementTerms,")
        print("     which census.py uses as the Class B carry model, and Class B is untested rather")
        print("     than refuted. The rejected classes are un-exported from `kairos` and fenced by")
        print("     tests/test_baseline.py instead; the code stays runnable so Gates 1-2a and")
        print("     Looks 1-3 remain reproducible. See docs/PROTOCOL.md 'Amendment'.")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
