"""Gate R: subsidy capture, net of measured adverse selection.

    python gater.py [--markets 120]

``docs/PROTOCOL.md`` Class R. Registered 2026-09-14, before this was written and before any reward
score was computed.

Classes A, B, C and M all tested hypotheses whose counterparty was an **informed trader**, and all
four lost to it — Class M by a measured 96.1% of the spread. Here the counterparty is the **venue**,
which pays by published rule rather than by opinion.

The tension the gate exists to resolve: the venue scores ``((v-s)/v)^2``, so rewards pay
quadratically more for a **tighter** quote — which is also the position of **maximum adverse
selection**. Quoting at the max-spread edge earns nothing at all. There is an optimum somewhere
between, and both terms are measurable: the pool and the formula are published, the competition is
read off the real book with the venue's own formula, and the cost of a fill was measured by Gate M.

Nothing here trades or quotes (F3).
"""

from __future__ import annotations

import argparse
import collections
import json
import time
from statistics import median

from kairos.book import fetch_book_result, queue_fills
from kairos.polymarket import _get_retry
from kairos.rewards import book_score, order_score, q_min, share_of_pool
from gatem import open_universe, quote

CLOB_MARKET = "https://clob.polymarket.com/markets/"

#: Measured by Gate M: median quoted half-spread 0.01000, R(60) +0.00039, so adverse selection is
#: 0.0096 per filled contract. Carried as a measured constant, never re-derived here.
ADVERSE = 0.0096

#: Measured fraction of the quoted half-spread a maker retains (Gate M: 0.00039 / 0.01000). Used by
#: gate3.py for the same purpose and for the same reason: it is the transferable quantity.
RETENTION = 0.00039 / 0.01000

#: C11 — the omission Pass 30.2 recorded is not repeated.
SIZES = (20.0, 100.0, 500.0, 2000.0)

#: Quote distance as a fraction of the market's own max spread.
FRACTIONS = tuple(i / 10.0 for i in range(0, 11))

FLOOR_ANNUAL = 104.70
DAYS = 365.0
MIN_MARKETS = 20


def reward_terms(condition_id: str):
    """``(daily_pool, max_spread_in_price_units, min_size)``, or a named refusal string.

    ``max_spread`` is published in **cents** and every price here is in dollars; the conversion is
    done once, at the boundary, so no downstream caller can be handed the raw field.

    Named refusals rather than a bare ``None``: a market with no pool, one whose terms cannot be
    fetched, and one advertising a pool with a **zero max spread** are three different findings, and
    the third is real — it exists in the live universe (AXIOMS G5).
    """
    try:
        d = _get_retry(CLOB_MARKET + str(condition_id), timeout=15)
    except Exception:
        return "terms_unfetchable"
    rw = (d or {}).get("rewards") or {}
    rates = rw.get("rates") or []
    pool = sum(float(r.get("rewards_daily_rate") or 0.0) for r in rates)
    if pool <= 0.0:
        return "no_reward_pool"
    try:
        max_spread, min_size = float(rw["max_spread"]) / 100.0, float(rw["min_size"])
    except (KeyError, TypeError, ValueError):
        return "terms_malformed"
    if max_spread <= 0.0:
        return "pool_with_zero_max_spread"   # nothing can qualify: the pool is unreachable
    return pool, max_spread, min_size


def queue_ahead(book, midpoint: float, distance: float) -> tuple[float, float]:
    """Resting size that outranks a quote posted ``distance`` from the midpoint, per side."""
    bid_px, ask_px = midpoint - distance, midpoint + distance
    ahead_bid = sum(lv.size for lv in book.bids if lv.price > bid_px)
    ahead_ask = sum(lv.size for lv in book.asks if lv.price < ask_px)
    return ahead_bid, ahead_ask


