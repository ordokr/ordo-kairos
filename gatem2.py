"""Gate M2: the subsidised maker — spread, rebates and holding rewards together.

    python gatem2.py [--markets 200]

``docs/PROTOCOL.md`` Class M2. Registered 2026-09-14, before this was written and before any rebate
figure was computed.

Gate M measured that a maker retains **3.9%** of the quoted half-spread, and every gate since
excluded rebates and holding rewards as terms that "cut for" the hypothesis. Examining them changes
the arithmetic by an order of magnitude.

**The rebate is not a congestion game.** The pool is ``rebateRate x total taker fees`` and a maker's
share is ``own_fee_equivalent / total_fee_equivalent``, so the two scale together and the rebate per
filled contract is ``rebateRate x fee`` **whatever other makers do**. That is the structural
difference from the liquidity rewards Gate R measured, where share falls with every entrant.

**Holding rewards are modelled separately and honestly.** They pay for *holding inventory*, which a
market maker specifically avoids. They stack only if the inventory is a hedged YES+NO pair — which
costs ~$1, pays exactly $1 at resolution, and is therefore riskless carry at the venue's posted
rate. That rate is **3.25%**, below the 6% this repository charges for locked capital, so it cannot
stand alone.

Nothing here trades or quotes (F3).
"""

from __future__ import annotations

import argparse
import collections
import json
import time
from statistics import median

from kairos.book import fetch_book_result, queue_fills
from kairos.costs import CONSERVATIVE
from kairos.rewards import holding_reward, maker_rebate
from gatem import open_universe, quote
from gate3 import RETENTION, side_flow_contracts

#: Posted by the venue, variable at its discretion. A subsidy, not an edge.
HOLDING_RATE = 0.0325

SIZES = (25.0, 100.0, 500.0, 2000.0)
FLOOR_ANNUAL = 104.70
DAYS = 365.0
MIN_MARKETS = 50


