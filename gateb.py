"""Gate B — can the Class B pipeline correctly find NOTHING?

    python gateb.py [--groups N] [--horizons ...]

``docs/CENSUS-RESULTS.md`` Decision 001 held Class B behind this gate: its false-positive mode is
**unmeasured and severe**, and a scanner built before its gate repeats the error Gate 0 exists to
prevent (AXIOMS A7).

Structurally identical to Gate 0 and deliberately so — null worlds, a positive control, a rate that
must not exceed chance, and a power floor — but the failure being falsified is different. Gate 0
asks whether the pipeline invents *forecasting skill*. Gate B asks whether it invents *riskless
profit*, which needs no forecasting to be wrong about.

**Pass — both conditions:**

1. **False positives.** No arbitrage-free world's fire rate exceeds what chance allows, judged by
   the exact binomial tail rather than an invented tolerance.
2. **Power.** A genuine, fillable, post-cost edge is detected at least ``POWER_FLOOR`` of the time.
   A scanner that refuses everything passes condition 1 trivially and is worth nothing.

`scan_naive` is carried through every world as an **exhibit**. It is expected to fail, and the size
of its failure is the empirical case for every refusal in `scan`.
"""

from __future__ import annotations

import argparse
import time

from kairos.nullworld import ALPHA, POWER_FLOOR, _binomial_tail  # one implementation, not two
from kairos.structural import (
    add_quote_noise,
    believed_complete,
    fair_group,
    hide_an_outcome,
    inject_arbitrage,
    marginally_unprofitable,
    obvious_arbitrage,
    scan,
    scan_naive,
    thin_the_book,
    truncate_legs,
)

#: Horizons to sweep. Long horizons are included **because** that is where the repo's two carry
#: models disagree (0.0034 at one year, 0.0129 at two) and where negRisk groups are most numerous.
#: Excluding them would hide the failure mode the gate exists to find.
HORIZONS = (7.0, 30.0, 90.0, 365.0, 730.0)

#: Edge for the positive control: comfortably above the round-trip cost of a 5-leg group, so a
#: failure to detect is a statement about the scanner rather than about the size of the edge.
CONTROL_EDGE = 0.05


