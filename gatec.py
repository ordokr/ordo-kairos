"""Gate C — can the cross-venue pairing pipeline correctly find NOTHING?

    python gatec.py [--pairs N] [--seed S]

``docs/PROTOCOL.md`` Gate C registers this gate ahead of the measurement it licenses, for the same
reason Decision 001 held Class B behind Gate B: the false-positive mode is **unmeasured and severe**,
and a scanner built before its gate repeats the error Gate 0 exists to prevent (AXIOMS A7).

The failure being falsified is **semantic non-fungibility** — two markets that look identical and
resolve differently. A pipeline that pairs them does not merely find a phantom edge; it books a
position it believes is hedged and is not, which is worse than a missed trade because both legs can
lose together.

**Pass — both conditions, as registered:**

1. **False positives.** No null world's pairing rate exceeds what chance allows, judged by the exact
   binomial tail rather than an invented tolerance.
2. **Power.** True pairs — the same event, phrased as each venue phrases it — are matched at least
   ``POWER_FLOOR`` of the time. A matcher that refuses everything passes condition 1 trivially and
   is worth nothing.

**Validity is asserted before any verdict, per unit** (``kairos.validity``, AXIOMS G3/G4). A null
world is only usable if **every** pair in it is genuinely non-identical: contamination by even one
true pair makes its false-positive rate uninterpretable, so the floor there is 1.000, not the power
floor. The control is usable only if the oracle can pair it at all.

``same_event_naive`` is carried through every world as an **exhibit**, and reported at the threshold
that is *best for it* rather than a convenient one — so its failure is a lower bound on the
difficulty rather than a strawman.
"""

from __future__ import annotations

import argparse
import time

from kairos.identity import (
    CONTROL_WORLD,
    NULL_WORLDS,
    WORLDS,
    build_pair,
    same_event,
    same_event_oracle,
    title_similarity,
)
from kairos.nullworld import ALPHA, POWER_FLOOR, _binomial_tail  # one implementation, not two
from kairos.validity import assess

#: Thresholds swept for the naive exhibit. It is given its best shot on purpose.
NAIVE_GRID = tuple(round(0.40 + 0.01 * i, 2) for i in range(60))

