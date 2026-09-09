"""Gate 0b — is stratified search worth its own cost?

    python gate0b.py [--replications N] [--events N]

Gate 0 established that the stratified protocol's false-positive rate is controlled once the search
is priced against the distribution of the maximum, and that on the **strong diffuse** control it
detects far less than the unstratified protocol does. That second half is not yet an answer, because
``inject_signal`` misprices at every price and the whole case for stratifying is that a real edge is
concentrated. A protocol judged only against diffuse signal has not been judged against its own
hypothesis.

This runs both protocols against :func:`kairos.nullworld.inject_banded_signal`, where the market is
honest everywhere except one price band. The comparison is the decision:

- stratified **wins** here and loses when diffuse -> the choice of protocol is a bet on the shape of
  the signal, and must be pre-registered rather than picked once the answer is visible.
- stratified **loses** here too -> it costs more than it buys under any shape tested, and the
  candidate is dead. No further stratified work on real data.

Neither outcome licenses running it on the real dataset. That needs the winner to clear Gate 0's
power floor, which is a separate question this script also reports.

**Two limitations, both load-bearing:**

1. **The ceiling gates the verdict.** If the best forecast obtainable from the features is itself
   mostly undetected, this compares two instruments inside a world where neither could succeed, and
   the ordering it produces is about the world. The script refuses to conclude in that case.
2. **Only the final *test* is stratified here, not the protocol.** Candidates are still fitted on the
   whole fit split and selected on the whole select split, so the candidate handed to the stratified
   test was chosen to be good *on average* — which against a banded signal means chosen to capture
   nothing. A fully stratified protocol would fit and select within strata too. A loss here
   therefore falsifies **test-only stratification**, which is the cheap version, and leaves the
   fit-level version untested.
"""

from __future__ import annotations

import argparse
import time

from kairos.inference import paired_deltas, superiority_test
from kairos.nullworld import (
    ALPHA,
    POWER_FLOOR,
    achievable_oracle,
    add_noise_features,
    fair_market,
    inject_banded_signal,
    run_all_protocols,
)
from kairos.validity import assess

#: Bands to concentrate the signal in. ``mid`` is the case the real data suggested (mid-priced
#: contracts resolved NO far more often than their price implied); the others check that the finding
#: is about concentration itself and not about one band's arithmetic.
BANDS: tuple[tuple[str, tuple[float, float]], ...] = (
    ("mid", (0.40, 0.60)),
    ("lowmid", (0.15, 0.40)),
    ("highmid", (0.60, 0.85)),
)

