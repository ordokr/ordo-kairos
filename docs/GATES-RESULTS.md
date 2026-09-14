# Gate S — Subsidy persistence: required horizon against observed stability

Run 2026-09-14 · `python gates.py --pages 20` · registration in [`PROTOCOL.md`](PROTOCOL.md) Class S,
written before the runner existed and before any cadence, direction or hazard figure was computed.

> **VERDICT: NO VERDICT on persistence** — the pre-committed outcome, reached for the pre-committed
> reason. **1** succession pair could be established against a registered minimum of **2**.
> One revision is not a cadence.
>
> **The one thing the gate did establish, recorded but not a verdict:** the single observed revision
> held the maker's take **exactly flat** while the taker fee rose 67%.

---

## 1. Null gate — 6 of 6

| world | kind | result | |
|---|---|---:|---|
| `no_structure` | FPR | 0/200 | PASS |
| `interleaved` | FPR | 0/200 | PASS |
| `reversed_versions` | FPR | 0/200 | PASS |
| `separated` | POWER | 200/200 | PASS |
| `churn_is_unstable` | POWER | 200/200 | PASS |
| `flat_reads_stable` | FPR | 0/200 | PASS |

`reversed_versions` is the G14 probe: it assigns version numbers in **reverse** temporal order,
negating the detector's own premise that a higher suffix means a later cohort. It fires zero times.

**The exhibit, on identical data:** a churning programme reads `direction -0.000000` — "no change" —
and `instability 50.0%`. That is why direction and instability are two statistics. A signed mean of
revision deltas averages churn to zero and calls it stability, and a single-statistic version of this
gate would have done exactly that.

The detector is deliberately conservative: it requires AUC ≥ 0.90 **and** a permutation rejection.
0/200 across all three FPR worlds reflects that double hurdle, not a tuned threshold — the floor was
fixed at 0.90 before the real cohorts were built.

## 2. The cohorts — 3,564 fee-enabled markets, 12 live schedules

| schedule | n | M2-eligible | exp | take | newest | oldest |
|---|---:|---:|---:|---:|---:|---:|
| `crypto_15_min` | 1 | 1 | **2** | 0.0500 | 6.7mo | 6.7mo |
| `crypto_fees_v2` | 368 | 111 | 1 | 0.0140 | 0.0mo | 13.3mo |
| `culture_fees` | 104 | 17 | 1 | 0.0125 | 0.1mo | 11.0mo |
| `economics_fees` | 90 | 22 | 1 | 0.0125 | 0.4mo | 11.7mo |
| `finance_prices_fees` | 182 | 68 | 1 | 0.0100 | 0.0mo | 11.7mo |
| `general_fees` | 3 | 0 | 1 | 0.0125 | 5.6mo | 10.3mo |
| `mentions_fees` | 4 | 1 | 1 | 0.0100 | 0.0mo | 0.2mo |
| `politics_fees` | 516 | 72 | 1 | 0.0100 | 0.2mo | **14.4mo** |
| `sports_fees_v2` | 470 | 36 | 1 | **0.0075** | **2.2mo** | 11.7mo |
| `sports_fees_v3` | 1,597 | 432 | 1 | **0.0075** | 0.0mo | **2.1mo** |
| `tech_fees` | 82 | 22 | 1 | 0.0100 | 0.2mo | 10.6mo |
| `weather_fees` | 147 | 26 | 1 | 0.0125 | 0.0mo | 10.1mo |

**`crypto_15_min` runs at `exponent: 2`** — its fee is `rate × (p(1−p))²`. Its "take" of 0.0500 is
therefore **not on the same scale** as any other row and must never be compared with them. This was a
live defect in the first version of the estimator; see [Pass 34.2](CORRECTIONS.md).

## 3. The one succession, and what it did

**`sports_fees_v2 → v3`: AUC 1.0000, permutation p = 0.0025.** Perfect separation — *every* v3 market
was created after *every* v2 market. The boundary is sharp: v2's newest market is 2.2 months old and
v3's oldest is 2.1 months old, bracketing the revision to roughly **three days, about 2.1 months ago**.

| | taker fee | rebate | **maker's take** |
|---|---:|---:|---:|
| `sports_fees_v2` | 0.03 | 25% | **0.0075** |
| `sports_fees_v3` | 0.05 | 15% | **0.0075** |
| change | **+67%** | −40% | **0.0000** |

