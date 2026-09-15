"""Gate 4.0: the capacity ceiling, measured before another edge is searched for.

    python gate4.py [--size 25] [--pairs N]

``docs/PROTOCOL.md`` Gate 4.0. Registered 2026-09-14, before this was built and before any capacity
number existed.

**Why this runs out of order.** Gate 4 sits behind Gate 3, which is behind having a candidate, so
the one measurement that can kill the programme for free is scheduled after every expensive thing in
it. That is a policy constraint rather than an evidential one: capacity is a property of the
**venue** -- depth, horizon, and the size of the opportunity set -- not of the strategy that would
exploit it, so it needs no surviving candidate to be measurable.

**Every assumption here is optimistic on purpose.** Perfect fills (``hit_rate = 1.0``), zero
infrastructure and research cost, full convergence on every trade, and instant redeployment of
capital at the horizon limit. The ceiling is built to be unreachably generous so that a failure
cannot be blamed on a harsh test -- the same construction as Gate D.0 comparing the largest gap to
the median cost.

**Recurrence is inverted, not invented.** Three of the four inputs to
``edge x fillable x opportunities x hit_rate - fixed`` are measurable now; how often an opportunity
reappears is not, because no price history has been fetched. So this reports the recurrence the
hurdle would require, alongside a horizon-limited ceiling on what recurrence can physically be, and
never fabricates a frequency (AXIOMS A6, G3; PROTOCOL Gate 4's ban on naive annualisation).

Nothing here trades, sizes a position, or touches capital (F3).
"""

from __future__ import annotations

import argparse
import collections
import time

from kairos.book import fetch_book_result
from kairos.costs import CONSERVATIVE
from kairos.economics import StrategyEconomics, rank_strategies
from kairos.kalshi import fetch_books
from gated import DAYS_HELD, aligned_pairs, best_round_trip, poly_handles

#: The objective floor, registered: the repo's own opportunity cost of locked collateral. A strategy
#: that cannot beat the carry rate the cost model already charges it is strictly worse than not
#: trading. Deliberately an existing constant rather than one invented after four failed hypotheses.
HURDLE_RATE = CONSERVATIVE.settlement_wedge_annual

DAYS_PER_YEAR = 365.0


