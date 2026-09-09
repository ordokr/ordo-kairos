# Look 3 — Results

**Verdict: NEITHER hypothesis replicated. The Class A forecasting edge is REJECTED at this venue and
scale.** Run 2026-09-08 on **1,966 fresh events**, none of which had ever been tested.
Reproduce with `ORDO_KAIROS_STATE=<durable> python replicate.py --windowed`.

This is the first adequately powered, fully pre-registered test this project has run: 983
out-of-sample events against look #1's 366.

---

## Result

| hypothesis | log score | vs market | p | materiality | look #1 |
|---|---|---|---|---|---|
| market | 0.37573 | — | — | — | benchmark |
| `C_logit` | 0.37202 | +0.00371 | **0.0335** | **0.987%** | +0.01341 |
| `drift` | 0.37624 | −0.00051 | 0.7056 | −0.136% | +0.01193 |

Registered thresholds: `alpha = 0.025` (Bonferroni over two tests), materiality floor **1.00%** of
the benchmark.

**`C_logit` failed both, and failed both narrowly.** `p = 0.0335` sits below the conventional 0.05
and above the registered 0.025; the gain is **0.987%** of the benchmark against a 1.000% floor. Miss
either guard and this run reports a finding.

That is the entire argument for pre-registration, and it is worth stating plainly: had the alpha
split and the materiality floor been chosen *after* seeing `p = 0.0335`, there would have been an
easy, sincere-sounding case for both — two tests are "really one family", 0.987% "rounds to 1%".
Both numbers were frozen in `PROTOCOL.md` before this data was fetched, and the reason each exists
predates this run by two gates. The floor was added after Gate 1's `B_settle` won at `p = 0.0005` on
0.024% of the benchmark; the alpha split was added because carrying two look-#1 near-misses forward
doubles the error rate.

## The magnitude behaved exactly as pre-committed

The registration recorded, before the data existed, that look #1's `+0.012` to `+0.013` was the
**maximum of 5 baselines and of 4 forecasters** measured at low power, that selected estimates under
those conditions are substantially inflated, and that **a smaller effect on replication would be
evidence about magnitude rather than a failure of method**.

| hypothesis | look #1 | Look 3 | change |
|---|---|---|---|
| `C_logit` | +0.01341 | +0.00371 | **−72%** |
| `drift` | +0.01193 | −0.00051 | **sign reversal** |

Look #1's two near-misses were a 72% overestimate and a sign error. Both are textbook outcomes for a
best-of-*k* selected at `p ≈ 0.11`, and both were predicted in writing beforehand rather than
explained afterwards.

Look #2's numbers on 115 events — `C_logit +0.02468`, `drift +0.05338` — were *larger still*, and
were recorded at the time as "not encouraging and must not be described as such". At 1,966 events
`drift` is negative. That is what 115 events buys.

## Sample

| | |
|---|---|
| Fresh events | **1,966** (registered target 1,500) |
| Excluded as already seen | 846 — look #1's 731 and look #2's 115 |
| Development / sealed | 1,474 / 492 events |
| Out-of-sample tested | **1,602 rows in 983 events** |
| Windows swept | 6 quarters, 2024-10 → 2027-01, newest-first |
| Markets scanned | ~12,600 (12,665 price histories cached) |

The sweep stopped when the registered event count was met, not when a p-value moved. Windows were
taken in date order, so which quarters entered the sample cannot depend on anything measured in them.

**The sealed holdout was not queried.** Neither hypothesis cleared development, and spending the one
permitted query on a hypothesis that had already failed would burn it for nothing (C6). 492 events
remain sealed for a future, differently-designed run.

---

## Coverage gaps — stated, not hidden

Three quarters could not be retrieved: **2025-07-01 → 2026-04-01**, HTTP 500 at every offset
attempted. Two of them (`2025-10`, `2026-01`) are permanently broken upstream — verified 500 at
offsets 0, 500, 1000 and 2000. The third (`2025-07`) serves deeper pages normally but 500s at
offsets 0, 100 and 200, so the sweep's three-consecutive-failure cap gave up on it; that quarter is
recoverable by raising `MAX_CONSECUTIVE_WINDOW_FAILURES` and was deliberately **not** chased
mid-run.

**The sample therefore has a nine-month hole in calendar time.** It is a limitation of coverage, not
a selection effect — the gap is defined by an upstream fault, which cannot correlate with whether a
recalibration beats the market — but it is recorded because an unstated hole in a sample is
indistinguishable from one nobody noticed.

This gap was very nearly invisible. An earlier probe returned `[]` on any error, so those three
quarters showed up as "0 markets" and were read as *"no markets resolved then"*. `fetch_window` now
returns failed offsets alongside markets, and the sweep prints them, precisely so a broken window
cannot masquerade as an empty one.

---

## What this settles, and what it does not

**Settled.** Neither logit-space recalibration of the market price nor the `drift_per_day` price-path
forecaster adds information beyond the raw Polymarket quote, on 983 independent out-of-sample events
at a 24-hour decision lead. Per the registration: `q_ref` is dead as a forward hypothesis and no
further model work is done on Polymarket resolved markets.

**Not settled, and out of scope by construction.**

- Other decision leads. Every gate ran at 24 hours; the horizon was never varied, and Page et al.
  and Moshrefi both report the market's calibration is a function of time to expiry. This is a
  registered separate experiment, deliberately not folded in.
- Other venues. Kalshi has a different fee structure and a different participant mix.
- Class B (structural/arbitrage). Untouched by this result — it is a different hypothesis about a
  different object.
- The nine-month gap above.

**What it does not license** is the reading that markets are efficient. This tested two specific,
cheap, price-only transformations. It is a rejection of *these hypotheses at this scale*, which is
the only thing a null result ever is.

---

## Registration compliance

| Registered | Honoured |
|---|---|
| Test only events look #1 never saw | Look #1's 731 rebuilt and **verified exactly** before use; run would have voided on mismatch |
| Exclude look #2's spent events | 115 excluded; 846 total |
| Two named hypotheses only | `C_logit`, `drift`. No other model tested |
| Same lead as look #1 | 24 h |
| `alpha = 0.025`, materiality 1% | Applied; `C_logit` failed both by <0.02pp |
| Sweep windows newest-first to 1,500 events, then stop | Stopped at 1,966 on the window that crossed it |
| Sealed holdout queried once | Not queried — nothing earned it |

One thing the registration did not anticipate: it commits to **deleting `baseline.py`** on this
outcome. `gate1.py` imports from it and `replicate.py` imports `_fit_logit` from `gate1`, so deleting
it makes Looks 1–3 unreproducible from a clean checkout — and this workspace is not a git repository,
so the deletion is irreversible. That conflict is flagged rather than resolved unilaterally.
