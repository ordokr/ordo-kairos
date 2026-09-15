"""Gate K.0: is a maker better paid on Kalshi? The cheap structural precondition.

    python gatek.py [--pages 12]

``docs/PROTOCOL.md`` Class K. Registered 2026-09-14, before this was written and before any Kalshi
spread figure was computed.

Classes M, M.0, M2, R and S are Polymarket-only. Gate M measured **3.9%** spread retention there.
This asks the cheapest version of the same question of a second venue: **is there room to quote
inside the spread at all**, weighted by the flow that would have to fill you.

The weighting is the whole point. Gate M.0's registered condition passed on a median of *markets*
while **77.4% of the flow** sat in one-tick markets where an entrant can only join the back of a
queue (``CORRECTIONS.md`` Pass 28.1). That correction is applied here in advance.

**No fee or rebate is measured.** Kalshi's market API exposes no fee, maker, taker, rebate or reward
field at all, and ``kairos/kalshi.py`` already records the published schedule as unverified. This
gate is about the spread and nothing else.

Nothing here trades or quotes (F3).
"""

from __future__ import annotations

import argparse
import collections
from statistics import median

from kairos.costs import CONSERVATIVE
from kairos.inference import weighted_share_ci
from kairos import kalshi as K

#: Polymarket's measured share of flow with room to quote inside (Gate M.0 as corrected by
#: CORRECTIONS.md Pass 28.1: 77.4% of flow sits at one tick, so 22.6% does not).
POLYMARKET_FLOW_WITH_ROOM = 0.226

MIN_MARKETS = 300


def tick_size(m: dict, mid: float) -> float | None:
    """Tick at this price, from ``price_ranges``. Tapered structures vary the step by range."""
    ranges = m.get("price_ranges") or []
    for r in ranges:
        try:
            lo, hi, step = float(r["start"]), float(r["end"]), float(r["step"])
        except (KeyError, TypeError, ValueError):
            continue
        if lo <= mid <= hi and step > 0.0:
            return step
    # Single unconditional range is common; fall back to it rather than guessing a cent.
    for r in ranges:
        try:
            step = float(r["step"])
        except (KeyError, TypeError, ValueError):
            continue
        if step > 0.0:
            return step
    return None