The venue raised the taker fee by two thirds, cut the rebate share by two fifths, and the maker's
per-contract rebate came out **identical to four decimal places**. Weighted direction `+0.000000`,
weighted instability `0.00%`.

This was **declared in the registration before the run**, precisely so that confirming it would
confirm a pre-registration rather than announce a discovery (AXIOMS G14). What the run added is that
the pair is a genuine temporal succession rather than two coexisting variants — the confound the
registration named as the thing that would void the measurement.

**It is one observation.** It is consistent with a venue that reprices takers and protects makers. It
is equally consistent with coincidence, and with one decision that will not be repeated. The
registered rule does not let a single event become a cadence, and it should not.

## 4. The hazard bound — the dominant term

Zero withdrawals have been observed, so the hazard can only be **bounded** (rule of three: 95% upper
bound `3/n` on the per-unit probability given zero events in `n` units).

| counting | n | monthly bound | **annual bound** |
|---|---:|---:|---:|
| **Programme-months** (one decision withdraws everything) | 14.4 | ≤ 21.4% | **≤ 94.5%** |
| Schedule-months (assumes 12 independent programmes) | 113.7 | ≤ 2.7% | ≤ 27.6% |

**The programme-level count governs**, and the registration was wrong to specify schedule-months
([Pass 34.4](CORRECTIONS.md)). Summing across schedules treats twelve consequences of a *single*
business decision as twelve independent trials, and it makes the bound look 3.4x tighter than the
evidence supports.

**≤ 94.5% annually is very close to no constraint at all.** The registered rule says that where the
bound admits near-certain withdrawal it is "reported as the dominant term whatever else the gate
finds", and it is: the data cannot rule out that the subsidy disappears within the year.

## 5. Payback

Gate M2's net of $139,450/yr is $11,621/month, with the 6% capital hurdle already charged.

| build | cost @ $12,000/person-month | payback | vs 14.4mo observed span |
|---:|---:|---:|---|
| 0 | $0 | 0.0mo | clears |
| 1mo | $12,000 | 1.0mo | clears |
| 3mo | $36,000 | 3.1mo | clears |
| 6mo | $72,000 | 6.2mo | clears |

Every rung clears, which sounds like good news and is mostly an artefact: **the registered `REFUTED`
condition — "payback exceeds observed stability at every build cost including zero" — is vacuous**,
because payback at zero build cost is zero months and can never exceed anything. Recorded rather than
quietly repaired ([Pass 34.5](CORRECTIONS.md)). The gate's discriminating power sits entirely in the
pair-count test and the direction test, not here.

## 6. Why the apparatus cannot answer the question

Three limits, all of which point the same way:

1. **The API exposes each market's *current* `feeType`**, never the history of schedule assignment.
   A schedule's "age" is inferred from the creation dates of markets now carrying it — which is only
   the same thing if assignment happens at creation and nothing is ever reassigned.
2. **`open_universe` returns open markets only.** Every cohort is truncated by resolution, and an
   entire earlier version can be invisible. `crypto_fees_v2` implies a `v1` that does not appear
   anywhere in 3,564 markets — almost certainly because its markets have all resolved.
3. **Zero observed withdrawals.** There is no event to fit, only an absence to bound.

None of this is fixable by measuring harder from here. It would take an archive of historical
schedule assignments, which is a different apparatus and a different registration.

## 7. What this does not cover

- **The venue's finances, budget and intentions.** Unobservable, and the dominant term.
- **Withdrawal without warning.** A single decision has no cadence.
- **Regulatory change** to either programme.
- **Competitive response**, which compresses the spread even while the rebate holds.
- **F3 stands.** Nothing traded, quoted, or touched capital.

## 8. What this means for Class M2

Unchanged, and that is the point. Gate M2 stands as measured: **NOT REFUTED, subsidy-dependent, never
an edge.** Gate S was asked whether the subsidy will last and has answered **that it cannot tell** —
while bounding the annual withdrawal hazard at ≤94.5%, which is to say barely bounding it.

A NO VERDICT is not a pass. Proceeding as though Class M2 had cleared a persistence test would be
exactly the drift this protocol exists to prevent.