#: A null world is usable only if every pair in it is genuinely a non-pair. Unlike a power ceiling
#: this is a construction invariant, not a statistical quantity, so the floor is exact.
NULL_CEILING_FLOOR = 1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=400, help="pairs generated per world")
    ap.add_argument("--seed", type=int, default=20260909)
    args = ap.parse_args()

    print("=" * 92)
    print("GATE C - CAN THE CROSS-VENUE PAIRING PIPELINE CORRECTLY FIND NOTHING?")
    print("=" * 92)
    print(f"  {args.pairs} pairs per world, alpha {ALPHA}, power floor {POWER_FLOOR}")
    print("  synthetic published text only. NO market data is fetched by this gate.")
    t0 = time.time()

    matched: dict[str, int] = {}
    oracle_correct: dict[str, int] = {}
    sims: dict[str, list[float]] = {}
    refusal_counts: dict[str, dict[str, int]] = {}

    for world, _ in WORLDS:
        matched[world] = 0
        oracle_correct[world] = 0
        sims[world] = []
        refusal_counts[world] = {}
        for i in range(args.pairs):
            pair = build_pair(world, args.seed + i * 131)
            verdict = same_event(pair.left, pair.right)
            matched[world] += int(verdict.paired)
            for reason in verdict.refusals:
                key = reason.split(":")[0] if reason.startswith("unrecoverable") else reason
                refusal_counts[world][key] = refusal_counts[world].get(key, 0) + 1
            truth = same_event_oracle(pair.left_identity, pair.right_identity)
            oracle_correct[world] += int(truth.paired == pair.truly_same)
            sims[world].append(title_similarity(pair.left, pair.right))

    n = args.pairs
    control = CONTROL_WORLD[0]
    null_names = [name for name, _ in NULL_WORLDS]

    # ---- naive exhibit, at the threshold most favourable to it ----
    best_t, best_obj, best_power, best_worst = NAIVE_GRID[0], -2.0, 0.0, 1.0
    for t in NAIVE_GRID:
        power = sum(s >= t for s in sims[control]) / n
        worst = max(sum(s >= t for s in sims[w]) / n for w in null_names)
        if power - worst > best_obj:
            best_t, best_obj, best_power, best_worst = t, power - worst, power, worst
    naive_rate = {w: sum(s >= best_t for s in sims[w]) / n for w, _ in WORLDS}

    # ---- validity, per unit, before any verdict ----
    print(f"\n{'=' * 92}")
    print("VALIDITY - may this run announce a verdict at all?")
    print("=" * 92)
    null_report = assess({w: oracle_correct[w] / n for w in null_names}, NULL_CEILING_FLOOR)
    control_report = assess({control: oracle_correct[control] / n}, POWER_FLOOR)
    print(null_report.explain())
    print(control_report.explain())
    if not null_report.may_conclude or not control_report.may_conclude or null_report.excluded:
        print()
        print(null_report.refusal() or control_report.refusal()
              or "NO VERDICT. A null world contains pairs that are genuinely the same event, so its "
                 "false-positive rate measures the world and not the matcher.")
        print("=" * 92)
        return 2

    # ---- per-world table ----
    print(f"\n{'=' * 92}")
    print("PAIRING RATE BY WORLD   (matcher under test / naive title-similarity exhibit)")
    print("=" * 92)
    print(f"  {'world':<26} {'same?':<6} {'matcher':>9} {'naive':>9}   principal refusal")
    print("  " + "-" * 88)
    for world, _ in WORLDS:
        truly_same = world == control
        top = sorted(refusal_counts[world].items(), key=lambda kv: -kv[1])[:1]
        reason = f"{top[0][0]} ({top[0][1]}/{n})" if top else "-"
        print(f"  {world:<26} {str(truly_same):<6} {matched[world] / n:>9.3f} "
              f"{naive_rate[world]:>9.3f}   {reason}")

    # ---- verdict ----
    print(f"\n{'=' * 92}\nVERDICT\n{'=' * 92}")
    failures: list[str] = []

    power = matched[control] / n
    ok = power >= POWER_FLOOR
    print(f"  POWER    {control:<24} {power:6.3f}  (floor {POWER_FLOOR})  "
          f"{'PASS' if ok else 'FAIL (inert)'}")
    if not ok:
        failures.append(f"{control}: power {power:.3f} below {POWER_FLOOR}")

    for world in null_names:
        rate = matched[world] / n
        tail = _binomial_tail(matched[world], n, ALPHA)
        ok = tail >= 0.01
        print(f"  FPR      {world:<24} {rate:6.3f}  (binom p {tail:.4f})  "
              f"{'PASS' if ok else 'FAIL (pairs non-identical events)'}")
        if not ok:
            failures.append(f"{world}: pairs at {rate:.3f} in a world with no true pair")

    # ---- the exhibit, reported as what it is rather than as a fire rate ----
    invisible = [w for w in null_names if sims[w] == sims[control]]
    print(f"\n  EXHIBIT - title similarity, swept over {len(NAIVE_GRID)} thresholds and reported at")
    print(f"  its OWN best ({best_t:.2f}): power {best_power:.3f} against a worst null pairing rate")
    print(f"  of {best_worst:.3f}. Best achievable separation {best_obj:+.3f}.")
    if best_obj <= 0.0:
        print("\n  That separation is not small. It is NON-POSITIVE: no similarity threshold")
        print("  exists at which this matcher pairs true events more often than it pairs")
        print("  non-events. The exhibit is not weak evidence, it is no evidence.")
    if invisible:
        print(f"\n  And the reason is measurable, not rhetorical. For {', '.join(invisible)}")
        print("  the similarity vector is IDENTICAL to the control's, pair for pair - because the")
        print("  titles are identical. Those markets differ in the resolution source and in the")
        print("  settlement clock time, and a venue puts neither in the title. The evidence that")
        print("  separates a hedge from a double position is not in the text the eye compares.")
    print("\n  That is what every refusal in `same_event` is paid for.")

    print()
    if failures:
        print("  GATE C: FAIL")
        for f in failures:
            print(f"    - {f}")
        print("\n  No paired venue data is fetched (PROTOCOL Gate C, AXIOMS A7).")
        print("  Fix the matcher. Do NOT tune the worlds until it passes (A8).")
    else:
        print("  GATE C: PASS")
        print("  The matcher refuses every registered near-miss and still pairs the same event")
        print("  across two venues' phrasings. Fetching paired data is now licensed.")
        print()
        print("  What this does NOT establish, and must not be read as establishing:")
        print("   - coverage of real venue phrasing. The text here is ours; this falsifies the")
        print("     matcher's LOGIC, not its reach over titles neither venue has been asked for.")
        print("   - that a venue publishes the evidence at all. The oracle ceiling is computed on")
        print("     ground truth, so it proves a world CONTAINS a mismatch, not that the mismatch")
        print("     is recoverable from what is published. On real data those look identical from")
        print("     inside the matcher and have to be told apart by hand.")
        print("   - that a paired market is tradeable. Gate C licenses a MEASUREMENT, and the")
        print("     measurement's own kill rule still stands (A5, D1, F3).")
    print(f"\n  elapsed {time.time() - t0:.1f}s")
    print("=" * 92)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
