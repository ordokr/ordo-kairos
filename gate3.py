"""Gate 3.0 for Class M: does the fill arrive at all?

    python gate3.py [--markets 250] [--size 25]

``docs/PROTOCOL.md`` Gate 3.0. Registered 2026-09-14, before this was built and before any book depth
was fetched for the measured set.

Gate M measured what a fill is **worth** — ``R(60) = +0.00039``, 3.9% of the quoted half-spread. It
measured nothing about whether a fill **happens**. Price priority puts the resting size ahead of a
new order, so an entrant joining the back of the touch queue sees nothing until that size is
consumed, and **where a day's one-sided flow is smaller than the size already resting, the entrant is
never filled and earns exactly zero whatever the spread.**

Two strategies, both measured
-----------------------------

**(a) Join the back.** Fills ``max(0, side_flow - touch_depth)`` a day at the full quoted
half-spread times the measured retention.

**(b) Improve by one tick.** First in the queue, so every contract of one-sided flow reaches it, but
the capture is ``(spread - 2 ticks) / 2`` instead of ``spread / 2``. Reported as the **generous**
variant and it is generous twice over: it assumes an entrant is never outbid, which is false the
moment an incumbent requotes, and it applies a retention measured on *aggregate* flow to
*best-quote* fills, which are the ones most exposed to informed traders.

**No null gate, deliberately.** A7 requires one before a *search*. This is a single registered
arithmetic on two measured quantities with no hypothesis space and no estimator to fool, exactly as
Gates D.0 and 4.0 were. Stated because skipping a null gate is normally the error rather than the
plan.

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
from gatem import open_universe, quote

#: Measured by `scanm.py` on 237 markets and 276,421 pooled observations: R(60) = +0.00039 against a
#: median quoted half-spread of +0.01000. Carried as a **ratio** because it is the transferable
#: quantity - each market here has its own spread. See docs/SCANM-RESULTS.md.
RETENTION = 0.00039 / 0.01000

#: Unchanged from Gate M.0 so the two are comparable. Absolute dollars, never a rate (Pass 27.1).
FLOOR_ANNUAL = 104.70

DAYS_PER_YEAR = 365.0
MIN_MARKETS = 50

#: C11. The registration froze no posted size, which is itself the defect Pass 30.2 records; the
#: curve is reported so no single point can be presented as the answer after the fact.
SIZES = (5.0, 25.0, 100.0, 500.0, 2000.0)


def side_flow_contracts(daily_dollar_volume: float, price: float) -> float:
    """One side's daily flow in **contracts**.

    Depth is quoted in contracts and ``volumeNum`` in dollars, so comparing them directly would be
    the units error Pass 27.1 recorded. Dollars become contracts at the traded price, and one side
    sees half the two-sided volume.
    """
    if price <= 0.0:
        return 0.0
    return (daily_dollar_volume / price) / 2.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=21)
    ap.add_argument("--markets", type=int, default=250)
    ap.add_argument("--size", type=float, default=25.0)
    args = ap.parse_args()

    print("=" * 88)
    print("GATE 3.0 (Class M) - DOES THE FILL ARRIVE AT ALL?")
    print("=" * 88)
    print(f"  retention {RETENTION:.1%} of the quoted half-spread (measured, scanm.py)")
    print(f"  floor ${FLOOR_ANNUAL:.2f}/yr absolute | preconditions: longshot band, tick room > 1")
    print("  Expectation recorded before the run: markets wide enough to quote in are wide because")
    print("  they are QUIET, so (a) should approach zero fills and (b) is the interesting one.")
    print("  NOTHING IS TRADED OR QUOTED.")

    print(f"\n[1/3] Sweeping for in-band markets with tick room...", flush=True)
    census: collections.Counter[str] = collections.Counter()
    eligible: list[tuple[dict, float, float, float, float]] = []
    for m in open_universe(args.pages):
        q = quote(m)
        if isinstance(q, str):
            census[q] += 1
            continue
        spread, tick, price, daily_vol = q
        if spread / tick <= 1.0 + 1e-9:
            census["no_tick_room"] += 1
            continue
        eligible.append((m, spread, tick, price, daily_vol))
    print(f"      {'eligible (in band, tick room)':<34} {len(eligible)}")

    print(f"\n[2/3] Fetching real books for up to {args.markets} of them...", flush=True)
    rows: list[tuple[str, float, float, float, float, float]] = []
    for m, spread, tick, price, daily_vol in eligible[:args.markets]:
        try:
            token = json.loads(m["clobTokenIds"])[0]
        except (KeyError, ValueError, TypeError, IndexError):
            census["bad_token"] += 1
            continue
        book, why = fetch_book_result(str(token))
        if book is None:
            census[f"unfetchable:{why}"] += 1
            continue
        if not book.bids or not book.asks:
            census["one_sided_book"] += 1
            continue
        touch = (book.bids[0].size + book.asks[0].size) / 2.0
        flow = side_flow_contracts(daily_vol, price)
        # Both variants are capped at the size actually posted, once a day. The registration wrote
        # (a) as `max(0, flow - depth)` with no cap, which lets one entrant absorb every contract of
        # excess flow at unlimited size - and made (a) beat (b), which is structurally impossible.
        # One posting a day is conservative and is stated rather than tuned (CORRECTIONS Pass 30.1).
        cap_a = CONSERVATIVE.maker_capture(spread, price) * RETENTION
        cap_b = CONSERVATIVE.maker_capture(max(spread - 2 * tick, 0.0), price) * RETENTION
        rows.append((str(m.get("question", ""))[:40], touch, flow, cap_a, cap_b, spread))
        time.sleep(0.03)

    for key, count in census.most_common(8):
        print(f"      {key:<34} {count}")
    print(f"      {'books measured':<34} {len(rows)}")

    if len(rows) < MIN_MARKETS:
        print(f"\n  WITHHELD - {len(rows)} books against a floor of {MIN_MARKETS}. Apparatus, not")
        print("  a capacity finding (AXIOMS A1, G12).")
        return 0

    starved = sum(1 for _, touch, flow, _, _, _ in rows if flow <= touch)

    def annual(size: float) -> tuple[float, float]:
        a = sum(min(queue_fills(flow, touch), size) * ca for _, touch, flow, ca, _, _ in rows)
        b = sum(min(flow, size) * cb for _, _, flow, _, cb, _ in rows)
        return a * DAYS_PER_YEAR, b * DAYS_PER_YEAR

    print(f"\n[3/3] Queue depth against daily one-sided flow")
    print(f"  median touch depth (contracts)   : {median(r[1] for r in rows):,.0f}")
    print(f"  median one-sided daily flow      : {median(r[2] for r in rows):,.0f}")
    print(f"  markets where the queue NEVER clears in a day : {starved}/{len(rows)} "
          f"({starved / len(rows):.1%})")

    # C11: a design variable is not held at one value. The registration failed to freeze a size at
    # all, so the curve is the result and no single point on it may be presented as the answer.
    print(f"\n  {'posted size':>12} {'(a) back of queue':>20} {'(b) improve':>16}   floor "
          f"${FLOOR_ANNUAL:,.2f}")
    for size in SIZES:
        a, b = annual(size)
        print(f"  {size:>12,.0f} {'$' + format(a, ',.2f'):>20} {'$' + format(b, ',.2f'):>16}   "
              f"{'a' if a > FLOOR_ANNUAL else '-'}{'b' if b > FLOOR_ANNUAL else '-'}")

    annual_a, annual_b = annual(args.size)
    print(f"\n{'=' * 88}\nVERDICT (at the --size default of {args.size:.0f})\n{'=' * 88}")
    a_ok, b_ok = annual_a > FLOOR_ANNUAL, annual_b > FLOOR_ANNUAL
    if not a_ok and not b_ok:
        print("  GATE 3.0: REFUTED - neither variant clears the floor.")
        print("  An entrant cannot get filled often enough for the surviving spread to matter.")
        print("  Per the registered decision rule Class M closes, and with Classes A, B and C")
        print("  already closed, every hypothesis class in the programme has been tested and")
        print("  none survives. The registered programme ends.")
    elif b_ok and not a_ok:
        print("  GATE 3.0: Class M survives ONLY as a quote-improvement strategy.")
        print("  Joining the queue earns nothing: the resting size is not consumed often enough.")
        print("  Improving the quote clears the floor, but that number is generous twice over -")
        print("  it assumes an entrant is never outbid, and applies a retention measured on")
        print("  aggregate flow to best-quote fills, which are the most informed. Competitive")
        print("  response is the next question and is a NEW registration, not licensed here.")
    else:
        print("  GATE 3.0: both variants clear. Class M survives; Gate 4 re-runs against maker")
        print("  numbers rather than taker ones.")
    print(f"\n  Unmodelled and all cutting against: competitive requoting, adverse selection at")
    print("  the touch, partial fills, cancellation. Maker rewards are excluded and cut for.")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