PROTOCOLS = ("kairos", "strat_naive", "strat_maxt")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replications", type=int, default=24)
    ap.add_argument("--events", type=int, default=750)
    ap.add_argument("--contracts", type=int, default=4)
    ap.add_argument("--bias", type=float, default=0.8)
    ap.add_argument("--candidates", type=int, default=16)
    ap.add_argument("--boot", type=int, default=250)
    ap.add_argument("--seed", type=int, default=20260908)
    args = ap.parse_args()

    print("=" * 84)
    print("GATE 0b - DOES STRATIFIED SEARCH PAY FOR ITSELF WHEN THE SIGNAL IS CONCENTRATED?")
    print("=" * 84)
    print(f"  {args.events} events x {args.contracts} contracts, bias {args.bias:+.2f} in band, "
          f"{args.replications} replications, alpha {ALPHA}")

    t0 = time.time()
    rows: list[tuple[str, dict[str, float], float]] = []

    # Null control first: a banded *world shape* with no bias at all. If this over-rejects, nothing
    # measured below means anything, whatever the power numbers say (AXIOMS A7).
    print(f"\n  {'world':<22} " + " ".join(f"{p:>12}" for p in PROTOCOLS) + f"{'ceiling':>10}")
    print("  " + "-" * 70)

    for label, builder in [
        ("null (bias 0)", lambda s: add_noise_features(
            fair_market(n_events=args.events, contracts_per_event=args.contracts, seed=s), seed=s
        )),
    ] + [
        (f"banded:{name}", (lambda b: lambda s: inject_banded_signal(
            n_events=args.events, contracts_per_event=args.contracts,
            bias=args.bias, band=b, seed=s,
        ))(band))
        for name, band in BANDS
    ]:
        hits = {p: 0 for p in PROTOCOLS}
        tries = {p: 0 for p in PROTOCOLS}
        ceiling = 0
        for r in range(args.replications):
            s = args.seed + r * 101
            world = builder(s)
            res = run_all_protocols(
                world, n_candidates=args.candidates, alpha=ALPHA, n_boot=args.boot, seed=s
            )
            for p in PROTOCOLS:
                if p in res:
                    hits[p] += res[p].significant
                    tries[p] += 1
            # Ceiling: the best forecast obtainable from the features, tested the same way.
            orc = achievable_oracle(world)
            ceiling += superiority_test(
                orc, world.market, world.outcomes, world.cluster_ids,
                alpha=ALPHA, n_boot=args.boot, seed=s,
            ).significant
        rates = {p: (hits[p] / tries[p] if tries[p] else float("nan")) for p in PROTOCOLS}
        cr = ceiling / args.replications
        rows.append((label, rates, cr))
        print(f"  {label:<22} " + " ".join(f"{rates[p]:12.3f}" for p in PROTOCOLS)
              + f"{cr:10.3f}")

    print("  " + "-" * 70)
    print(f"  (null row is a false-positive rate; banded rows are power; "
          f"ceiling = best obtainable)")

    # ---- verdict ----
    print(f"\n{'=' * 84}\nVERDICT\n{'=' * 84}")
    null_rates = rows[0][1]
    banded = rows[1:]
    if null_rates["strat_maxt"] > 3 * ALPHA:
        print(f"  strat_maxt false-positive rate {null_rates['strat_maxt']:.3f} is out of control "
              f"at alpha={ALPHA}. Nothing below is interpretable.")
        print("=" * 84)
        return 1

    # ---- the guard that must come before any verdict, applied PER WORLD ----
    # Delegated to kairos.validity so a future runner inherits it instead of reimplementing it.
    # This exact check was recorded as fixed in CORRECTIONS Pass 4 (G0.2) and then omitted here in
    # Pass 9, because the Pass-4 fix lived as a property of Gate 0's report class (AXIOMS G3, G8).
    report = assess({lbl: c for lbl, _, c in banded}, POWER_FLOOR)
    for line in report.explain().splitlines():
        print(f"  {line}")
    if not report.may_conclude:
        print(f"\n  -> {report.refusal()}")
        print(f"\n  elapsed {time.time() - t0:.1f}s")
        print("=" * 84)
        return 2
    usable_names = {u.name for u in report.usable}
    valid = [(lbl, r, c) for lbl, r, c in banded if lbl in usable_names]

    wins = sum(1 for _, r, _ in valid if r["strat_maxt"] > r["kairos"])
    best_strat = max((r["strat_maxt"] for _, r, _ in valid), default=0.0)
    print(f"  stratified beat unstratified in {wins} of {len(valid)} usable "
          f"concentrated-signal worlds")
    print(f"  best stratified power {best_strat:.3f} against floor {POWER_FLOOR}")

    if wins == 0:
        print("\n  -> Stratified search loses to the unstratified protocol even when the signal is")
        print("     concentrated, which is the one shape it was proposed for. It costs more than it")
        print("     buys under every shape tested. DEAD - do not run it on real data (AXIOMS C9).")
    elif best_strat < POWER_FLOOR:
        print("\n  -> Stratified search wins the comparison but still cannot clear the power floor.")
        print("     A protocol that beats a weak alternative and detects nothing is not an")
        print("     instrument. More events before this is usable, not more strata (AXIOMS A1).")
    else:
        print("\n  -> Stratified search pays for itself on a concentrated signal and clears the")
        print("     power floor. The protocol choice is now a BET ON SIGNAL SHAPE and must be")
        print("     pre-registered in docs/PROTOCOL.md BEFORE it touches real data (AXIOMS A8).")
    print(f"\n  elapsed {time.time() - t0:.1f}s")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
