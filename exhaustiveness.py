"""Measure the negRisk exhaustiveness failure rate — the number Class B's universe turns on.

    python exhaustiveness.py [--limit N]

``kairos.legset`` refuses an arbitrage whose edge cannot absorb the residual risk that a group is
**not** exhaustive: if no listed outcome occurs, every leg resolves NO, the set pays $0 instead of
$1, and the whole stake is lost. Break-even is ``edge / (edge + stake)``, so with a 4% residual
bound a sub-5% arbitrage is not worth taking.

That bound is ``3 / trials`` while no failure has been seen, so **the tradeable universe widens by
measuring more groups and by nothing else**. This script is that measurement, made reproducible
rather than left as the ad-hoc probe the first 75 came from: the constants in
``kairos.legset`` are outputs of this run and should be regenerated, never edited by hand.

**What counts as a failure, and why both directions matter:**

- **zero winners** — no listed outcome occurred. The buy-every-leg identity pays $0. This is the
  catastrophic case and the one the residual bound is about.
- **more than one winner** — the outcomes were not mutually exclusive. This one pays *more* than $1,
  so it is not a loss for an arbitrage buyer, but it falsifies the same structural claim and is
  counted and reported separately rather than quietly treated as a pass.

**Survivorship check.** A group where nothing won might be voided rather than resolved, and voided
markets report ``["0","0"]`` — which a clean-resolution filter silently drops, making the sample
structurally unable to contain the failures it is looking for. Measured across 4,968 closed negRisk
markets: **zero voided, zero unparseable, zero settled between the extremes.** The channel does not
exist here, and the run re-checks it rather than trusting this note.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import time

from kairos.legset import fetch_event
from kairos.polymarket import RESOLUTION_TOL, cache_dir


def closed_neg_risk_events() -> list[str]:
    """Every distinct event id carrying a closed negRisk market, from cached pages only."""
    cd = pathlib.Path(cache_dir())
    events: set[str] = set()
    for sub in ("markets", "windows"):
        d = cd / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                batch = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(batch, list):
                continue
            for m in batch:
                if m.get("negRiskMarketID") and m.get("closed"):
                    for e in m.get("events") or []:
                        if e.get("id"):
                            events.add(str(e["id"]))
    return sorted(events)


def classify(market: dict) -> str:
    """``yes`` / ``no`` / ``voided`` / ``unclean``. Never guesses; ``unclean`` is a real answer."""
    try:
        prices = [float(x) for x in json.loads(market["outcomePrices"])]
    except (KeyError, ValueError, TypeError):
        return "unclean"
    if len(prices) != 2:
        return "unclean"
    if abs(sum(prices)) < 1e-9:
        return "voided"
    if abs(sum(prices) - 1.0) > RESOLUTION_TOL:
        return "unclean"
    if prices[0] > 1.0 - RESOLUTION_TOL:
        return "yes"
    if prices[0] < RESOLUTION_TOL:
        return "no"
    return "unclean"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = every available event")
    ap.add_argument("--pause", type=float, default=0.05)
    args = ap.parse_args()

    print("=" * 84)
    print("NEGRISK EXHAUSTIVENESS - HOW OFTEN DOES NO LISTED OUTCOME WIN?")
    print("=" * 84)
    events = closed_neg_risk_events()
    if args.limit:
        events = events[: args.limit]
    print(f"  closed negRisk events available: {len(events)}")

    stats: collections.Counter[str] = collections.Counter()
    winners_hist: collections.Counter[int] = collections.Counter()
    zero_winner_events: list[tuple[str, int, bool]] = []
    multi_winner_events: list[tuple[str, int, int]] = []
    trials = 0
    t0 = time.time()

    for i, eid in enumerate(events):
        if i and i % 100 == 0:
            print(f"    {i}/{len(events)} scanned, {trials} usable", flush=True)
        ev = fetch_event(eid)
        if ev is None:
            stats["event_unavailable"] += 1
            continue
        markets = ev.get("markets") or []
        if not markets:
            stats["event_lists_no_markets"] += 1
            continue
        if not all(m.get("closed") for m in markets):
            stats["group_not_fully_closed"] += 1
            continue
        kinds = [classify(m) for m in markets]
        if any(k in ("unclean", "voided") for k in kinds):
            # Reported, never silently dropped: this is the survivorship channel (AXIOMS G5).
            stats["voided_or_unclean_leg"] += 1
            continue
        trials += 1
        wins = sum(1 for k in kinds if k == "yes")
        winners_hist[wins] += 1
        has_other = any(bool(m.get("negRiskOther")) for m in markets)
        if wins == 0:
            zero_winner_events.append((eid, len(markets), has_other))
        elif wins > 1:
            multi_winner_events.append((eid, len(markets), wins))
        time.sleep(args.pause)

    print(f"\n  usable fully-resolved groups: {trials}")
    for k, v in stats.most_common():
        print(f"    excluded: {k:28s} {v}")

    print(f"\n{'=' * 84}\nWINNERS PER GROUP\n{'=' * 84}")
    for w in sorted(winners_hist):
        flag = ""
        if w == 0:
            flag = "  <- NON-EXHAUSTIVE: the set pays $0"
        elif w > 1:
            flag = "  <- NOT MUTUALLY EXCLUSIVE"
        print(f"  {w} winner(s): {winners_hist[w]:5d}{flag}")

    failures = len(zero_winner_events)
    if zero_winner_events:
        print("\n  zero-winner groups (event, legs, had Other leg):")
        for eid, n, other in zero_winner_events[:20]:
            print(f"    {eid:>10}  {n:3d} legs  other={other}")
    if multi_winner_events:
        print("\n  multi-winner groups (event, legs, winners):")
        for eid, n, w in multi_winner_events[:20]:
            print(f"    {eid:>10}  {n:3d} legs  {w} winners")

    print(f"\n{'=' * 84}\nRESULT\n{'=' * 84}")
    from kairos.legset import break_even_failure_rate, residual_failure_bound

    bound = residual_failure_bound(trials, failures)
    print(f"  trials {trials}, zero-winner failures {failures}")
    print(f"  residual non-exhaustiveness bound: {bound:.4f}")
    print(f"\n  {'edge':>6}  {'break-even':>11}  verdict")
    for edge in (0.01, 0.02, 0.03, 0.05, 0.10):
        be = break_even_failure_rate(edge, 1.0 - edge)
        print(f"  {edge:6.0%}  {be:11.4f}  {'TRADEABLE' if bound < be else 'refused'}")
    print("\n  Paste into kairos/legset.py (do not hand-edit):")
    print(f"    EXHAUSTIVENESS_TRIALS = {trials}")
    print(f"    EXHAUSTIVENESS_FAILURES = {failures}")
    print(f"\n  elapsed {time.time() - t0:.1f}s")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
