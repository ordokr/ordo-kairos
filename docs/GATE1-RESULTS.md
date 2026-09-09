# Gate 1 — Results

**Verdict: `q_ref` REJECTED. The raw market quote is the benchmark.**
Run 2026-09-08. Reproduce with `python gate1.py --pages 20 --limit 900`.

---

## Dataset

Polymarket resolved markets, admitted on **measured history density** rather than nominal horizon.

| | |
|---|---|
| Markets scanned | ~1,683 |
| Rejected: no history / thin history / no decision point or out of band | 21 / 223 / 539 |
| **Admitted observations** | **900** |
| **Independent events** | **731** (Gate-0 requirement: 300) |
| Development / sealed holdout | 548 events (604 rows) / **183 events (296 rows)** |
| Out-of-sample fold predictions | 422 rows across 366 events |

Decision point is the last price at least **24 h** before trading stopped; resolution time comes
from the last observed trade, not `endDate`. Splits are by event, chronological, expanding-window.
The holdout was queried **once**.

---

## Result

| baseline | complexity | log score | vs `A_raw` | p | verdict |
|---|---|---|---|---|---|
| `A_raw` | 0 | 0.33607 | — | — | benchmark |
| `B_settle` | 1 | 0.33599 | +0.00008 | **0.0005** | significant but **immaterial (0.02%)** |
| `C_logit` | 1 | 0.32266 | **+0.01341** | 0.1139 | no reproducible gain |
| `C_iso` | 1 | 0.37506 | **−0.03899** | 0.8621 | actively worse |
| `D_both` | 2 | 0.32263 | +0.01344 | 0.1134 | no reproducible gain |

**No transformation of the market price beat the raw quote out of sample.** `baseline.py`'s central
premise fails its own gate.

---

## The four things this run established

### 1. Significance without materiality — a flaw in the selection rule, caught by the run

`B_settle` was initially declared a survivor on **p = 0.0005**, then failed the sealed holdout
(p = 0.3258). Its "win" was a gain of **+0.00008 nats — 0.02% of a 0.336 benchmark**, with a cluster
SE of 0.00002.

The mechanism: settlement un-discounting is a *tiny, deterministic, monotone* transform, so the
paired score differences have almost no variance. A trivial effect is then easy to detect. The
original selection rule gated on significance alone and duly selected it.

Fixed by requiring a survivor to clear **both** significance and a materiality floor (gain ≥ 1% of
the benchmark log score). **The fix does not change this verdict** — with it applied, `B_settle` is
excluded on materiality, `C_logit`/`D_both` were already excluded on significance, no survivors
remain, and `A_raw` wins either way. Both runs are on record. This is logged in
[`CORRECTIONS.md`](CORRECTIONS.md) so a rule change made after seeing a result is not mistaken for a
post-hoc rescue.

### 2. The settlement adjustment was untestable on this sample — a scope limit, not a finding

Median admitted market life is about **7 days**. At 6%/yr the settlement wedge over 7 days is
**~0.11%**, which is why `B_settle` moved the log score by 0.02%. This sample of recently-resolved
markets contains almost no settlement exposure.

**Gate 1 has therefore not tested the settlement adjustment.** Doing so requires long-dated resolved
contracts. Anything claiming this run refuted Gebele & Matthes would be misreading it.

### 3. Isotonic recalibration is actively harmful here

`C_iso` scored **−0.039** against raw — the worst of the five, and worse than the logistic form on
the same data. This confirms empirically the warning that isotonic overfits on sparse data, and it
settles the family question PROTOCOL Gate 1 asked: **logistic over isotonic**, decisively.

### 4. `C_logit` is underpowered, not disproven — and the distinction matters

`C_logit` and `D_both` showed a **materially sized** effect (+0.0134, ≈4% of the benchmark) that the
data could not separate from noise (p ≈ 0.11). Under AXIOMS A1, *"not enough evidence" is not "no
effect."*

From p = 0.1139 one-sided, t ≈ 1.21; reaching t ≈ 1.65 needs about **1.86×** the events, i.e.
roughly **680 fold-events / ~1,500–2,000 total**. That is the concrete re-test trigger.

**Double-counting check (AXIOMS C7):** `D_both − B_settle = −0.01336` on log score. They are *not*
indistinguishable, so the recalibration is doing work the settlement adjustment is not. The two
corrections are not redundant — but neither is proven.

---

## Consequences

1. **Gate 2 uses raw `q` as the benchmark.** `q_ref` has not earned the substitution.
2. **`kairos/baseline.py` is disabled by default, not deleted.** Strict C9 says remove what does not
   show a reproducible gain. Deleting on an *underpowered* null would violate A1, so it is retained
   with a named trigger: **re-run Gate 1 at ≥1,500 events. If `C_logit` still fails, delete it.**
   That tension is recorded rather than resolved by preference.
3. **Isotonic is removed from the baseline family** for this problem. That one *is* a clean negative.
4. **The census's Class-A supply claim is confirmed end to end** — 731 independent events assembled
   and scored from public data, above the 300 requirement.

---

## Limitations

- **One venue, one period.** Recently-resolved Polymarket markets, mostly short-horizon.
- **Admission is selective.** 900 of ~1,683 scanned. The price band `[0.02, 0.98]` and the 24 h lead
  both bite; results describe mid-range, multi-day markets and do not generalise to longshots or
  minutes-to-resolution contracts.
- **Not an edge test.** Gate 1 compares transformations of the *market's own price*. It says nothing
  about whether any forecaster can beat that price — that is Gate 2, and it remains entirely open.
