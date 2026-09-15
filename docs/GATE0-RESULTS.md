# Gate 0 — Results

> **Note 2026-09-09.** The stratified protocol `strat_maxt` was added as a gate condition while
> the decision to adopt stratification was live, briefly turning this gate's headline to FAIL on a
> protocol Gate 0b had already rejected. It is now an exhibit: reported, never gating. The verdict
> below is unchanged — a rejected challenger must not gate the incumbent (CORRECTIONS Pass 15).

**Verdict: PASS.** Run 2026-09-08. Reproduce with `python gate0.py`.

Configuration: 750 events × 4 contracts = 3,000 rows per world, split by event into
fit / select / sealed-holdout (250 events each). 30 replications per cell, 12 candidate
forecasters per replication, 300 bootstrap resamples, one-sided α = 0.05.

---

## Result

```
world                          protocol  signal     rate   binom p  verdict
--------------------------------------------------------------------------------------
fair_market+noise              naive     False     0.867         -  exhibit
fair_market+noise              cluster   False     0.067         -  exhibit
fair_market+noise              kairos    False     0.000    1.0000  PASS
martingale_market+noise        naive     False     0.867         -  exhibit
martingale_market+noise        cluster   False     0.167         -  exhibit
martingale_market+noise        kairos    False     0.067    0.4465  PASS
fair_market+shuffled+noise     naive     False     0.267         -  exhibit
fair_market+shuffled+noise     cluster   False     0.200         -  exhibit
fair_market+shuffled+noise     kairos    False     0.033    0.7854  PASS
fair_market+noise+timeshift    naive     False     0.833         -  exhibit
fair_market+noise+timeshift    cluster   False     0.033         -  exhibit
fair_market+noise+timeshift    kairos    False     0.067    0.4465  PASS
microstructure_placebo+noise   naive     False     0.833         -  exhibit
microstructure_placebo+noise   cluster   False     0.100         -  exhibit
microstructure_placebo+noise   kairos    False     0.000    1.0000  PASS
signal_strong                  naive     True      1.000         -  exhibit
signal_strong                  cluster   True      1.000         -  exhibit
signal_strong                  kairos    True      0.667         -  PASS
signal_strong                  oracle    True      0.767         -  exhibit
signal_moderate                naive     True      1.000         -  exhibit
signal_moderate                cluster   True      1.000         -  exhibit
signal_moderate                kairos    True      0.333         -  exhibit
signal_moderate                oracle    True      0.300         -  exhibit
signal_weak                    naive     True      1.000         -  exhibit
signal_weak                    cluster   True      0.567         -  exhibit
signal_weak                    kairos    True      0.067         -  exhibit
signal_weak                    oracle    True      0.133         -  exhibit
--------------------------------------------------------------------------------------
power curve                kairos   oracle   (oracle = ceiling)
    signal_strong           0.667    0.767  <- gate condition
    signal_moderate         0.333    0.300
    signal_weak             0.067    0.133
--------------------------------------------------------------------------------------
GATE 0: PASS   (alpha=0.05, power floor=0.5, worst null rate=0.067, oracle ceiling=0.767)
```

---

## What this establishes

**1. The sealed protocol holds its false-positive rate.** Across five structurally different null
worlds the rejection rate was 0.000–0.067 against a nominal 0.05, with the worst binomial tail at
0.4465 — comfortably consistent with chance.

**2. The instrument is not inert.** 0.667 power on the strong control, against an oracle ceiling of
0.767. Kairos captures **87% of the theoretically attainable power** at this sample size. That
number matters more than the raw power: it says the remaining loss is sample size, not method.

**3. Both undisciplined protocols fail, and they fail differently.**

| Protocol | Worst null FPR | Diagnosis |
|---|---|---|
| `naive` | **0.867** | Fit, select and test on the same data with IID inference. Catastrophic on 4 of 5 worlds |
| `cluster` | **0.200** | Correct inference, in-sample selection. **Cluster-robust inference alone does not fix selection bias** |
| `kairos` | 0.067 | Sealed holdout + cluster-robust inference |

This is AXIOMS C3, C5 and C6 measured against our own code rather than cited from papers. The
`naive` row is the empirical cost of the discipline the rest of the repo exists to enforce.

**4. Power collapses fast as the edge shrinks.** 0.667 → 0.333 → 0.067 across the signal ladder,
with the oracle collapsing alongside it (0.767 → 0.300 → 0.133). A realistic edge is *weaker* than
the strong control, so this is the operative constraint on Stage 0, not a footnote.

---

## Limitations — stated because the result is favourable

- **30 replications is coarse.** At n=30 the FPR gate only fires at 6+ rejections (20%), so it
  would not catch a modestly inflated rate. Tightening this needs more replications, not a
  different threshold.
- **`signal_moderate` shows kairos (0.333) above its oracle (0.300).** A forecaster cannot beat an
  unbeatable one; this is sampling noise at n=30 (SE ≈ 0.084) and should not be read as anything
  else. It is also a reminder of how coarse these rates are.
- **Synthetic worlds are not markets.** They test the *statistical machinery* for adaptive
  overfitting and clustering. They do not test venue microstructure, resolution risk, execution, or
  anything about real prices. Passing Gate 0 licenses proceeding to Gate 1 and nothing more.
- **The candidate search is a stand-in for an LLM loop.** It reproduces adaptive overfitting via
  fitted random feature subsets. A real LLM loop may search differently — and Gate 0 should be
  re-run once one is attached, before trusting its output.

---

## What it does not establish

It does **not** show that Kairos can find an edge, that an edge exists, or that any strategy is
viable. It shows only that the instrument reports "nothing" when there is nothing, and can see
something when it is there and large enough. That is a licence to begin measuring, not a result.

Next: `PROTOCOL.md` Gate 1 — the four-way `q_ref` ablation, on real resolved markets. **Done 2026-09-08; `q_ref` rejected.**
