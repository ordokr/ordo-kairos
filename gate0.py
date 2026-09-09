"""Run the Gate-0 null-world falsification harness.

    python gate0.py [--quick]

``docs/PROTOCOL.md`` Gate 0. This ranks above all strategy discovery: before asking whether Kairos
can find an edge, we ask whether it reliably fails to find one that does not exist - and whether it
can still see one that does.

A FAIL here stops Stage 0. The response is to fix the pipeline, never to soften the null worlds
(``docs/AXIOMS.md`` A8).
"""

from __future__ import annotations

import sys
import time

from kairos.nullworld import ALPHA, FPR_TAIL_ALPHA, POWER_FLOOR, run_gate0

QUICK = "--quick" in sys.argv

print("=" * 86)
print("GATE 0 - NULL-WORLD FALSIFICATION OF KAIROS ITSELF")
print("=" * 86)
print(
    "Question: can this pipeline correctly discover NOTHING when there is nothing to discover,\n"
    "          while still detecting a signal that is genuinely there?\n"
)
print("Pre-registered thresholds (changing these after a result is a CORRECTIONS entry):")
print(f"  alpha                    {ALPHA}")
print(f"  power floor (strong)     {POWER_FLOOR}")
print(f"  FPR binomial tail alpha  {FPR_TAIL_ALPHA}")
print()
print("Protocols:")
print("  naive    fit+select on all data, IID inference        (expected to FAIL - exhibit)")
print("  cluster  fit+select on all data, cluster inference    (isolates selection bias)")
print("  kairos   fit/select/sealed-holdout, cluster inference (the gate condition)")
print()

kwargs = dict(replications=12, n_candidates=10, n_boot=200) if QUICK else {}
if QUICK:
    print("[--quick] reduced replications; indicative only, not a gate result.\n")

start = time.time()
report = run_gate0(progress=lambda line: print(f"  ... {line}", flush=True), **kwargs)
elapsed = time.time() - start

print()
print(report.explain())
print(f"\nelapsed {elapsed:.1f}s")

if not report.passed:
    print(
        "\nGate 0 FAILED. Stage 0 does not begin. Fix the pipeline; do not tune the null worlds."
    )
    sys.exit(1)
print("\nGate 0 passed. The instrument holds its false-positive rate and is not inert.")