def quote(m: dict) -> tuple[float, float, float, float] | str:
    """``(spread, tick, mid, flow_dollars)`` or a named refusal."""
    if m.get("status") != "active":
        return "not_active"
    try:
        bid = float(m["yes_bid_dollars"])
        ask = float(m["yes_ask_dollars"])
        vol = float(m.get("volume_24h_fp") or 0.0)
    except (KeyError, TypeError, ValueError):
        return "missing_quote_fields"
    if bid <= 0.0 or ask <= 0.0 or ask <= bid:
        return "no_two_sided_quote"
    mid = (bid + ask) / 2.0
    if not (CONSERVATIVE.min_price <= mid <= CONSERVATIVE.max_price):
        return "longshot_out_of_band"
    if vol <= 0.0:
        return "no_flow"
    tick = tick_size(m, mid)
    if tick is None:
        return "no_tick_structure"
    # Flow in dollars: contracts traded x the price they traded around.
    return ask - bid, tick, mid, vol * mid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=12)
    args = ap.parse_args()

    print("=" * 94)
    print("GATE K.0 - IS THERE ROOM TO QUOTE ON KALSHI? (the cheap structural precondition)")
    print("=" * 94)
    print("  Units: TICKS and PERCENT OF 24H DOLLAR FLOW. Never cents - three tick structures.")
    print("  Weighting: by FLOW, not by market count (Pass 28.1, applied in advance).")
    print(f"  Comparator: Polymarket's measured {POLYMARKET_FLOW_WITH_ROOM:.1%} of flow with room.")
    print("  NO fee or rebate is measured - Kalshi exposes none. NOTHING IS TRADED OR QUOTED.")

    print(f"\n[1/3] Fetching Kalshi events...", flush=True)
    events = K.fetch_events(pages=args.pages)
    markets = [m for e in events for m in (e.get("markets") or [])]
    print(f"      events {len(events)}   markets {len(markets)}")

    print(f"\n[2/3] Applying preconditions...", flush=True)
    census: collections.Counter[str] = collections.Counter()
    rows = []
    for m in markets:
        q = quote(m)
        if isinstance(q, str):
            census[q] += 1
            continue
        rows.append(q)
        census["eligible"] += 1
    for k, c in census.most_common(8):
        print(f"      {k:<28} {c}")

    if len(rows) < MIN_MARKETS:
        print(f"\n  WITHHELD - {len(rows)} markets against a floor of {MIN_MARKETS}. Apparatus.")
        return 0

    print(f"\n[3/3] Spread in ticks, weighted by flow")
    total_flow = sum(f for _, _, _, f in rows)
    ticks = [s / t for s, t, _, _ in rows]
    flow_with_room = sum(f for s, t, _, f in rows if s / t > 1.0 + 1e-9)
    share = flow_with_room / total_flow

    by_struct: dict[float, list[tuple[float, float]]] = {}
    for s, t, _, f in rows:
        by_struct.setdefault(t, []).append((s / t, f))
    print(f"      {'tick':>8} {'markets':>9} {'flow $':>14} {'med ticks':>10} {'flow w/ room':>13}")
    for t in sorted(by_struct):
        vals = by_struct[t]
        tf = sum(f for _, f in vals)
        room = sum(f for tk, f in vals if tk > 1.0 + 1e-9)
        print(f"      {t:>8.4f} {len(vals):>9} {'$' + format(tf, ',.0f'):>14} "
              f"{median(tk for tk, _ in vals):>10.2f} {room / tf if tf else 0:>12.1%}")

    # Flow-weighted median: the tick spread at which half the dollar flow sits below.
    ordered = sorted(((s / t, f) for s, t, _, f in rows), key=lambda x: x[0])
    cum, fw_median = 0.0, ordered[-1][0]
    for tk, f in ordered:
        cum += f
        if cum >= total_flow / 2.0:
            fw_median = tk
            break

    print(f"\n      markets eligible            {len(rows)}")
    print(f"      total 24h flow              ${total_flow:,.0f}")
    print(f"      median spread (by market)   {median(ticks):.2f} ticks")
    print(f"      median spread (by FLOW)     {fw_median:.2f} ticks")
    print(f"      flow WITH room to quote     {share:.1%}")
    print(f"      flow pinned at one tick     {1 - share:.1%}")

    # Two bare point estimates are not a comparison. Gate M's null gate failed exactly that way
    # (CORRECTIONS.md Pass 29): medians right, single replications wrong 20-47% of the time.
    ci = weighted_share_ci([s / t > 1.0 + 1e-9 for s, t, _, _ in rows],
                           [f for _, _, _, f in rows], seed=20260914)

    print(f"\n{'=' * 94}\nVERDICT\n{'=' * 94}")
    print(f"  Kalshi     flow with room : {share:.1%}"
          + (f"   95% CI [{ci[0]:.1%}, {ci[1]:.1%}]" if ci else "   (no interval: too few units)"))
    print(f"  Polymarket flow with room : {POLYMARKET_FLOW_WITH_ROOM:.1%}  (Gate M.0, corrected)")

    if ci is not None and ci[0] <= POLYMARKET_FLOW_WITH_ROOM <= ci[1]:
        print("\n  GATE K.0: NO VERDICT. The interval straddles Polymarket's measured share, so the")
        print(f"  {share:.1%} point estimate does not distinguish the two venues. A difference of")
        print(f"  {(share - POLYMARKET_FLOW_WITH_ROOM) * 100:+.1f} points on one snapshot, with an")
        print(f"  interval {(ci[1] - ci[0]) * 100:.1f} points wide, is not a finding.")
        print("  Class K neither closes nor licenses Gate K. Three-state discipline (validity.py).")
    elif share <= POLYMARKET_FLOW_WITH_ROOM:
        print("\n  GATE K.0: REFUTED. Kalshi offers a maker no more room than the venue already")
        print("  measured, and Class K closes. No adverse-selection measurement is licensed -")
        print("  there is nothing to select against that has not already been measured worse.")
    else:
        print("\n  GATE K.0: NOT REFUTED on the cheap gate ONLY. This licenses Gate K, the")
        print("  realized-half-spread measurement, as a NEW registration. It licenses no claim")
        print("  whatever about maker profitability on Kalshi: tick room is a precondition for")
        print("  an edge, never evidence of one. Gate M found 96.1% of the spread going to")
        print("  adverse selection on a venue that HAD room.")
    print("\n  Unmodelled: fees and rebates (Kalshi publishes none in the API and the schedule")
    print("  remains unverified), adverse selection, queue position, inventory. F3 stands.")
    print("=" * 94)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