def fee_terms(m: dict) -> tuple[float, float] | str:
    """``(fee_rate, rebate_rate)`` for a market, or a named refusal.

    A fee-free category pays **no** rebate — geopolitics is excluded by arithmetic, not by choice.
    """
    if not m.get("feesEnabled"):
        return "fees_disabled"
    fs = m.get("feeSchedule") or {}
    try:
        rate, rebate = float(fs["rate"]), float(fs["rebateRate"])
    except (KeyError, TypeError, ValueError):
        return "no_fee_schedule"
    if rate <= 0.0:
        return "fee_free_no_rebate"
    return rate, rebate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--markets", type=int, default=200)
    args = ap.parse_args()

    print("=" * 94)
    print("GATE M2 - THE SUBSIDISED MAKER (spread + rebates + holding rewards)")
    print("=" * 94)
    print(f"  spread retention {RETENTION:.1%} of the quoted half-spread (measured, Gate M)")
    print("  rebate = rebateRate x feeRate x p(1-p) per FILLED contract - NOT competition-normalised")
    print(f"  holding rewards {HOLDING_RATE:.2%}/yr on position value - a TREASURY SUBSIDY, variable")
    print(f"  floor ${FLOOR_ANNUAL:.2f}/yr | NOTHING IS TRADED OR QUOTED")

    print(f"\n[1/3] Sweeping for in-band, tick-room, fee-charging markets...", flush=True)
    census: collections.Counter[str] = collections.Counter()
    eligible: collections.Counter[str] = collections.Counter()
    rows = []
    for m in open_universe(args.pages):
        q = quote(m)
        if isinstance(q, str):
            census[q] += 1
            continue
        spread, tick, price, daily_vol = q
        if spread / tick <= 1.0 + 1e-9:
            census["no_tick_room"] += 1
            continue
        terms = fee_terms(m)
        if isinstance(terms, str):
            census[terms] += 1
            continue
        rows.append((m, spread, price, daily_vol, terms))
        census[f"eligible:{m.get('feeType')}"] += 1
        eligible[str(m.get("feeType"))] += 1
        if len(rows) >= args.markets:
            break
    for k, c in census.most_common(8):
        print(f"      {k:<34} {c}")

    print(f"\n[2/3] Pricing books and per-contract economics...", flush=True)
    priced = []
    for m, spread, price, daily_vol, (rate, rebate) in rows:
        try:
            token = json.loads(m["clobTokenIds"])[0]
        except (KeyError, ValueError, TypeError, IndexError):
            census["bad_token"] += 1
            continue
        book, why = fetch_book_result(str(token))
        if book is None or not book.bids or not book.asks:
            census[f"unusable_book:{why}"] += 1
            continue
        touch = (book.bids[0].size + book.asks[0].size) / 2.0
        flow = side_flow_contracts(daily_vol, price)
        spread_per_fill = RETENTION * (spread / 2.0)
        rebate_per_fill = maker_rebate(rate, rebate, price)
        priced.append((touch, flow, spread_per_fill, rebate_per_fill, rate, rebate,
                       str(m.get("feeType"))))
        time.sleep(0.03)

    print(f"      markets priced                   {len(priced)}")
    if len(priced) < MIN_MARKETS:
        print(f"\n  WITHHELD - {len(priced)} markets against a floor of {MIN_MARKETS}. Apparatus.")
        return 0

    msp = median(p[2] for p in priced)
    mrb = median(p[3] for p in priced)
    print(f"      median spread kept per fill      {msp:+.6f}")
    print(f"      median REBATE per fill           {mrb:+.6f}   ({mrb / msp:.1f}x the spread)")

    # Registered weighting: per-category, because feeRate and rebateRate both vary by category.
    # The registration's "81 of 100 are politics at 0.04" was an UNFILTERED sample; this is the
    # eligible mix after the band, tick-room and feesEnabled preconditions (CORRECTIONS.md 33.2).
    by_cat: dict[str, list[tuple[float, float, float, float]]] = {}
    for _, _, spf, rbf, rate, rebate, cat in priced:
        by_cat.setdefault(cat, []).append((spf, rbf, rate, rebate))
    print(f"\n      {'category':<26} {'n':>4} {'feeRate':>8} {'rebate':>7} "
          f"{'spread/fill':>12} {'rebate/fill':>12} {'ratio':>6}")
    for cat, vals in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        s, r = median(v[0] for v in vals), median(v[1] for v in vals)
        print(f"      {cat:<26} {len(vals):>4} {vals[0][2]:>8.2f} {vals[0][3]:>6.0%} "
              f"{s:>+12.6f} {r:>+12.6f} {r / s if s else float('nan'):>5.1f}x")

    print(f"\n[3/3] Annual, by posted size (C11). Capital is charged at the "
          f"{CONSERVATIVE.settlement_wedge_annual:.0%} hurdle.")
    print(f"  {'size':>7} {'capital':>11} {'spread/yr':>11} {'rebate/yr':>11} {'holding':>9} "
          f"{'cap cost':>10} {'NET/yr':>12} {'vs floor':>9}")
    best = (-1e18, None)
    for size in SIZES:
        sp = rb = 0.0
        for touch, flow, spf, rbf, _, _, _ in priced:
            fills = min(queue_fills(flow, touch), size)
            sp += fills * spf
            rb += fills * rbf
        sp *= DAYS
        rb *= DAYS
        # Two-sided quoting at `size` needs ~$1 per contract per market (a YES+NO pair costs $1).
        capital = size * len(priced)
        # Holding rewards accrue on a hedged pair, which is riskless - but 3.25% on capital that
        # costs 6% is a NET LOSS on that capital. Adding it as a positive without charging the
        # hurdle was a defect in the first run of this gate (CORRECTIONS.md Pass 33.3).
        hold = holding_reward(capital, HOLDING_RATE, DAYS)
        cap_cost = capital * CONSERVATIVE.settlement_wedge_annual
        net = sp + rb + hold - cap_cost
        if net > best[0]:
            best = (net, size)
        print(f"  {size:>7,.0f} {'$' + format(capital, ',.0f'):>11} "
              f"{'$' + format(sp, ',.0f'):>11} {'$' + format(rb, ',.0f'):>11} "
              f"{'$' + format(hold, ',.0f'):>9} {'-$' + format(cap_cost, ',.0f'):>10} "
              f"{'$' + format(net, ',.0f'):>12} "
              f"{'CLEARS' if net > FLOOR_ANNUAL else 'below':>9}")

    net_best, size = best
    print(f"\n{'=' * 94}\nVERDICT\n{'=' * 94}")
    print(f"  markets priced : {len(priced)}   best NET ${net_best:,.0f}/yr at {size:,.0f} contracts")
    print(f"  floor          : ${FLOOR_ANNUAL:,.2f}/yr")
    print(f"\n  per filled contract: spread {msp:+.6f}  +  rebate {mrb:+.6f}  "
          f"=  {msp + mrb:+.6f}  ({(msp + mrb) / msp:.1f}x spread alone)")
    print(f"  holding rewards alone: {HOLDING_RATE:.2%}/yr vs a "
          f"{CONSERVATIVE.settlement_wedge_annual:.0%} capital hurdle -> "
          f"{'CLEARS' if HOLDING_RATE > CONSERVATIVE.settlement_wedge_annual else 'FAILS'}")

    if net_best <= FLOOR_ANNUAL:
        print("\n  GATE M2: REFUTED - even with both subsidies the total is below the floor.")
    else:
        print("\n  GATE M2: NOT REFUTED - but SUBSIDY-DEPENDENT, and must be reported as such.")
        print("  The rebate and the holding rate are both set by the venue and both variable at its")
        print("  discretion. A subsidy the counterparty can switch off with one decision is not an")
        print("  edge; it is a promotion. Subsidy persistence is a NEW registration (F3 stands).")
    print("\n  Unmodelled: subsidy persistence (the dominant risk), queue position beyond Gate 3.0's")
    print("  model, competitive response, and inventory risk on any position not held as a hedged")
    print("  pair. Holding rewards require HOLDING, which a flat market maker by definition does not.")
    print("=" * 94)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
