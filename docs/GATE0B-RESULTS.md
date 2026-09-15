# Gate 0b — Results

**Verdict: test-only stratification is REJECTED. It does not clear the power floor and does not beat
the unstratified protocol on the one signal shape it was proposed for.** Run 2026-09-08.
Reproduce with `python gate0b.py --replications 16 --events 900 --bias 1.6`.

The multiplicity correction built alongside it (`inference.max_statistic_test`) **passed** and is
retained. What failed is the protocol, not the correction.

---

## Why this gate exists

Gates 1 and 2a each tested a single average over the whole sample and returned the same shape:
`+0.0134 / p=0.114` and `+0.0119 / p=0.117`. The obvious reading was "underpowered, get more events."
The literature suggests a different reading — that the market's error is not uniform, so an average
over the whole sample is the wrong estimand:

- Calibration is **not static**: it sits at reference values mid-life and departs sharply near expiry
  (Moshrefi 2026, 23M Kalshi trades).
- Models "failed to beat the market in the headline contract but some did so convincingly in
  contracts referencing **less visible** races" (Sethi & Kline 2025).
- Hybrid beat the market **particularly where the two disagreed by ≥5%** (Gruen et al. 2023).

Testing inside strata is therefore a live candidate. It is also a **search**, so under A7 it needs
its own null-world pass before it may touch real data. Pre-registration is in
[`PROTOCOL.md`](PROTOCOL.md) Gate 0b, written before any stratified result was seen.

---

## Result 1 — the correction works

`max_statistic_test`: one shared cluster resample per replicate, every stratum recomputed on it,
studentised. Measured on synthetic clustered nulls with no effect in any stratum:

| strata searched | uncorrected FPR | max-t corrected FPR |
|---|---|---|
| 2 | 0.100 | 0.067 |
| 3 | 0.142 | 0.033 |
| 5 | **0.233** | **0.092** |

Nominal is 0.05; 120 trials, so the SE on a true 0.05 rate is ~0.020. The uncorrected 5-strata rate
of 0.233 matches `1 − 0.95⁵ = 0.226` almost exactly, which is what independent strata predict.

In the full harness, on **price bands** — genuinely correlated, not randomly assigned — the same
pattern holds and is if anything sharper:

| protocol | false-positive rate, null world |
|---|---|
| `strat_naive` (report the winning band's own p) | **0.188** |
| `strat_maxt` (corrected) | 0.062 |
| `kairos` (unstratified) | 0.000 |

**Reporting the band that worked rejects a true null nearly four times too often.** That is the
whole content of AXIOM C10, measured rather than asserted.

## Result 2 — but the protocol does not pay for itself

900 events × 4 contracts, `bias = +1.60` inside the band, 16 replications, α = 0.05.

| world | `kairos` | `strat_naive` | `strat_maxt` | ceiling |
|---|---|---|---|---|
| null (bias 0) | 0.000 | 0.188 | 0.062 | 0.000 |
| banded:mid | **0.312** | 0.688 | 0.188 | 0.812 |
| banded:lowmid | 0.125 | 0.312 | 0.000 | *0.062 — excluded* |
| banded:highmid | **0.375** | 1.000 | 0.250 | 1.000 |

In both worlds where the harness is valid, the corrected stratified search detects **less** than
simply not stratifying, and neither approaches the 0.50 power floor. `strat_naive`'s apparently
strong 0.688–1.000 is substantially the 0.188 inflation above, not detection.

**Test-only stratification is rejected.** No stratified result may be reported from real data.

---

## Finding — the same guard defect, three times in one session

Gate 0 established long ago that a power comparison is meaningless when the best obtainable forecast
is itself undetected: it measures the world, not the protocols. This gate reproduced that defect
twice more before it was caught, each time in a form the previous fix did not cover.

| # | Defect | How it surfaced | Fix |
|---|---|---|---|
| 1 | No ceiling guard at all | First run printed **"DEAD"** with ceilings of 0.19–0.38, all below the floor. The verdict was unearned | Guard added before the verdict |
| 2 | Guard used the **max** ceiling across worlds | `banded:lowmid` (ceiling 0.062, nothing detectable) hid behind `banded:highmid` (1.000) and still contributed its ordering | Guard applied **per world**; excluded worlds are named in the output |
| 3 | The control world did not contain its own hypothesis | The band was defined on `pi`, but every protocol only sees `market`. At `bias=1.6` a `pi=0.5` contract quotes at **0.83**, mixed with honest contracts worth 0.83 — a signal concentrated in a band nobody could condition on | Band defined on the **quoted price**; two tests added asserting `stratify_by_price(market)` alone separates biased from honest contracts |

Defect 3 is the instructive one. It was found by a check that *should have confirmed* the diagnosis
and instead refuted it: band-dummy features scored **0.375** against a smooth price tilt's **0.500**,
which cannot happen if the band is observable. A control that does not contain the hypothesis it
names cannot falsify it, and it will fail quietly — every number it produces looks plausible.

The first version of `test_the_signal_really_is_concentrated_not_diffuse` passed throughout. It
checked *how much* of the range was mispriced and never that the mispricing was **visible**.

---

## What this does and does not settle

**Settled.** Test-only stratification — cutting the final test into pre-registered price bands while
fitting and selecting globally — costs more power than it buys, on both a diffuse signal
(`inject_signal`, Gate 0: 0.250 vs 0.667) and a concentrated one (this gate). Rejected.

**Not settled.** A **fit-level** stratified protocol, where candidates are fitted and selected within
strata rather than only tested within them, is untested. The candidate handed to the stratified test
here was chosen to be good *on average*, which against a banded signal means chosen to capture
nothing — so this gate falsifies the cheap version and leaves the expensive one open.

**Deliberately not built.** The fit-level version is a larger protocol with its own multiplicity
structure and would need its own Gate 0b. Under C9 and E1 it does not get built until something
cheaper has demonstrated the concentrated-edge hypothesis is worth that much machinery.

**Retained regardless.** `max_statistic_test` is validated and stays. Any future protocol that
searches over strata — price, horizon, disagreement, visibility — now has a correction whose
false-positive behaviour has been measured on correlated strata rather than assumed.