def class_c_opportunities(size: float, cap: int = 0):
    """Price the adjudicated alignment table and return the opportunities that clear their own cost.

    ``net_edge = gross_gap - round_trip`` is the profit per contract on **full** convergence -- the
    gap closing to zero, which is the most a convergence trade can ever collect. An upper bound by
    construction, and the registration says so.
    """
    census: collections.Counter[str] = collections.Counter()
    clearing: list[tuple[str, float, float, float]] = []   # title, net_edge, capital, gross_gap
    priced = 0
    pairs = aligned_pairs()
    if cap:
        pairs = pairs[:cap]

    for t in pairs:
        handles = poly_handles(str(t["pm_id"]))
        if isinstance(handles, str):
            census[f"polymarket:{handles}"] += 1
            time.sleep(0.05)
            continue
        p_yes, why_y = fetch_book_result(handles[0])
        p_no, why_n = fetch_book_result(handles[1])
        k_yes, k_no, why_k = fetch_books(str(t["kx_ticker"]))
        if p_yes is None or p_no is None:
            census[f"unfetchable_polymarket:{why_y if p_yes is None else why_n}"] += 1
            time.sleep(0.05)
            continue
        if k_yes is None or k_no is None:
            census[f"unfetchable_kalshi:{why_k}"] += 1
            time.sleep(0.05)
            continue
        best, reason = best_round_trip(p_yes, p_no, k_yes, k_no, size=size, costs=CONSERVATIVE)
        if best is None:
            census[reason.split(":")[-1] or "unpriceable"] += 1
            time.sleep(0.05)
            continue
        _, rt = best
        priced += 1
        in_band = (CONSERVATIVE.price_in_band(rt.yes_vwap)
                   and CONSERVATIVE.price_in_band(rt.no_vwap))
        net_edge = rt.gross_gap - rt.cost
        if net_edge <= 0.0:
            census["priced_but_does_not_clear_its_own_cost"] += 1
        elif not in_band:
            # Counted separately rather than merged: "no opportunity" and "an opportunity the
            # protocol excludes" are different findings (AXIOMS G5).
            census["clears_but_excluded_as_longshot"] += 1
        else:
            clearing.append((str(t["pm_title"]).encode("ascii", "replace").decode()[:52],
                             net_edge, rt.entry_cost * size, rt.gross_gap))
        time.sleep(0.05)
    return priced, clearing, census


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=float, default=25.0)
    ap.add_argument("--pairs", type=int, default=0, help="cap pairs (0 = the whole table)")
    args = ap.parse_args()

    print("=" * 88)
    print("GATE 4.0 - CAPACITY CEILING (is there a business, not is there an edge)")
    print("=" * 88)
    print("  Registered before the number existed. The recorded expectation is that the ceiling")
    print("  lands orders of magnitude below any defensible hurdle - and that expectation carries")
    print("  no weight against the measurement (CORRECTIONS.md Pass 26.3).")
    print(f"  hurdle {HURDLE_RATE:.1%}/yr on capital locked | size {args.size:.0f} | "
          f"hit_rate 1.0 and fixed cost $0, both optimistic")
    print("  NOTHING IS TRADED.")

    print(f"\n[1/2] Pricing the reachable Class C opportunity set at {args.size:.0f} "
          f"contracts...", flush=True)
    priced, clearing, census = class_c_opportunities(args.size, args.pairs)
    for key, count in census.most_common():
        print(f"      {key:<48} {count}")
    print(f"      {'priced':<48} {priced}")
    print(f"      {'CLEAR their own round trip, in band':<48} {len(clearing)}")

    if clearing:
        print(f"\n  {'opportunity':<54} {'net edge':>10} {'capital':>10}")
        for title, edge, capital, _ in sorted(clearing, key=lambda r: -r[1]):
            print(f"  {title:<54} {edge:>+10.5f} {capital:>10.2f}")

    # --- the ceiling -------------------------------------------------------------------------
    # One "opportunity" is one pair-trade held for the registered horizon. With a 7-day hold the
    # same capital can physically cycle 365/7 times a year, so that -- times the number of distinct
    # clearing pairs -- is a hard upper bound on recurrence, assuming each regenerates the instant
    # it is exited. Nothing observed supports that; it is the generous end of the range.
    cycles = DAYS_PER_YEAR / DAYS_HELD
    deployable = sum(c for _, _, c, _ in clearing)
    mean_edge = (sum(e for _, e, _, _ in clearing) / len(clearing)) if clearing else 0.0
    mean_capital = (deployable / len(clearing)) if clearing else 0.0

    class_c = StrategyEconomics(
        name=f"Class C convergence @ {args.size:.0f}",
        edge_per_contract=mean_edge,
        fillable_contracts=args.size,
        opportunities_per_year=cycles * len(clearing),
        capital_required=max(mean_capital, 1e-9),
    )
    # Recorded, not re-measured: docs/SCANB-RESULTS.md, 78 completable groups priced at 25
    # contracts a leg, none positive, closest -0.00597/contract. Entered at its *best* observed
    # edge, which is the generous reading of a uniformly negative result.
    class_b = StrategyEconomics(
        name="Class B negRisk @ 25 (recorded)",
        edge_per_contract=-0.00597,
        fillable_contracts=25.0,
        opportunities_per_year=cycles * 78,
        capital_required=25.0,
    )

    print(f"\n[2/2] Ceiling at the horizon-limited maximum recurrence "
          f"({cycles:.0f} cycles/yr x distinct opportunities)")
    print(f"  {'strategy':<34} {'edge/ct':>9} {'opps/yr':>9} {'capital':>10} "
          f"{'gross/yr':>11} {'hurdle':>9}")
    rows = []
    for econ in rank_strategies([class_c, class_b]):
        hurdle = HURDLE_RATE * (deployable if econ is class_c else econ.capital_required)
        rows.append((econ, hurdle))
        print(f"  {econ.name:<34} {econ.edge_per_contract:>+9.5f} "
              f"{econ.opportunities_per_year:>9.0f} {econ.capital_required:>10.2f} "
              f"{econ.gross_annual_value:>11.2f} {hurdle:>9.2f}")

    print(f"\n{'=' * 88}\nVERDICT\n{'=' * 88}")
    if not clearing:
        print(f"  Not one of {priced} priced opportunities clears its own round trip inside the")
        print("  registered band. The ceiling on annual throughput is $0 at any recurrence, and")
        print("  no frequency rescues a non-positive edge.")
        print("\n  GATE 4.0: CAPACITY IS THE BINDING CONSTRAINT.")
        print("  Per the registered decision rule, no further edge search is licensed - more")
        print("  discovery optimises a non-constraint. The remaining moves are structural (a")
        print("  different role, market, or product) and each is a new registration.")
        print("=" * 88)
        return 0

    ceiling = class_c.gross_annual_value
    hurdle_dollars = HURDLE_RATE * deployable
    required = class_c.required_opportunities_for(hurdle_dollars)
    print(f"  distinct clearing opportunities : {len(clearing)}")
    print(f"  deployable capital now          : ${deployable:,.2f}")
    print(f"  generous annual ceiling         : ${ceiling:,.2f}")
    print(f"  hurdle ({HURDLE_RATE:.0%} on that capital)   : ${hurdle_dollars:,.2f}")
    print(f"  recurrence the hurdle requires  : {required:,.0f} opportunities/yr")
    print(f"  ...physically possible at a {DAYS_HELD:.0f}d hold: "
          f"{cycles * len(clearing):,.0f}/yr")

    clears = ceiling > hurdle_dollars
    label = "CEILING CLEARS THE FLOOR" if clears else "CAPACITY IS THE BINDING CONSTRAINT"
    print(f"\n  GATE 4.0: {label}")
    if clears:
        print("  Capacity is not the constraint at this size. Gate D and Gate 3 become worth")
        print("  their cost, and the operator's own hurdle - what the same effort earns")
        print("  elsewhere - is then the live question. This is a Level-0 screen (D3): it may")
        print("  kill a candidate and may not certify one.")
    else:
        print("  The generous ceiling does not clear the carry rate the cost model already")
        print("  charges this capital, so the strategy pays itself less than not trading.")
        print("  Per the registered decision rule, no further edge search is licensed.")
    print(f"\n  Passing this floor would be necessary, never sufficient: hit_rate is 1.0, fixed")
    print("  cost is $0, convergence is assumed complete, and impact is unmodelled.")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