def net_per_day(book, *, midpoint, pool, max_spread, min_size, size, distance, side_flow,
                competitors) -> tuple[float, float, float, float]:
    """``(reward, fills, net_registered, net_consistent)`` per day for a two-sided quote."""
    if size < min_size:
        return 0.0, 0.0, 0.0, 0.0   # below the market's minimum qualifying size: scores nothing
    one = order_score(max_spread, distance, size)
    own = q_min(one, one, midpoint=midpoint)          # posted on both sides, so balanced
    reward = pool * share_of_pool(own, competitors)
    ahead_bid, ahead_ask = queue_ahead(book, midpoint, distance)
    fills = (min(queue_fills(side_flow, ahead_bid), size)
             + min(queue_fills(side_flow, ahead_ask), size))
    # REGISTERED rule, run as the verdict: fills are charged as pure cost at the measured constant.
    registered = reward - fills * ADVERSE
    # Gate-3.0-consistent reading, reported beside it. Gate M's R(60) is ALREADY net of adverse
    # selection, so the registered rule charges it twice against a capture of zero; the measured
    # per-fill P&L is RETENTION x distance, which is small and positive rather than a cost.
    consistent = reward + fills * RETENTION * distance
    return reward, fills, registered, consistent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--markets", type=int, default=120)
    ap.add_argument("--size", type=float, default=100.0)
    args = ap.parse_args()

    print("=" * 92)
    print("GATE R - SUBSIDY CAPTURE, NET OF MEASURED ADVERSE SELECTION")
    print("=" * 92)
    print("  The counterparty is the VENUE, not an informed trader. That is the new principal cause.")
    print(f"  adverse selection {ADVERSE} per filled contract (measured, Gate M)")
    print(f"  floor ${FLOOR_ANNUAL:.2f}/yr | score = ((v-s)/v)^2 * size, so the edge earns ZERO")
    print("  Expected to be marginally positive and to vanish as share normalises. NOTHING TRADED.")

    print(f"\n[1/3] Finding incentivized markets...", flush=True)
    census: collections.Counter[str] = collections.Counter()
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
        terms = reward_terms(m.get("conditionId"))
        if isinstance(terms, str):
            census[terms] += 1
            continue
        rows.append((m, terms, price, daily_vol))
        census["incentivized"] += 1
        if len(rows) >= args.markets:
            break
    for k, c in census.most_common(6):
        print(f"      {k:<32} {c}")

    print(f"\n[2/3] Scoring the real books against the venue's own formula...", flush=True)
    priced = []
    for m, (pool, max_spread, min_size), price, daily_vol in rows:
        try:
            token = json.loads(m["clobTokenIds"])[0]
        except (KeyError, ValueError, TypeError, IndexError):
            census["bad_token"] += 1
            continue
        book, why = fetch_book_result(str(token))
        if book is None or not book.bids or not book.asks:
            census[f"unusable_book:{why}"] += 1
            continue
        midpoint = (book.best_bid + book.best_ask) / 2.0
        competitors = book_score(book, midpoint=midpoint, max_spread=max_spread,
                                 min_size=min_size)
        side_flow = (daily_vol / price) / 2.0 if price > 0 else 0.0
        priced.append((book, midpoint, pool, max_spread, min_size, side_flow, competitors))
        time.sleep(0.03)
    print(f"      markets priced                   {len(priced)}")
    if priced:
        print(f"      median daily pool                ${median(p[2] for p in priced):,.0f}")
        print(f"      median competitor score          {median(p[6] for p in priced):,.0f}")

    if len(priced) < MIN_MARKETS:
        print(f"\n  WITHHELD - {len(priced)} markets against a floor of {MIN_MARKETS}. Apparatus.")
        return 0

    def total(size: float, frac: float) -> tuple[float, float, float, float]:
        r = f = nr = nc = 0.0
        for book, mid, pool, v, ms, flow, comp in priced:
            a, b, d, e = net_per_day(book, midpoint=mid, pool=pool, max_spread=v, min_size=ms,
                                     size=size, distance=frac * v, side_flow=flow,
                                     competitors=comp)
            r += a; f += b; nr += d; nc += e
        return r * DAYS, f * DAYS, nr * DAYS, nc * DAYS

    print(f"\n[3/3] Net annual by quote distance, at {args.size:.0f} contracts a side")
    print(f"  {'s / max_spread':>15} {'reward/yr':>12} {'fills/yr':>12} "
          f"{'NET registered':>16} {'NET consistent':>16}")
    for f in FRACTIONS:
        r, fl, nr, nc = total(args.size, f)
        print(f"  {f:>15.1f} {'$' + format(r, ',.0f'):>12} {fl:>12,.0f} "
              f"{'$' + format(nr, ',.0f'):>16} {'$' + format(nc, ',.0f'):>16}")

    print(f"\n  size curve at each size's own best distance (C11)")
    print(f"  {'size':>8} {'best s/v':>10} {'NET/yr':>14}")
    best_overall = (-1e18, None, None)
    for size in SIZES:
        best = max(((total(size, f)[2], f) for f in FRACTIONS), key=lambda x: x[0])
        print(f"  {size:>8,.0f} {best[1]:>10.1f} {'$' + format(best[0], ',.0f'):>14}")
        if best[0] > best_overall[0]:
            best_overall = (best[0], size, best[1])

    net, size, frac = best_overall
    print(f"\n{'=' * 92}\nVERDICT\n{'=' * 92}")
    print(f"  incentivized markets priced : {len(priced)}")
    print(f"  best net                    : ${net:,.0f}/yr at {size:,.0f} contracts, "
          f"s = {frac:.1f} x max_spread")
    print(f"  floor                       : ${FLOOR_ANNUAL:,.2f}/yr")

    if net <= 0.0:
        print("\n  GATE R: REFUTED - no quote distance pays.")
        print("  The subsidy does not exceed the adverse selection incurred to earn it, at any")
        print("  distance or size. Per the registered decision rule Class R closes, and with")
        print("  Classes A, B, C and M all closed, the registered programme ends.")
    elif net <= FLOOR_ANNUAL:
        print("\n  GATE R: REFUTED - below the floor.")
        print("  Positive, but not by the order of magnitude that distinguishes a business from")
        print("  an artefact. The programme ends on the registered rule.")
    else:
        print("\n  GATE R: NOT REFUTED.")
        print("  Subsidy capture clears the floor at the measured competition. This is a SNAPSHOT")
        print("  of today's competitors - share normalises against every entrant, so the next")
        print("  question is competitor response, and that is a NEW registration (F3 stands).")
    print("\n  Unmodelled: competitor response to entry, maker rebates, holding rewards, epoch")
    print("  mechanics, the $1 minimum payout. Adverse selection was measured at a ~1c half-spread")
    print("  and applying it at 4-6c flatters wide quotes.")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