#: (name, has_signal, is_exhibit). Exhibits are reported and never gate: they measure a risk the
#: scanner structurally cannot carry, so failing them is information rather than a defect.
def worlds(n_legs: int, days: float, seed: int):
    """Arbitrage-free worlds, two positive controls, and two exhibits."""
    base = fair_group(n_legs=n_legs, days=days, seed=seed)
    truncated = truncate_legs(base, keep=max(2, n_legs - 2), seed=seed)
    return [
        ("fair", False, False, base),
        ("fair+noise", False, False, add_quote_noise(base, seed=seed)),
        ("truncated", False, False, truncated),
        ("non_exhaustive", False, False, hide_an_outcome(base)),
        ("thin_book", False, False, thin_the_book(obvious_arbitrage(base))),
        # The discriminating null: structure impeccable, only the cost arithmetic says no.
        ("marginal", False, False, marginally_unprofitable(base)),
        # Exhibit: truncation the scanner is told does not exist. No arithmetic can fix this.
        ("truncated_believed", False, True, believed_complete(truncated)),
        # Two controls. The second is defined without reference to the scanner's own cost formula.
        ("ARB circular", True, True, inject_arbitrage(base, edge=CONTROL_EDGE)),
        ("ARB independent", True, False, obvious_arbitrage(base)),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", type=int, default=200, help="groups per world per horizon")
    ap.add_argument("--min-legs", type=int, default=3)
    ap.add_argument("--max-legs", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260908)
    args = ap.parse_args()

    print("=" * 92)
    print("GATE B - CAN THE CLASS B PIPELINE CORRECTLY FIND NOTHING?")
    print("=" * 92)
    print(f"  {args.groups} groups per world per horizon, {args.min_legs}-{args.max_legs} legs, "
          f"alpha {ALPHA}, power floor {POWER_FLOOR}")
    print(f"  horizons (days): {', '.join(f'{h:.0f}' for h in HORIZONS)}")
    t0 = time.time()

    names: list[str] = []
    fires: dict[tuple[str, float], int] = {}
    naive_fires: dict[tuple[str, float], int] = {}
    has_signal: dict[str, bool] = {}
    is_exhibit: dict[str, bool] = {}

    for days in HORIZONS:
        for i in range(args.groups):
            seed = args.seed + i * 131
            n_legs = args.min_legs + (i % (args.max_legs - args.min_legs + 1))
            for name, signal, exhibit, group in worlds(n_legs, days, seed):
                if name not in has_signal:
                    names.append(name)
                    has_signal[name] = signal
                    is_exhibit[name] = exhibit
                key = (name, days)
                fires[key] = fires.get(key, 0) + int(scan(group).fires)
                naive_fires[key] = naive_fires.get(key, 0) + int(scan_naive(group).fires)

    # ---- per-horizon table ----
    print(f"\n{'=' * 92}")
    print("FIRE RATE BY WORLD AND HORIZON   (disciplined scanner / naive exhibit)")
    print("=" * 92)
    header = f"  {'world':<18} {'signal':<7}" + "".join(f"{d:>13.0f}d" for d in HORIZONS)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for name in names:
        row = f"  {name:<18} {str(has_signal[name]):<7}"
        for d in HORIZONS:
            r = fires[(name, d)] / args.groups
            nr = naive_fires[(name, d)] / args.groups
            row += f"{r:>7.3f}/{nr:<6.3f}"
        print(row)

    # ---- verdict ----
    print(f"\n{'=' * 92}\nVERDICT\n{'=' * 92}")
    failures: list[str] = []
    for name in names:
        total = sum(fires[(name, d)] for d in HORIZONS)
        n = args.groups * len(HORIZONS)
        rate = total / n
        if is_exhibit[name]:
            print(f"  exhibit  {name:<18} {rate:6.3f}  (reported, never gates)")
            continue
        if has_signal[name]:
            ok = rate >= POWER_FLOOR
            print(f"  POWER    {name:<16} {rate:6.3f}  (floor {POWER_FLOOR})  "
                  f"{'PASS' if ok else 'FAIL (inert)'}")
            if not ok:
                failures.append(f"{name}: power {rate:.3f} below {POWER_FLOOR}")
        else:
            tail = _binomial_tail(total, n, ALPHA)
            ok = tail >= 0.01
            print(f"  FPR      {name:<16} {rate:6.3f}  (binom p {tail:.4f})  "
                  f"{'PASS' if ok else 'FAIL (over-fires)'}")
            if not ok:
                failures.append(f"{name}: fires at {rate:.3f} in an arbitrage-free world")

    naive_worst = max(
        (sum(naive_fires[(n_, d)] for d in HORIZONS) / (args.groups * len(HORIZONS))
         for n_ in names if not has_signal[n_] and not is_exhibit[n_]),
        default=0.0,
    )
    print(f"\n  exhibit: the naive scanner fires at up to {naive_worst:.3f} in worlds that contain")
    print("  no arbitrage at all. Every refusal in `scan` is paid for by that number.")

    print()
    if failures:
        print("  GATE B: FAIL")
        for f in failures:
            print(f"    - {f}")
        print("\n  No Class B scanner is built against real markets (Decision 001, AXIOMS A7).")
        print("  Fix the pipeline. Do NOT tune the worlds until it passes (A8).")
    else:
        print("  GATE B: PASS")
        print("  The pipeline finds nothing where there is nothing, and finds a real edge when")
        print("  there is one. A scanner against real negRisk groups is now licensed - and is")
        print("  still only a CANDIDATE generator, never a confirmed arbitrage (A5, D1).")
    print(f"\n  elapsed {time.time() - t0:.1f}s")
    print("=" * 92)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
