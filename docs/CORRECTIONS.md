# Ordo Kairos — Corrections Log

Append-only record of claims this project made and then had to withdraw, plus the status of every
outstanding corrective instruction. Its purpose is anti-drift: a refuted claim recorded here must
not be silently re-asserted by a later session or agent.

Newest pass at the top.

---

## Pass 41 — The evidence was never destroyed, only orphaned; Pass 40 misdiagnosed its own loss (2026-09-15)

**Pass 40 is withdrawn in its central claim.** It recorded that squashing "destroyed" the
pre-registration proof and that the repository faced a choice between a clean history and verifiable
evidence. Both were wrong, and wrong in the way this log exists to catch: the diagnosis named the
wrong cause and then reasoned correctly from it.

### 41.1 The squash removed reachability from one ref, not the objects

The 21 commits and both proofs were intact in the object store the entire time. What the squash
changed was which ref reached them. **Reachability from `main` is an accident of a commit object,
not its substance** (`foundations.md` §I). Pass 40 treated an accident as the substance and wrote a
eulogy for evidence that was sitting on disk.

The fix is one tag. `provenance/pre-squash` points at `a65de17`, is fetched by a default
`git clone`, and restores the ratio to **2 of 8** for any reader:

| gate | registration | runner |
|---|---|---|
| Class S | `5169570d` | `a5cfb1f5` |
| Class C | `cddb6a14` | `6b4348b8` |

`main` remains a single squashed commit. Both goals hold at once.

### 41.2 The tradeoff in the brief was fictional and nearly got priced

The problem arrived stated as a tradeoff — clean history *or* verifiable evidence — and every
candidate remedy inherited it: restore the history and lose the flat `main`, or keep `main` and
accept an unverifiable claim. **When every candidate shares an assumption, the assumption is the
principal cause.** Negating it ("evidence must live on `main`") dissolved the problem rather than
splitting it. A stated tradeoff is a claim about the option space and deserves the same falsification
as a claim about a number.

### 41.3 AXIOMS C9a is satisfied by preservation, and was right not to be amended

Pass 40.2 declined to amend C9a to excuse the erasure, on the grounds that rewriting a rule to permit
a violation converts a breach into retroactive permission. That call is now vindicated from the other
side: the axiom did not need an exemption because **nothing had to be erased**. An axiom that looks
like it needs weakening is usually reporting a misdiagnosis upstream of it.

### 41.4 What the guard now checks

The ratio falsifier reads `provenance/pre-squash`, not `HEAD` — reading `HEAD` on a squashed `main`
silently reports zero, which is the exact failure this pass prevents. It fails if the ref goes
missing, if the ref is moved to a single-commit history, or if the ratio moves in either direction.
`TestPass41ProvenanceLivesOnARefNotOnMain` guards the ref, the read site, and the README's
reproduction command.

### 41.5 The correction that generalises

Pass 40 is the 40th entry and the first about something other than a number. Pass 41 puts it back in
the family: **the defect was again in the words around the measurement, not in the measurement.**
"Destroyed" was the wrong word for "unreachable," and the wrong word cost a real claim for a day.

---

## Pass 40 — The history was squashed, deleting this project's only pre-registration evidence (2026-09-15)

> **Withdrawn in its central claim by [Pass 41](#pass-41--the-evidence-was-never-destroyed-only-orphaned-pass-40-misdiagnosed-its-own-loss-2026-09-15).** The evidence was orphaned, not destroyed, and
> is now preserved on the `provenance/pre-squash` tag. 40.2 (do not amend the axiom) and 40.3 (the
> falsifier must be an equality) stand. The entry is kept unedited below, per the append-only rule.

**The first entry in this log that is not about a number.** It is recorded here anyway, because this
log exists to stop a withdrawn claim being silently re-asserted, and an unrecorded erasure is exactly
the drift it was built to catch.

### 40.1 Twenty-one commits were squashed to one and force-pushed to a public `main`

After publication, at the maintainer's direction, the development history was flattened to a single
root commit. The pre-squash tip was `a65de17`.

What that cost, precisely: **Pass 39 recorded that 2 of 8 gates — Class C and Class S — carried a
registration commit landing before the commit that added their runner.** Those two were the only
independently verifiable evidence that anything in this repository was pre-registered rather than
back-filled to match its result. Squashing put registration and runner in the same commit for every
gate. The provable ratio is now **0 of 8**.

The claim itself is unchanged and still true as a fact about how the work was done. It is now
unverifiable from the artifact for **all** gates rather than six of eight. A repository whose entire
value rests on pre-registration deleted its own proof of pre-registration.

### 40.2 This breaks AXIOMS C9a, and the axiom is not being amended to excuse it

> **C9a.** […] Erasure is only correct where the artifact is *itself* the hazard (a secret, a live
> credential), never where it is merely refuted.

The history was not a hazard. It had been scanned for credentials, keys, and personal identifiers
before publication and was clean. It was erased for presentation. C9a does not permit that.

The axiom stands as written. Amending it to carve out an exemption would convert a recorded
violation into a retroactive permission, which is the precise move this log exists to prevent. The
correct response to breaking your own rule is to record that you broke it.

### 40.3 The falsifier that covered this claim lost its teeth, and has been re-sharpened

`TestRegistrationPrecedesImplementation` asserted `provable >= PROVABLE`. With `PROVABLE` now `0`
that assertion cannot fail for any input — an unfalsifiable test sitting in the suite whose entire
subject is falsifiability. Changed to an **equality**: if a future gate lands its registration in
its own commit, `provable` becomes 1, the test fails, and `PROVABLE` and the README must both be
updated to earn it. Guarded by `TestPass40TheSquashIsRecordedNotHidden`.

### 40.4 Recoverable at time of writing

The pre-squash tip `a65de17` and its ancestors survived in the local object store and reflog when
this entry was written. Until git prunes unreachable objects, the history — and with it the Class C
and Class S proofs — can be restored by force-pushing that commit back. This note exists so that a
later reader knows the loss was recoverable for a window, and whether that window was used.

---

## Pass 39 — The pre-registration claim is true and mostly unprovable (2026-09-14)

The README was rewritten as the project's public face and then, for the first time, **falsified
against itself** (`tests/test_readme_claims.py`). One claim failed.

### 39.1 Six of eight gates committed their registration and their runner together

The README asserts every gate was registered before it was built. Checked against git:

| gate | registration commit precedes runner? |
|---|---|
| Class C, Class S | **yes** — separate commits |
| Class M2, F, R, K, SM, N | **no** — same commit |

The claim is **true as a fact about how the work was done** and **not verifiable from the artifact
for six of eight gates.** A reader cannot distinguish "registered first" from "back-filled to match
the result," and that is precisely the distinction the whole repository is built to enforce. The
single claim carrying all the credibility is the one the history cannot support.

This is the same failure class as every other pass, applied to the project rather than a gate: the
arithmetic was right, and the sentence around it promised more than the evidence carried.

Fixed three ways rather than by softening the sentence:

1. The README **discloses the 2-of-8 ratio** in its own "why believe any of it" section.
2. A falsifier measures the ratio and **fails if it gets worse**, which is the only honest way to
   hold a claim history cannot prove.
3. Future gates land their registration in **its own commit** before the runner exists.

**What does survive independently:** the pre-committed expectations. Gates K.0 and SM.0 both recorded
predictions that turned out directionally wrong, and Class S's registration contains four defects its
own run exposed. A back-filled registration does not predict its own failures.

### 39.2 The front page was the only ungated document in the repository

Every number here had to survive a registration, a null world and a decision rule. The README
asserted eleven results, six counts and a methodological virtue on nothing but the author's word —
and it is the document most people will read and the only one most will read.

`tests/test_readme_claims.py` now checks each count against the tree, each headline figure against a
results document, the "never traded" promise against every source file (no POST, no signing, no
credentials, no `data=` on a Request), the zero-dependency claim by AST, and the pre-registration
claim against git history. It caught a real inconsistency on its first run: `LICENSE` had been added
while the README still read "not yet declared."

### 39.3 A test that runs the test suite is not a test

The first version of the test-count falsifier shelled out to `unittest discover`, which rediscovers
the file containing it and re-runs the suite inside itself. Unbounded recursion; it hung for ten
minutes before being killed. Replaced with a static AST count of test methods.

Recorded because it is a small, pure instance of the recurring lesson: the arithmetic (counting
tests) was never in question, and the defect was entirely in how the count was obtained.

### 39.4 Licence

Apache-2.0, matching the plurality of licensed repositories in this org and the flagship public one.
There is **no single house licence** — of 66 repositories, 36 declare none, 12 are Apache-2.0, 10
MIT, 7 custom and 1 GPL-3.0 — so "the same licence as everything else" was a premise that did not
survive checking either.

---

## Pass 38 — Gate N.0 run; two flooring helpers reused where the floor was the wrong answer (2026-09-14)

Class N registered and run. Result in [`GATEN-RESULTS.md`](GATEN-RESULTS.md). **REFUTED ON
CAPACITY** — markets under 24h old carry **0.11%** of flow against a registered floor of 5%.

### 38.1 A volume-ordered sampling frame cannot reach a population defined by newness

The first run **WITHHELD at 173 young markets** against a floor of 200, having swept 3,996 — near the
pagination ceiling. `gatem.open_universe` orders by **volume**, and a market listed an hour ago has
had no time to accumulate any, so the frame systematically under-samples exactly the population the
class is about.

The gamma API supports `order=createdAt`, verified before the amendment was written. The frame became
the **union of the volume sweep and an age sweep from both ends**, deduplicated — 5,224 classified
markets, of which 2,139 young.

Recorded as Class N Amendment 1 **before the measuring run**, not after seeing a result, and it
altered no threshold, statistic, bucket boundary or decision rule. A floor on sample size is an
instruction to obtain more of the right sample, never to lower the floor.

### 38.2 `age_hours` floors at zero, so every future deadline collapsed to `-0h`

The registration required the age/time-to-resolution confound to be **reported**. The first measuring
run reported a column of `-0h` for every bucket, because time-to-resolution was computed as
`-age_hours(endDate)` and `age_hours` returns `max(0.0, ...)`. A date in the future therefore floors
to zero and negates to `-0.0`.

The correlation printed alongside it (`-0.212`) was computed on the only rows with non-zero values —
markets whose end date had already **passed**. It was meaningless.

**This is the second flooring helper in this gate reused where the floor is wrong.** The first was
caught in advance: `gatem.days_since` floors at `max(1.0, ...)` days and would have collapsed the
entire youngest bucket into "1 day", which the registration named as an apparatus fact before the
runner existed. The same class of defect, one caught by reading and one only by reading the output.

Fixed with `signed_hours_until`, unfloored and signed. The corrected confound is **+0.331** across
5,100 markets: young markets resolve in 25 hours, mature ones in 2,595.

### 38.3 A diagnostic subsample took the first N rows, which were all from one bucket

Queue depth was sampled as "the first 120 rows with a quote", and the union frame lists the volume
sweep first — so all 120 came from `>30d` and the two young buckets printed "no books sampled". A
comparison with nothing in one arm.

Fixed to sample **per bucket**. The corrected figures are the sharpest in the result: median touch
size **75** (<6h) and **36** (6–24h) against **6,284** (>30d).

### 38.4 The pre-committed expectation was right, for the first time in four gates

Registered: young markets will be wider and emptier — "close to mechanical, and not the interesting
half" — and will carry too little flow, so the gate refutes on capacity. Both held: 16x wider, 93.7%
with no book, 0.11% of flow.

Gates K.0 and SM.0 both had directionally wrong expectations, as did this gate's spread half in the
sense that its interval straddled. Recording expectations has been useful mainly when they were
wrong; this is the case where it confirms the reasoning rather than correcting it.

### 38.5 The finding worth carrying forward

**A mechanism is not an opportunity.** Nine prior classes failed because the economics were thin or
the counterparty was informed. This one failed with **every structural precondition true** — wider,
emptier, thinner-queued, all in the predicted direction and by large margins — and no flow to trade
against. The wide window is real and it closes before anyone arrives.

---

## Pass 37 — Gate SM.0 run; a confound registered in advance prevented a four-fold false positive (2026-09-14)

Class SM registered and run. Result in [`GATESM-RESULTS.md`](GATESM-RESULTS.md). **NO VERDICT** —
flow-weighted median half-spread **0.00630** against a comparator of 0.00500, with the share of flow
above the comparator at **62.4%, 95% CI [43.3%, 86.7%]**, straddling 50%.

### 37.1 Reusing the previous gate's statistic would have manufactured the best number in the repository

Gate K.0's statistic is *share of flow whose spread exceeds one tick*. Smarkets ladders in **decimal
odds**, giving a probability-space tick of ~0.005–0.008 against the flat cent used by Polymarket and
Kalshi. On that statistic:

| venue | tick | Gate K.0 statistic |
|---|---:|---:|
| Polymarket | 0.0100 | 22.6% |
| Kalshi | 0.0100 | 26.6% |
| **Smarkets** | **~0.005–0.008** | **100.0%** |

**Every eligible Smarkets market clears "more than one tick" because the tick is half the size.** A
four-fold apparent improvement, entirely artefactual, and it would have been the most exciting figure
this project has produced.

The confound was named in the registration *before the run*, and the primary was moved onto the
half-spread in **probability units**, which is comparable across all three venues. This is the first
pass in this log where a defect was **prevented by the registration rather than caught after the
fact** — the ladder was measured during apparatus probing, the consequence was reasoned through, and
the statistic was chosen accordingly.

### 37.2 A guessed field shape produced zero eligible markets, and the gate correctly refused

The first run reported **0 eligible against a floor of 200** and WITHHELD. Cause: the contract →
market mapping was built from `market["contract_selections"]`, which is **null** on Smarkets market
objects. The mapping lives on `/v3/markets/{ids}/contracts/` as `{id, market_id}`.

I guessed a field shape instead of verifying it, which is the same class of error as Pass 33.2's
transcribed rate table. **What worked is that the gate refused**: with no volume resolvable, every
market failed the flow precondition and the runner reported an apparatus failure rather than a
measurement of zero (AXIOMS G5). A runner that defaulted missing volume to "include anyway" would
have reported an unweighted result and called it flow-weighted.

### 37.3 The implemented test is equivalent to the registered one, recorded so it is not read as drift

The registration specified an interval on the **flow-weighted median** against 0.005. The runner
intervals the **share of flow above 0.005** against 50%.

These are the same test: a weighted median exceeds `x` exactly when the weighted share above `x`
exceeds 50%. The share formulation bootstraps more stably than a quantile and reuses
`weighted_share_ci` from Pass 36. Recorded because an equivalent-but-different-looking statistic is
indistinguishable from a substituted one unless the equivalence is stated.

### 37.4 The pre-committed expectation was wrong again, in the same harmless direction

Registered: half-spread at or below 0.005, therefore refutation. Measured: 0.00630, with an interval
too wide to establish it. Second gate running where the expectation was directionally wrong and the
verdict was NO VERDICT. The expectations are not improving; the machinery that makes their wrongness
legible is working.

---

## Pass 36 — Gate K.0 run; a registered rule that compared two bare point estimates (2026-09-14)

Class K registered and run. Result in [`GATEK-RESULTS.md`](GATEK-RESULTS.md). **NO VERDICT** —
Kalshi's flow with room to quote is **26.6%, 95% CI [18.4%, 39.1%]**, against Polymarket's **22.6%**.

### 36.1 The registered decision rule had no interval on either side of its comparison

Class K's rule read: *"Flow share with tick room ≤ 22.6% → REFUTED; > 22.6% → NOT REFUTED."* A bare
threshold on a bare point estimate, with no uncertainty on the measurement and none on the
comparator.

Run as registered it returns **NOT REFUTED at 26.6%**. With a bootstrap interval it returns **NO
VERDICT**, because [18.4%, 39.1%] contains 22.6% and a 4-point gap inside a 20.7-point-wide interval
distinguishes nothing.

**This is Pass 29 repeating.** Gate M's null gate failed on exactly this: medians right, single
replications wrong 20–47% of the time, fixed by adding intervals and a third verdict state. The
lesson was recorded, and Class K's registration was still written without one. Recording a
correction does not immunise the next registration against the same mistake — only a guard does, and
the guard added then was specific to Gate M's estimator.

Fixed by adding `kairos.inference.weighted_share_ci` (i.i.d. percentile bootstrap over **markets**,
the independent unit — distinct from `microstructure.bootstrap_ci`, which blocks a time series) and
routing the verdict through the three-state discipline.

### 36.2 A test asserted a property the statistic should not have, and the statistic was right

The first version of `test_weight_decides_the_share_not_the_count` asserted that with one market
carrying 91% of the weight the interval's **lower** bound must exceed 0.5. It came back **0.0** and
the test failed.

The implementation was correct. A bootstrap resample of 100 units omits any given unit in
`(99/100)^100 ≈ 37%` of draws, so a share resting on a single market genuinely is near-unestimable,
and a narrow interval there would have been a lie of precision. The **assertion about what the
statistic should say** was wrong — which is Pass 28.2's finding one more time: the arithmetic was
right and the sentence about it was not.

The test now encodes the true property: **concentration of weight widens the interval**, and that is
exactly why Gate K.0's own interval is 20.7 points wide.

### 36.3 The second venue cannot answer the question that made the first one interesting

Kalshi's market API exposes **no fee, maker, taker, rebate or reward field whatsoever**, and
`kairos/kalshi.py` has carried the published schedule as unverified since 2026-09-09. Gate M2's
entire economics — `rebateRate × feeRate × p(1-p)`, 77% of the gross — has **no measurable
counterpart** on Kalshi from public data.

Declared in the registration before the run, so the gate was scoped to the spread alone rather than
quietly shrinking once the fields turned out to be missing.

### 36.4 The pre-committed expectation was directionally wrong, and recording it is why that is visible

The registration predicted Kalshi would look **worse** (a 1c tick on a $1 contract is coarse) and
that the gate would **refute**. The point estimate went the other way. Had no expectation been
registered, +4 points could have been narrated as encouraging rather than as noise inside an
interval. The expectation was wrong; the machinery that made the wrongness legible worked.

---

## Pass 35 — Gate S's payback table held size at one value, and it hid the answer (2026-09-14)

### 35.1 A C11 violation inside the analysis whose registration demanded a curve

Class S registered build cost as "**a curve, not a point**: 0 / 1 / 3 / 6 person-months. A design
variable is not held at one value." The runner obeyed that for build cost and then **held posted size
fixed at 2,000 contracts** — the largest rung of Gate M2's own size curve, requiring **$390,000** of
capital. Size is a design variable too, and C11 does not stop applying because the registration
happened to name only one of them.

Restoring it changes what the gate says to anyone without $390,000:

| size | capital | net/yr | ROC | 1mo build | 3mo build | 6mo build |
|---:|---:|---:|---:|---:|---:|---:|
| 25 | $4,875 | $2,024 | 41.5% | **71mo** | **213mo** | **427mo** |
| 100 | $19,500 | $8,096 | 41.5% | **18mo** | **53mo** | **107mo** |
| 500 | $97,500 | $40,257 | 41.3% | 3.6mo | 10.7mo | **21mo** |
| 2,000 | $390,000 | $139,450 | 35.8% | 1.0mo | 3.1mo | 6.2mo |

**Bold exceeds the 14.4-month observed life of the entire fee programme.** At $19,500 of capital, one
person-month of build takes **17.8 months** to repay — longer than the subsidy has been observed to
exist at all. At $4,875 it takes **71 months**.

The single figure the first run reported — "payback 6.2 months, clears" — was true only at the top
rung, and it read as a general finding. It was not.

### 35.2 Return on capital is flat and then saturates, which the single row also hid

ROC holds at ~41.5% up to roughly $100k and falls to 35.8% at $390k: the last $292,500 of capital
earns **33.9%** marginal. Available taker flow beyond the queue is finite (Gate 3.0's fill model), so
capital stops buying fills proportionally. A one-row table cannot show a saturation curve.

### 35.3 What does not change

The verdict. Gate S still returns **NO VERDICT** on persistence for the registered reason — one
succession pair against a minimum of two. The payback table was never load-bearing for the verdict
([Pass 34.5](#): its `REFUTED` rung is vacuous), which is *why* the defect survived the first reading:
nothing downstream depended on it. It is decision-relevant to an operator regardless.

---

## Pass 34 — Gate S run; the runner disagreed with its own registration (2026-09-14)

Class S registered and run. Result in [`GATES-RESULTS.md`](GATES-RESULTS.md). **NO VERDICT on
persistence** — 1 succession pair against a registered minimum of 2 — with the annual withdrawal
hazard bounded only at **≤94.5%**.

### 34.1 The verdict branch tested for zero pairs where the registration said fewer than two

The registered rule reads: *"Version suffixes are not temporal succession, **or fewer than 2
succession pairs** → NO VERDICT."* The runner's first version tested `if not pairs:` — zero — and so
reported **NOT REFUTED** on a single pair. The registered answer is NO VERDICT.

Caught by reading the registration against the output before anything was recorded. The result would
have been a gate that passed itself on one observation, which is the precise failure the pair
minimum was written to prevent.

**This is Pass 33.5 again, one gate later**: the code did not implement the registered sentence.
The guard is now `len(pairs) < MIN_PAIRS` with `MIN_PAIRS = 2` named as a constant, and a regression
test asserts the runner contains the comparison rather than a truthiness check.

### 34.2 A live schedule uses a different price exponent, so its take was not comparable

`maker_take` strips the `(p(1-p))^exponent` factor and its docstring asserted that factor "is
identical across schedules". It is not: **`crypto_15_min` is live at `exponent: 2`**, where the fee
is `rate x (p(1-p))^2`. Its stripped product of `0.25 x 0.20 = 0.0500` is not a larger take than
`crypto_fees_v2`'s `0.0140` — it is a quantity in **different units**.

Nothing in this run's verdict depended on it (`crypto_15_min` has one market and one version), but a
future succession pair spanning an exponent change would have produced a meaningless delta with no
warning. Fixed with `take_pair`, which **refuses** a comparison across differing exponents and names
the exponent in the message so it is not mistaken for a data error.

### 34.3 The registered preconditions would have biased the measurement they were applied to

The registration set preconditions as "the Gate M2 universe: longshot band, tick room > 1,
`feesEnabled`". The band and tick-room filters are **tradeability** filters, and tradeability
correlates with recency — applying them to a *creation-date* cohort measurement selects on a variable
correlated with the thing being measured and would manufacture separation.

Amendment: only `feesEnabled` applies to the cohort measurement (S1). The Gate M2 universe is used
solely to **weight** the revision test (S2), which is what the registration wanted it for.

### 34.4 The registered hazard unit treated one decision as twelve independent trials

The registration specified rule-of-three on **schedule-months**. One decision withdraws every
schedule at once, so summing across twelve schedules counts twelve consequences of a single choice as
twelve independent observations.

| counting | n | annual bound |
|---|---:|---:|
| Programme-months (correct) | 14.4 | **≤ 94.5%** |
| Schedule-months (registered) | 113.7 | ≤ 27.6% |

The registered unit makes the bound look **3.4x tighter** than the evidence supports. Amendment: both
are reported and the **programme-level count governs**. Adding a charge that cuts against the
hypothesis is permitted; the reverse would not be.

### 34.5 One rung of the registered decision rule is vacuous by construction

The rule's `REFUTED` condition reads "required payback exceeds observed stability **at every build
cost including zero**". Payback at zero build cost is zero months and cannot exceed anything, so that
rung can never fire.

Recorded rather than repaired after seeing the result. The gate's discriminating power rests entirely
on the pair-count test and the direction test; the payback curve is descriptive, not decisive, and
Class S's registration should not have implied otherwise.

### 34.6 The universe is open markets only, so cohort history is truncated by resolution

`open_universe` returns open markets. Every cohort's oldest member is bounded by what has not yet
resolved, and an entire earlier schedule version can be invisible — `crypto_fees_v2` implies a `v1`
that appears nowhere in 3,564 markets, almost certainly because its markets have all resolved.

This is an apparatus ceiling, not a fact about the world (AXIOMS G12), and it reinforces the NO
VERDICT rather than arguing around it.

---

## Pass 33 — Gate M2 run; a fee coefficient that was wrong everywhere, in the safe direction (2026-09-14)

Class M2 registered and run. Result in [`GATEM2-RESULTS.md`](GATEM2-RESULTS.md). **NOT REFUTED:
net `$139,450`/yr at 2,000 posted contracts, carried by the maker rebate and not by the spread.**

### 33.1 Every Polymarket cost this project has ever computed was charged at the wrong rate

`CostModel.taker_fee_coeff` defaults to **0.07**, documented as "the shape of Kalshi's published
trading fee", and Gates B, C, D.0 and 4.0 charged every Polymarket cost at it. The live
`feeSchedule` on 1,445 markets across **11 distinct schedules** says the true rate is:

| rate | categories | overcharge at 0.07 |
|---|---|---|
| 0.07 | crypto | none — exact |
| 0.05 | sports v3, weather, culture, economics, general | 40% |
| 0.04 | politics, finance, tech, mentions | 75% |
| 0.03 | sports v2 | 133% |

**0.07 is the maximum across every live category**, so the error is one-directional: costs were
overstated in every gate, never understated. Those refutations stand *a fortiori* and Class C's
unbanded NOT-REFUTED would be more not-refuted, not less. The alpha on those looks is spent (A6) and
**they are not re-run**; Gate M2 reads each market's live schedule instead of the constant.

`takerOnly` is `true` on **11 of 11** schedules, which retrospectively confirms `maker_fee_coeff = 0.0`.

### 33.2 The registration's own fee table was stale, and its claim about which category dominates was wrong

Two errors in Class M2's registration, both transcribed from published documentation rather than
measured:

1. **Sports pays a 15% rebate, not 20%**, and there is a second live sports schedule
   (`sports_fees_v2`, 0.03/25%) that the published table does not mention at all.
2. **"81 of 100 markets sampled are `politics_fees`"** was a small-sample artifact. Unfiltered, the
   universe is **52% sports and 20% politics**; after this gate's own band and tick-room
   preconditions, politics is **20 of 195**. The registration's headline — a 75% overcharge on "the
   dominant category" — named the wrong category.

**Neither error reached the arithmetic**, because the runner reads `feeSchedule` per market rather
than a hardcoded table. That is the whole reason it did not: a table in prose cannot be wrong in a
way the code notices, and this one was wrong for a day. The lesson is Pass 28.2 again — the defect
was in the sentences surrounding the measurement, not in the measurement.

### 33.3 Holding rewards were added as a positive without charging what the capital costs

The first run of `gatem2.py` reported a total that added **3.25%/yr** of holding rewards to the
spread and rebate terms while charging nothing for the capital those rewards require. Holding
rewards are paid on **held position value**; this repository charges **6%** for locked capital.
3.25% on capital costing 6% is a **net loss of 2.75%**.

Corrected: capital is stated explicitly ($1 per posted contract per market, the cost of the hedged
YES+NO pair), charged at the 6% hurdle, and holding rewards appear beside it — where at 2,000
contracts they contribute **−$10,725**, not +$12,675. The verdict survives only because the rebate
is 4.9x the entire cost of capital.

This is **Pass 27.1 in a new costume**: a rate added to a dollar total without pricing the dollars.
Caught in the same session that produced it, by re-reading the column headings.

### 33.4 The meta-guard was red at `HEAD` and the Gate F commit was pushed anyway

`TestCorrectionsLogStaysExecutable` fails when a pass is added to this log with no guard in
`test_regressions.py`. Checked out at `a6832ca`, it **fails on `Pass 32`** — the Gate F commit added
the corrections entry and never added the guard, and the push went out with the suite red.

The ordering that produced it: run the suite, *then* write the corrections entry, then commit. The
guard exists precisely to catch a correction that stays prose, and it caught this one a day late
because nothing re-ran it after the prose was written. **Verification must come after the last edit,
not after the last code edit.** Guards for Passes 32 and 33 are now present; the suite is green.

### 33.5 The registered decision rule said "reported separately" and the runner nets them

Amendment, recorded rather than applied silently: the registration specified holding rewards be
**reported separately** from the market-edge terms. The runner reports them in their own column *and*
includes them in NET, because once capital is charged they are a **cost-bearing** term — excluding a
negative contribution from the total would flatter the hypothesis. Adding a charge that cuts against
the hypothesis is permitted; the reverse would not be.

---

## Pass 32 — Gate F run; carry does not clear the cost of the capital it locks (2026-09-14)

Class F registered and run. Result in [`GATEF-RESULTS.md`](GATEF-RESULTS.md). **REFUTED: best net
return on deployed capital `+2.85%`/yr against a `6%` hurdle, and every leverage that would raise it
was liquidated on the real price path.**

### 32.1 The estimator manufactured a profit out of a liquidation, and the null gate caught it

Gate F's null gate **failed on its first run**: `liquidation_cascade` reported a profit in **35%** of
replications of a world that liquidated in **100%** of them.

The cause was a discretization defect. A period can jump far past the liquidation trigger, and the
estimator credited the spot leg at that **overshot** price while losing only the fixed margin — so a
violent breach paid *better* than a marginal one. Exchanges liquidate continuously and nobody keeps
the overshoot.

Fixed in the estimator, not the worlds (A8): the spot is credited **at the threshold**, making the
residue exactly maintenance + penalty + one crossing, with the larger loss being the carry never
earned afterwards. A regression test now asserts a bigger breach cannot pay more than a smaller one.

### 32.2 The exhibit is the whole argument for the class of gate

On the liquidation world the **naive carry sum** — funding totalled, four crossings charged, price
path ignored — reports **`+4.71%`** where the truth is **`-0.67%`**. A 5.4-point error that flips the
sign, produced by an estimator that never looks at the price.

**That is what every public carry backtest over a calm window is.** The carry is paid *for* the
crash; a sample without one measures the premium and none of the risk.

### 32.3 The trade-off is now measured rather than argued

Leverage is the only lever that raises return on locked capital, and it is the same lever that lowers
the breach threshold. BTC pays most at 3x (`+2.85%`) and is **liquidated at 5x** (`-2.72%`); SOL is
liquidated at **2x**. Even a 98-day window that looks calm in aggregate breached those thresholds.

### 32.4 A venue is legally unreachable, and that is a measurement

`fapi.binance.com` returns **HTTP 451 — Unavailable For Legal Reasons** from the operator's
jurisdiction. The deepest-liquidity venue for this trade cannot be reached at all. Recorded as an
operator precondition of the kind Gate C refused to assume; nothing here asserts eligibility to
trade any venue.

OKX caps funding history at **98 days**, verified against a retrying fetcher so the limit is a
genuine end rather than a swallowed rate limit (Pass 9). The sample therefore cannot be guaranteed
to contain an unwind — **which is why the refutation rests on the null gate rather than on the
window.**

---

## Pass 31 — Gate R run; a verdict whose sign depends on an accounting choice (2026-09-14)

Class R registered and run. Result in [`GATER-RESULTS.md`](GATER-RESULTS.md). **NOT REFUTED on the
registered rule by $6,324/yr at one size, negative at every larger size, and positive everywhere
under the other honest accounting.**

### 31.1 The implementation diverged from the registration, and the absurdity caught it

The frozen rule is `pool x share(s) - fills(s) x 0.0096`. The first implementation added
`+ fills x distance`, an unregistered capture term, and reported **$3,257,641/yr at `s/v = 1.0`** —
the one distance at which rewards are **zero by construction**.

**An optimum sitting exactly where the measured thing pays nothing is a structural tell**, and it is
what exposed the defect. The number came from applying Gate M's constant at 4-6x the distance it was
measured at, a caveat the code itself carried in a comment and then let stand as the verdict. Naming
a limitation and then reporting the number it invalidates is the failure, not the caveat.

### 31.2 The registration double-counts adverse selection

Gate M's `R(60)` is **already net** of adverse selection — it is what a maker keeps. The registered
rule charges `0.0096` per fill against a capture of **zero**, which charges the same cost twice. The
per-fill P&L consistent with Gate M and with `gate3.py` is `RETENTION x s`: small, and **positive**.

The two accountings **disagree in sign at every size above 20**: at 100 contracts and `s = 0.1`,
`-$30,415/yr` registered against `+$39,820/yr` consistent.

The registered rule was run as the verdict because it is what was frozen (A8), and the consistent
reading is reported beside it. **A verdict whose sign depends on an accounting choice is not a
finding, and recording that is the result.**

### 31.3 Reading the primary source inverted the candidate that generated this gate

The `principles-20-solutions` run that produced Class R selected *"quote at the max-spread edge to
earn rewards while minimising fills."* The venue's published score is `((v-s)/v)^2` — **zero at the
edge**. Rewards pay quadratically more for the tighter quote, which is also the position of maximum
adverse selection.

The candidate had been generated against a **search-result summary**; one fetch of the venue's own
documentation destroyed its premise. This is the skill's own "second-hand framings" rule earning its
place, and it is the third time in this arc that re-reading a primary source changed a conclusion
(the others: Pass 26.1's unenforced exclusion, and the re-probe that recovered
`rewards_daily_rate` after a first probe had eliminated the whole class).

### 31.4 What the class establishes, and the term it cannot measure

At the honest end — Gate-M-consistent accounting, at a size where the assumption holds — subsidy
capture across the **entire** incentivized universe is worth **tens of thousands of dollars a year**.
Two to three orders of magnitude above Class C (`$10.47/yr`) and Class M's Gate 3.0 (`~$1,200/yr`),
and still not a business that justifies the build.

**The deciding term is unmeasurable from outside:** `own / (own + competitors)` is a snapshot of
today's competition, and the whole question is what it does when an entrant arrives. A congestion
game cannot be resolved by observing it from outside the congestion.

Two subsidy programmes remain untouched: **maker rebates** and **holding rewards**
(`holdingRewardsEnabled`), both of which cut for the hypothesis.

---

## Pass 30 — Gate 3.0 run; the fills arrive, and the registration's predictions did not (2026-09-14)

Result in [`GATE3-RESULTS.md`](GATE3-RESULTS.md). **Both variants clear the floor at every size
measured; Class M survives.** The queue turns over ~36 times a day and only 2.4% of markets fail to
clear it.

### 30.1 The registration specified variant (a) with no cap on posted size

It wrote expected fills for an order joining the back of the queue as
`max(0, side_flow - touch_depth)` — which lets one entrant absorb **every contract of excess flow at
unlimited size**. First run: (a) returned `$123,586/yr` against (b)'s `$6,480`.

**That ordering is structurally impossible.** (a) sits strictly behind (b) in the queue and can never
earn more at equal size. The arithmetic was right and the model was absurd, which is the same shape
as every defect since Pass 26. Both variants are now capped at the size actually posted, once a day
— conservative, and stated rather than tuned.

### 30.2 The registration froze no posted size, which C11 exists to prevent

C11 says a design variable is not held at one value. Gate 3.0's frozen-parameters table specifies
units, weighting, preconditions, statistic and floor — **and no size**, while the entire verdict
scales linearly in it: `$245` at 5 contracts, `$76,078` at 2,000.

**With no registered size there is no registered verdict, only a curve.** Choosing a point on it now
would be selecting the answer after seeing it (A8), so the curve is reported whole and the headline
is given at the size whose retention assumption still holds.

### 30.3 Both pre-committed expectations were wrong, and that is the useful part

The registration predicted that markets wide enough to quote in would be wide *because they are
quiet*, so (a) would approach zero fills and (b) would be the interesting variant. **Both wrong.**
The markets are wide and active — 36 queue turnovers a day — and **(a) beats (b) at every size**,
because paying two ticks for priority is wasted when you get filled anyway.

Recorded prominently because a registration whose predictions are checked and fail is worth more
than one whose predictions are never checked. Every prior gate's adverse prior was confirmed; this
one's was refuted.

### 30.4 Where these numbers stop being trustworthy, stated with the result

Every figure rests on `RETENTION = 3.9%`, measured in Gate M **on aggregate flow**. At a posted size
of 500 against a median touch depth of 148 an entrant is three times the resting queue; at 2,000,
thirteen times. **They are then the book rather than a share of it**, and the flow reaching them is
disproportionately the informed part the retention was averaged over.

**The large-size rows are the least trustworthy and the only ones producing interesting money.** At
the sizes where the assumption holds the magnitude is about **$1,200/yr**. As a *rate* it is roughly
40% on ~$3,100 of capital, and Pass 27.1 is the standing reason that framing is not the question.

---

## Pass 29 — Gate M run; the spread survives, 3.9% of it (2026-09-14)

Gate M's null gate passed and the measurement ran. Result in
[`SCANM-RESULTS.md`](SCANM-RESULTS.md). **Verdict NOT REFUTED; a maker retains 3.9% of the quoted
half-spread and informed flow takes 96.1%.**

### 29.1 The null worlds traded every step; the real data is 95.7% stale

Before trusting the verdict, the real series was characterised: **95.7% of minute-to-minute prices
are unchanged and 59.6% of contributions are exactly zero.** Polymarket's `prices-history` is a
minute-sampled series, not a trade sequence, and the null worlds generated a trade every step.

**The estimator had been validated on a process the data does not resemble. That is the G14 failure
Gate C already committed** — power 1.000 against its own parser's dialect, 0/26 against real venue
text — and it was caught here only because the real series was measured before the number was
believed rather than after.

Fixed by adding two worlds at the measured staleness. The estimator **survived**: STALE informed
0%/100% profit/loss, STALE bounce 100%/0%, and STALE bounce recovers `+0.00928` against a true
`+0.01000`. So the verdict stands. It did not have to, and the check was one probe.

### 29.2 The power precondition compared incommensurable counts

The registered threshold of **100,000 observations** was calibrated on synthetic *trade sequences*
where every observation is a distinct trade. It was applied to **minute samples**, ~96% of which
carry no trade. `276,421 >= 100,000` was therefore not a check of anything — a units error of the
same family as Pass 27.1, in a precondition rather than a hurdle.

Re-calibrated in the regime that actually obtains: at 276,000 samples and 95.7% staleness, detection
is 10/10 in both directions. That, not the raw count, is what licenses the verdict.

### 29.3 The pattern extends: five gates, five defects, and they are not only in decision rules

Pass 28.2 recorded three gates with three decision-rule defects and zero measurement defects. With
Gate M:

| pass | gate | defect | where |
|---|---|---|---|
| 26.1 | D.0 | omitted a standing precondition | decision rule |
| 27.1 | 4.0 | rate tested against a magnitude | decision rule |
| 28.1 | M.0 | markets weighted, hypothesis about flow | decision rule |
| — | M | statistic measured the wrong quantity; sign backwards | **estimator design**, caught pre-run |
| — | M | point estimate where the quantity is noisy | **inference**, caught by the null gate failing |
| 29.1 | M | null worlds unlike the real data | **validation regime** |
| 29.2 | M | precondition in the wrong units | precondition |

The refinement to Pass 28.2: the errors are not specifically in decision rules, they are in
**everything that surrounds the measurement** — what is measured, how its noise is handled, what it
is validated against, and what the threshold means. The arithmetic was correct every time.

Two of Gate M's four were caught by the protocol's own machinery working as designed: the null gate
**failed on its first run** and forced the interval inference, and the estimator's replacement
happened before it ever ran. That is the machinery earning its cost.

### 29.4 What the verdict licenses, and the number that outranks it

NOT REFUTED means the interval sits above zero. It does not mean the economics work.

Gate M.0's gross ceiling of `$29.28M/yr` on with-room flow becomes **~$1.14M/yr** net of measured
adverse selection, at a 100% capture rate that is impossible — incumbents already hold **77.4%** of
flow at one tick. At a 1% share it is ~`$11,400/yr`, before queue position, inventory, infrastructure
and operator time, none of which is measured and all of which cut against.

**The tick test attenuates `R` toward zero**, measured: a true `-0.010` reads as `-0.0028`. Zero is
the direction that flatters the maker, so **NOT REFUTED is the less trustworthy of the two possible
verdicts here**, and the true retention may be below 3.9%.

Per the registered rule this proceeds to Gate 3, whose content for this class is **queue position** —
nothing measured here says the fills would arrive at all.

---

## Pass 28 — Gate M.0 run; the constraint moved, and a third decision rule was miswritten (2026-09-14)

Gate M.0 ran as registered. Result in [`GATEM-RESULTS.md`](GATEM-RESULTS.md). It is the **first
dead-on-arrival check in this repository that a hypothesis has survived with room to spare**, and
the first time the binding constraint has moved rather than been confirmed.

### 28.1 The registered falsifier weighted markets, and the hypothesis is about flow

The registered primary condition was *"the median in-band market must quote more than one tick."*
Measured **2.0 ticks** — it passes. Asked of the **flow** instead: **77.4% of measured volume sits in
markets quoted at one tick**, where an entrant cannot improve the quote and can only join the back of
an existing queue.

The disagreement was visible mid-run. A two-page sample of the volume head returned median **1.0
tick and REFUTED**; the full sweep returned **2.0 and NOT REFUTED**, because the low-volume tail is
where the wide spreads live. **Tick room and flow are anti-correlated** — the room is in markets
nobody trades.

**The condition is not rewritten after the fact.** The registered verdict stands; the flow-weighted
number is reported beside it. It does not overturn NOT REFUTED — $532M/yr of flow does sit in
markets with room, three orders of magnitude above what the floor requires — but it materially
changes what the verdict means, and a reader given only the unweighted median would have been
misled.

### 28.2 Three gates, three decision-rule defects, zero measurement defects

The pattern is now worth naming, because it is a property of this method rather than three
accidents:

| pass | gate | the measurement | the decision rule |
|---|---|---|---|
| 26.1 | D.0 | correct | omitted a registered exclusion (longshots) that flipped the verdict |
| 27.1 | 4.0 | correct | tested a **rate** against a **magnitude** constraint |
| 28.1 | M.0 | correct | weighted **markets** when the hypothesis was about **flow** |

Every apparatus did what it was built to do. Every error was in the sentence that decided what the
number meant. The protocol's discipline is overwhelmingly aimed at the measurement — null worlds,
sealed holdouts, cluster-robust inference, pre-registration — and **none of that machinery inspects
whether the decision rule is dimensionally right, correctly weighted, or applies the preconditions
the protocol already carries.**

The lesson extracted, and it is cheap: **a registered decision rule must state the units of its
threshold, the weighting of its statistic, and which standing preconditions it applies.** All three
defects above would have been caught by writing that sentence before the run rather than after.

### 28.3 What the moved constraint does and does not license

Gate 4.0 measured the taker ceiling at `$10.47/yr` on `$24.40` of deployable capital. Gate M.0
measures a gross maker ceiling of `$29,280,877/yr` on the `$532M` of annual flow in markets with tick
room. **Six orders of magnitude**, and it is a genuine structural difference rather than a bigger
number: the taker constraint was capacity and could not be elevated by any amount of edge search.

**It licenses one thing: Gate M, a measurement of adverse selection and queue position on real trade
data.** No executor, no quoting, no capital (F3).

It licenses **no claim that market making here is profitable**. Adverse selection, queue position,
inventory risk and competitive response are all excluded and all cut against; Polymarket's maker
rewards (advertised on 1,318 of 1,436 measured markets) are excluded and cut for. A 3.26% gross
spread per dollar of flow is what a maker collects **if the flow is uninformed**, and the whole
business of market making is that it is not. The excluded terms do not trim the ceiling, they decide
its sign.

---

## Pass 27 — Gate 4.0 run; a rate hurdle cannot measure a scale constraint (2026-09-14)

Gate 4.0 was registered out of gate order on a Theory-of-Constraints reading: Gate 4 sits behind
Gate 3, behind having a candidate, so the one measurement that could kill the programme for free was
scheduled after every expensive thing in it. That ordering is a **policy constraint**, and capacity
is a property of the venue rather than of any strategy, so it needed no candidate. Result in
[`GATE4-RESULTS.md`](GATE4-RESULTS.md).

### 27.1 The registered objective floor was the wrong *kind* of quantity

The floor was *"beat `settlement_wedge_annual` (6%/yr) on capital locked"*, chosen deliberately as an
**existing** constant so it could not be a threshold invented to be clearable. It was cleared:
`$10.47/yr` against a `$1.46` hurdle, a 43% return on capital.

**And 43% on twenty-four dollars is ten dollars.** Deployable capital across the entire reachable
cross-venue universe is `$24.40`. A rate hurdle passes trivially when the denominator is small, so
the test as registered cannot separate *"this is a business"* from *"this is ten dollars a year"* —
which is the only question Gate 4.0 existed to answer. **Throughput is dollars, not percentages**,
and the registration used a rate to test a magnitude.

**The hurdle is not being changed after seeing the result**, which is the A8 move and would be
especially tempting because changing it produces the answer the registration predicted. What is done
instead: the registered verdict is reported as it came out, this defect is recorded, and the finding
is restated in the units the question was asked in — `$24.40` deployable, `$10.47/yr` ceiling under
assumptions that cannot be met. That sentence needs no hurdle to interpret, and the registration had
already said clearing the floor was necessary and never sufficient.

**Guarding an existing constant against being *chosen* is not the same as checking it is the right
dimension.** Pass 26.3 recorded a sketch mistaken for a measurement; this is its sibling — a
well-sourced number applied to the wrong question.

### 27.2 A count that was inferred and published as measured

`GATED-RESULTS.md` and commit `6b4348b` both stated *"two pairs of 81 have a gap exceeding their own
round trip."* That was read off the printed **top-10** table, not counted across all 81. Counted
directly by `gate4.py`: **4 clear, of which 3 are longshots outside the registered band, leaving 1.**

Wrong in both directions — undercounting the clearing set and overcounting the tradeable one. This
is the G5 failure the repo already guards against in the other direction (an error and a measurement
sharing a counter); here an **inference and a measurement shared a sentence**. Corrected at the
source in `GATED-RESULTS.md`; the commit message stands as the historical record and is corrected
here rather than rewritten.

### 27.3 What the capacity finding does and does not license

It establishes that **capacity is the binding constraint and it is external** — one in-band
opportunity, `$24.40` deep, across everything two venues jointly reach. Not by the floor test, which
passed, but by magnitude.

It does **not** say no edge exists, and it is not a statistical result (A1). It says that if one
exists there is nowhere here to put meaningful money. Elevating a capacity constraint is structural
— a different role (maker rather than taker, the one untested lever inside these venues, where
`maker_fee_coeff` is already `0.0` and the spread becomes income rather than cost), a different
market, or a different product. **Each is a new registration, not a continuation of this one**, and
none is licensed by this pass.

---

## Pass 26 — Gate D.0 run; a registered exclusion that no scanner enforces (2026-09-14)

Gate D.0 ran as registered on the 140-pair alignment table. Result and full limitations in
[`GATED-RESULTS.md`](GATED-RESULTS.md); what belongs here is the four things it got wrong or found
wrong, none of which were visible before the arithmetic was actually walked off real books.

### 26.1 The longshot exclusion is registered "at every gate" and enforced by no scanner

`PROTOCOL.md` **Market-selection preconditions** exclude longshots at every gate, and
`CostModel.price_in_band` implements it. It is called in `kairos/gate.py` and `kairos/sizing.py`
**and in no scanner at all** — not `gated.py` as first written, and **not `scanb.py` or `scanc.py`**,
whose results are already recorded.

It decides this gate. Of 81 pairs priced at 25 contracts a side, **52 are out of band**, and the
single widest gap in the table sits on a market quoted at **3.8 cents**. Unbanded the class is NOT
REFUTED; banded, on the 29 survivors, it is REFUTED.

**Not resolved by picking one.** The banded reading is what the protocol says; the unbanded reading
is what every prior Class B measurement here actually did, so substituting it silently would make
this run non-comparable with the result it exists to be compared against — and choosing after seeing
both is the A8 move. `gated.py` reports both and says which is which.

**The status of `scanb.py` and `scanc.py` is flagged, not changed.** Re-running either is a new look
at a hypothesis whose alpha is spent, and it is not licensed by this pass. What is recorded is that
their nulls were measured **without** an exclusion the protocol requires — and since the exclusion
removes the cheap-looking longshots that drag a median down, its absence made those nulls *more*
likely to find something, not less. A null measured on a superset is still a null.

### 26.2 The first Gate D.0 run had no band, and its verdict is on the record

The band check was absent from the first execution, which reported a bare `NOT REFUTED` on largest
gap `+0.09775` against median round trip `0.02824`. Found by inspecting the pairs behind the
headline, not by a test.

Recorded rather than quietly patched **because the fix moved the verdict toward the outcome the
registration predicted.** A correction that produces the expected answer deserves more scrutiny than
one that produces a surprise, not less, and the way to keep it honest is to publish the pre-fix
number next to the post-fix one.

### 26.3 The registration's own cost estimate was wrong by a factor of four, in its own favour

Class C's registration put four crossings "around `0.13`" by extrapolating from Class B's `0.0834`
zero-fee hold-to-settlement cost. **Measured: `0.02824`.** The extrapolation subtracted one modelled
quantity from another and treated the remainder as a crossing cost; walking four real books gives a
number four times smaller.

The lesson is not that the prior was adverse — being adverse was the point. It is that **an
arithmetic sketch inside a registration is not a measurement**, and Gate D.0 was worth running
precisely because it could contradict the registration that created it. Had the sketch been trusted,
Class C would have been refuted on a number that is wrong.

### 26.4 A stale instruction in the execution order, withdrawn

PROTOCOL's execution order still listed as the next Class B step: *"extend discovery beyond the top
~800 open markets by volume."* `scanb.open_neg_risk_markets` already sweeps **both** volume
orderings across the whole offset-reachable universe, and `SCANB-RESULTS.md` records it. The
instruction was satisfied before it was read.

**Withdrawn.** The genuine remaining limit is different and is named in `SCANB-RESULTS.md`: Gamma's
`offset` caps at 2100, so the sweep covers the universe *offset pagination can reach*, not the
venue. Getting past it needs date-windowed discovery for open markets, as Look 3 built for closed
ones. That is **not** licensed by this pass and is not registered.

---

## Pass 25 - Class C (convergence) registered, with its own prior against it (2026-09-09)

`docs/PROTOCOL.md` **Class C / Gate D**. Registered **before** anything was built and before any
price *history* was fetched on either venue.

### Why a new class rather than a rescue

Class B cross-venue measured the cost of a hedge **held to settlement**: 117 pairs, zero clearing,
median `-0.09579`. That does not refute the literature it was built on. Gebele et al. measure a price
gap *at the touch*; we measured the executable cost of holding a two-leg hedge for a ~114-day median
horizon. A persistent 2-4% gap can be real and still unreachable that way.

Class C is the other route to it - enter on the gap, exit when it closes, never hold to settlement -
and it is a different hypothesis with different risk. **There is no riskless leg.** It inherits none
of Class B's licences.

### The registration argues against itself, on purpose

A convergence round trip crosses **four** books; the Class B trade crossed two and let settlement pay
the rest. So Class C pays more transaction cost and less carry, and wins only if the carry saved
exceeds two extra crossings. From the Class B run: of `0.0834` zero-fee cost, carry at 114 days is
roughly `0.019`, leaving about `0.065` of crossing cost for two legs - so **four crossings is around
`0.13` against carry savings of at most `0.019`.**

On those figures Class C is *worse* than the hypothesis that already failed. That is written into the
registration as **Gate D.0**, a dead-on-arrival check that runs first, needs no time-series data, and
refutes the class outright if the largest observed gap does not exceed the median round trip.
**Recording the adverse prior before producing the number is the point** - otherwise a negative
result later gets presented as a surprise rather than as the expected outcome it was.

### Two design choices that could have been made the convenient way

- **Hedged, not unhedged.** The unhedged variant costs two crossings instead of four and would look
  far better. It is also not a convergence test: its profit is dominated by whether the event
  happens, so a positive result would be uninterpretable. The cheaper instrument is the one that
  cannot fail cleanly, and it is refused.
- **The control must come from a process the detector was not written against.** This is G14 applied
  before the fact rather than after: Gate C scored power 1.000 against its own parser's dialect and
  0/26 against real text, and a convergence control drawn from the detector's own model would repeat
  that exactly.

### The false-positive generator, named

**Bid-ask bounce.** Any two noisy series show apparent convergence after a large observed gap,
because a large gap is partly measurement error and error mean-reverts by construction. Five null
worlds are registered against it, including the discriminating one - a real, fast, mean-reverting
spread whose amplitude is simply smaller than the round trip.

### Data discipline

The 140-pair snapshot has been seen; the histories have not. That distinction is thin and is exactly
where a forking path opens, so the snapshot is confined to the cost arithmetic and may not inform
pair selection, entry threshold or horizon. **A pair whose history is fetched is spent** - usable
once, never re-run after a failure.

---

## Pass 24 - The alignment table produced FALSE PAIRS, and the measurement caught them (2026-09-09)

`adjudicate.py`, `docs/alignment-groups.json`. Adjudication was scaled from 60 pairs to a 1,100-pair
pool by labelling **event groups** rather than pairs - one semantic judgement covering N outcome
pairs, because the same question answered thirteen times drifts. That was the right move and it was
applied wrongly.

### The claim withdrawn

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 24.1 | The 233-pair alignment table | **Contaminated. 40% false pairs** | A group key names the **Kalshi** event; the **Polymarket** side of a group is not homogeneous. Applying one exemplar's label to every member asserted a homogeneity nobody checked. **94 of 234 labelled pairs failed subject containment** once it was tested |

### The mispairs, and what exposed them

| Polymarket | Kalshi | claimed edge |
|---|---|---|
| Will a country leave **BRICS** in 2026? | Will another country leave **OPEC** in 2026? | +0.169 |
| **Trump** out as President by September 30? | **Gianni Infantino** out as President of **FIFA** | +0.106 |
| Morgan Wallen **Billboard** #1 top artist | Top artist on **Spotify** | **+0.754** |
| Frankfurt **to score first** | Mainz vs Frankfurt: **BTTS** | +0.204 |
| Balance of Power: **R Senate, D House** | **R-House, D-Senate** (inverted) | +0.299 |

**A +0.75 "edge" is not an arbitrage, it is a mispair announcing itself.** Every one of the ten pairs
that appeared to clear costs was a false pair. Had the table been trusted, the run would have
reported a large positive cross-venue arbitrage consisting entirely of markets about different
things.

### Two mechanical guards, now in code

1. **Subject containment** - every content token of the Kalshi event title must appear on the
   Polymarket side. This is what BRICS/OPEC and Trump/Infantino fail.
2. **Outcome match** - a Kalshi contestant must share a content token with the Polymarket title, so
   a Ballon d'Or group cannot pair Haaland against Messi.

A third case is refused rather than guarded: `2026 Midterms: Congress Balance of Power?` encodes its
outcome as party-chamber pairs whose distinguishing tokens are **single letters**. No token rule sees
`R Senate, D House` against `R-House, D-Senate`, and hand-adjudication got it wrong. **A group whose
outcomes cannot be checked is refused whole** (A6).

### The cleaned measurement

140 aligned pairs, 117 priced. **Zero clear costs.** Best `-0.00100`; median `-0.09579` at 25
contracts, `-0.08338` at zero fees - so the fee assumption is not what sinks it. The implausible
outliers are gone with the mispairs that produced them.

**VERDICT: WITHHELD.** 140 against the registered floor of 200. The count fell *below* the floor
because the guards removed 40% of the table - the honest direction.

### A second defect, found while reading the output

`run_alignment` had **no branch for reaching the floor**. It printed WITHHELD unconditionally, so at
233 pairs it reported "233 against a floor of 200" and called it underpowered in the same sentence. A
runner that structurally cannot announce a pass is not a measurement, and its verdict text agreeing
with the correct answer by accident is worse than a wrong one. Both branches are now written.

---

## Pass 23 - Gate C3 registered, table adjudicated, measurement completed end-to-end (2026-09-09)

`align.py`, `docs/ALIGNMENT.json`, `scanc.py --alignment`. Registered **before** building; adjudicated
**before** any price was fetched; measured after. **First cross-venue measurement that reached a
number.**

### The registered check fired

**Recall 0.000 against `RECALL_FLOOR = POWER_FLOOR = 0.50`.** The floor was deliberately the repo's
existing constant rather than a new one - inventing a threshold after seeing the old instrument score
zero is how a floor gets chosen to be clearable. The mechanical matcher is disqualified as a pair
source: its verified count measures the matcher, not the venues (G12).

### The table

60 mechanically-surfaced candidates, adjudicated from titles and settlement instants only:

| label | count |
|---|---|
| FUNGIBLE-WITH-BASIS | **36** |
| DISTINCT | 24 |
| **IDENTICAL** | **0** |

**IDENTICAL is empty and that is a finding, not a gap.** It requires a YES on one venue and a NO on
the other to pay $1 in *every* state. Even for pairs sharing a settlement instant **to the minute**
(Bitcoin-vs-gold: 05:00Z against 04:59Z), the venues' resolution criteria could not be verified equal
from published text. **No cross-venue pair here can be certified riskless, and none is described as
such.**

The 24 DISTINCT are not near-misses of judgement - they are horizon mismatches of years. Fourteen
Romanian-PM pairs run "by 2026" against "by 2045"; two Trump-Putin pairs run 2027 against 2029. The
mechanical matcher refused all 60 for the same undifferentiated reasons, which is the point.

### A systematic convention gap, not a one-off

The Somaliland 10h01m gap generalises: Polymarket resolves "before YEAR" at **04:59Z** (midnight ET)
while Kalshi frequently uses **15:00Z**. That is a structural basis risk across a whole class of
markets, and it is why `settlement_time` appears in **30 of 36** aligned pairs' basis inventories.

### The measurement

29 of 36 priced (7 too thin on the NO leg at every size):

| size | pairs | median edge | best | clearing costs |
|---|---|---|---|---|
| 5 | 29 | **-0.03863** | -0.01173 | **0** |
| 10 | 29 | -0.03863 | -0.01173 | 0 |
| 25 | 29 | -0.03863 | -0.01403 | 0 |
| 50 | 29 | -0.03863 | -0.01586 | 0 |

**The size curve is flat**, so this is not a depth artefact - the same conclusion the intra-venue scan
reached by re-running at 10 and 5.

**And it is not a fee artefact either.** Fee sensitivity: median `-0.03863` charged against
`-0.03784` at **zero fees** - the whole fee assumption is worth **0.00078**. The quadratic fee is
small here because most aligned markets are longshots trading at a few cents, where `P(1-P)` is
tiny. So the unverified Kalshi schedule, which Pass 19 correctly refused to let drive a terminal
verdict, turns out not to matter for this sample: **fee verification cannot rescue this deviation.**
What remains is the venues' actual spread plus carry over a ~114-day median horizon.

### Verdict: WITHHELD, and honestly so

36 aligned pairs against a registered floor of 200. The numbers above are **descriptive and
underpowered**; the kill rule turns on a median over >= 200 pairs and does not fire below it (A1).
The divergence bound is still **1.000 (unmeasured)**, so no aligned pair may be called a candidate
regardless.

**What changed is the pair source.** The mechanical matcher found 0 of these 36; adjudication found
them in the same mechanically-surfaced pool. Reaching 200 is now bounded work - adjudicate more of
the 22,866 surfaced candidates - rather than a blocked measurement or an exhausted branch.

---

## Pass 22 - Recall measured at ZERO; three passes of conclusions withdrawn (2026-09-09)

`recall.py`. **The matcher's recall on real cross-venue markets is 0/26.** Every conclusion drawn
from `scanc.py` rested on that number and none of the four passes measured it.

### The measurement

Candidate pairs were surfaced by **token overlap through an inverted index** - deliberately not by
any check the matcher makes, so a pair the matcher would reject for date, source or modality reasons
still appears - then adjudicated by reading the published titles and rules. 22,866 candidates
surfaced from 4,147 Polymarket markets. The top 26 by overlap:

| Polymarket | Kalshi | matcher |
|---|---|---|
| Will another country leave OPEC in 2026? | Will another country leave OPEC in 2026? | refused |
| Will Ferrari be the 2026 F1 Constructors' Champion? | F1 Constructors Champion / Ferrari | refused |
| Will Erling Haaland win the 2026 Ballon d'Or? | Who will win the Ballon d'Or in 2026? / Erling Haaland | refused |
| Will Loranne Ausley win the Tallahassee mayoral election? | Tallahassee Mayoral Election / Loranne Ausley | refused |
| ...22 more, including 10 further Ballon d'Or candidates | | refused |

**26 of 26 are plainly the same event. The matcher paired 0.** One pair is *verbatim identical in
title* and was still refused.

### Claims withdrawn

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 22.1 | "These two venues list very few mutually fungible events" (Pass 21, and the `scanc.py` verdict text) | **False** | They list many. 22,866 token-overlap candidates; the top 26 are all real pairs. The count of 3 was a property of the matcher, not the venues |
| 22.2 | "Class B cross-venue is NOT TESTABLE on publicly available data" (Pass 21) | **Withdrawn** | Not established. It rested on 22.1 |
| 22.3 | "F3 blocks the remaining step, and that is a deadlock" (Pass 21) | **Withdrawn - misread** | F3 forbids *"broker integration, live capital, or production executor"*. Reading market data with an application key is none of the three. There was no deadlock; there was a constraint quoted without being checked |
| 22.4 | Gate C's **power 1.000** | **Circular, and the circularity is the root cause** | The positive control was published by the same generator the parser was written against, so the gate measured the parser against itself. Real-text power is ~0. Gate C's own limitation #1 said this in words - and a 1.000 sat in the verdict table anyway, where three passes read it as power |

### The root cause is Pass 11's defect, reintroduced one gate later

Pass 11 caught Gate B's positive control being circular: `inject_arbitrage` bisected on the
scanner's own cost formula. Gate C avoided that trap **at the arithmetic layer** and walked into it
**at the text layer** - `publish()` and `parse_market()` are two halves of one author's model of how
venues write. Precision was measured against nine adversarial worlds and came back 0.000, which is
real. Power was measured against the parser's own dialect and came back 1.000, which is not.

**A gate reports two numbers and they are not equally trustworthy.** The null worlds are adversarial
by construction; the control is only as adversarial as its author's imagination. Filed as G14.

### Why the refusals happen, and why none of them is fixable by tuning

- `resolution_source` on nearly every pair: Kalshi publishes a list of ~20 news outlets, Polymarket
  writes prose. Token-set **equality** of arbiters can essentially never pass. The right test is
  source *compatibility* - do both resolve on the same underlying fact - which is a semantic
  question, not a set operation.
- `scope_differs` on the Ballon d'Or block: *"Will X win the 2026 Ballon d'Or?"* against *"Who will
  win the Ballon d'Or in 2026? / X"*. One stopword apart.
- `resolution_date_differs` / `settlement_time_differs`: venue **conventions**, and Gate C already
  registered the machinery for this - a divergence bound compared against `break_even_failure_rate`
  at the measured edge - which was never used. A boolean was used instead.

### What this does not overturn

The Somaliland finding stands: two markets both labelled *"before 2027"* really do settle 10h01m
apart. Semantic non-fungibility is real. But Gebele et al. named their paper after it and still
aligned 100,000 events across ten venues, finding ~6% dual-listed. **Non-fungibility is the filter,
not the conclusion**, and treating it as the conclusion is what produced 22.1.

---

## Pass 21 - The venue-pair branch was taken, and it is exhausted (2026-09-09)

`venues.py`. Gate C's stopping rule prescribes *"a different venue pair"* below 200 verified pairs.
That move was made. **No publicly reachable third venue can host the measurement.**

### Done as a probe, not an adapter

A venue adapter costs a day. Three of the four feasibility checks kill a candidate in a minute, so
the probe ran first — and it killed both live candidates. Building the PredictIt adapter and *then*
discovering it publishes no rules would have been the same error as scanning before gating.

### What each venue actually publishes

| venue | rules | determination instant | depth | verdict |
|---|---|---|---|---|
| **PredictIt** | **none - no rules field exists** | 116/590 carry a bare date, **never a clock time** | **none - bestBuy/bestSell only** | identity unverifiable, size unmeasurable |
| **Smarkets** | 19/60 events | **0/55 structured, 0/55 from prose** | yes, real bid/offer ladder | the near miss: real exchange, no settlement time |
| Manifold | - | - | AMM | play money, resolved at the market **creator's** discretion |
| Metaculus / Insight / Limitless | - | - | - | 403 / 401 / 404, or no money at stake |

**Smarkets is the instructive one.** It is a real exchange with a real ladder and rules on some
events, and it publishes **no determination instant at all** - not structured, and not recoverable
from prose by the extractor Gate C2 built and gated. Before Pass 20 that would have looked like a
minor gap. After it, the cost is measured: Polymarket and Kalshi both list *"before 2027"* markets on
the same subject whose deadlines are **ten hours and one minute apart**, and in that window one venue
pays YES while the other pays NO.

Manifold fails for a different reason worth keeping separate: it is not a *data* limitation. A
CFTC-regulated contract cannot be hedged against a market resolved at a stranger's discretion at any
price, however good the API.

### Status of the programme, stated without softening

- **Class A (forecasting edge): REJECTED** on 1,966 fresh events.
- **Class B intra-venue (negRisk): REJECTED** across the full reachable open universe.
- **Class B cross-venue: NOT TESTABLE** on publicly available data.

The third is **not a rejection** (A1). The hypothesis has not been tried and found wanting; it has
been found unmeasurable with what can be reached. The kill rule does **not** fire, because it fires
on a measured median over >= 200 verified pairs and there were none.

### The deadlock, recorded rather than resolved

What remains is authenticated venue access - a Betfair application key, a broker account. That sits
outside **F3**: no broker integration until the protocol has been passed in order. And the protocol
cannot now be passed without it. **The remaining step requires the permission that completing the
protocol was supposed to earn.** That is a real deadlock, it is an operator decision rather than an
engineering one, and relaxing F3 quietly to escape it would discard the only thing the programme has
actually built.

---

## Pass 20 - Gate C2 built; the instrument falsified the diagnosis that motivated it (2026-09-09)

Registered Gate C2 before writing it, built the settlement-instant extractor, extended Gate C to
**nine** null worlds, re-ran the gate (PASS, power 1.000, every world 0.000) and re-ran the
measurement. **Verdict unchanged: WITHHELD.** What changed is why.

### The claim this pass withdraws is Pass 19's headline

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 20.1 | "The binding constraint is a missing **instrument**, not a missing **market**. The registration's prescribed next move - a different venue *pair* - is aimed at a cause the measurement did not find." (Pass 19) | **Withdrawn. Building the instrument refuted it.** | The extractor worked: it reconstructs the Somaliland market's `endDate` from its own prose to the minute. What it then revealed is that the genuinely dual-listed pairs **are not the same event**. The registration's guidance was right and my diagnosis was wrong |

### The finding, hand-verified on live markets

Two markets both titled *"before 2027"*, about the same subject, that a human would call the same
market:

| | Polymarket | Kalshi |
|---|---|---|
| market | Will Trump recognize Somaliland before 2027? | `KXRECOGSOMALI-29-27`, "Before 2027" |
| determination instant | **2027-01-01T04:59Z** (11:59 PM ET, Dec 31) | **2027-01-01T15:00Z** (10:00 AM ET, Jan 1) |

**Ten hours and one minute apart.** An event occurring in that window resolves YES on Kalshi and NO
on Polymarket. A position held across the two as a hedge **is not a hedge**: both legs lose. The same
gap appears on the second pair - `KXPAHLAVIHEAD-27JAN-RPAH` closes 15:00Z against Polymarket's
04:59Z, again both labelled "before 2027".

This is **semantic non-fungibility measured on live markets rather than assumed.** It is the exact
failure Gate C was built to catch, it is invisible in every title, and it is present on the pairs
that look *most* identical. Kalshi is not even internally consistent about it:
`KXRECOGPERSONIRAN-26` closes at 04:59Z while `KXPAHLAVIHEAD-27JAN-RPAH` closes at 15:00Z, both
"Before 2027".

### The count got worse and the knowledge got better

Provisional pairs went from **1 to 0**. That is not a regression. Before the extractor, the
Somaliland pair's settlement time was *unknown* and therefore merely unrecoverable; after it, the
time is known and the two markets are known to **differ**. Converting an unknown into a measured
difference reduces the count and increases what the run establishes - and a run optimised for the
count would have hidden exactly the thing worth finding.

### Modality, the seventh piece of evidence

*"Will X happen **by** T"* and *"Will X be true **at** T"* carry the same timestamp and different
payoffs - a barrier and a digital. An extractor returning the instant while discarding which one it
came from would **manufacture** the non-fungibility this gate exists to catch, so modality was
registered as evidence before the extractor was written. Recovering it showed it is missing on
**74% of Polymarket and 56% of Kalshi** markets, so it immediately became the second-largest blocker.
Failing closed on it is correct and costs power, which is the safe direction.

### Apparatus: daylight saving, computed rather than looked up

Windows Python ships no IANA database and this repo takes no third-party dependencies, so
`zoneinfo` raised `ZoneInfoNotFoundError` on `America/New_York`. A fixed -5 offset would be wrong for
eight months of the year, and **an hour of error is more than enough to make a 12pm market look like
a 1pm one** - the precise size of the mistake this gate exists to prevent. The post-2007 US rule is
implemented directly, and the **two ambiguous hours a year** - 02:00-02:59 in March which does not
exist, 01:00-01:59 in November which happens twice - are **refused rather than guessed** (A6).

### Method note - the diagnosis was itself a hypothesis

Pass 19 said the measurement was blocked on a missing instrument. That was a *claim about why a
measurement failed*, and it was tested the only way such a claim can be: by building the instrument
and looking again. It was wrong. **"The instrument is missing" and "the thing is not there" look
identical from inside a blocked measurement**, and no amount of reasoning about the funnel
distinguished them - filed as AXIOMS G13.

---

## Pass 19 - The cross-venue measurement ran; the zero is structural (2026-09-09)

`kairos/kalshi.py`, `kairos/crossvenue.py`, `scanc.py`, and their tests. **VERDICT: WITHHELD.**
0 verified pairs out of ~8.7M same-date candidates, against a registered floor of 200.

**The zero must not be read as a finding about the venues.** Polymarket publishes no determination
instant - `endDate` is a day boundary, measured at **65% exactly 00:00Z and ~95% day-boundary over
788 open markets** - so under Gate C's six-piece evidence rule *no* Polymarket/Kalshi pair can
verify, whatever the two venues list. The count is fixed by an apparatus limit, not by the market
population, and it is reported that way.

### What the run does establish

**Dual-listed events exist and the matcher recognises them.** The scope check - the one that could
have failed on vocabulary alone ("Bitcoin" vs "BTC") - agreed on three real pairs, and one of them
agrees on **every piece of evidence either venue publishes**:

| Polymarket | Kalshi | blocked by |
|---|---|---|
| Will Trump recognize Somaliland before 2027? | Will Trump recognize Somaliland? | *unrecoverable*: source, settlement time |
| Will Reza Pahlavi lead Iran in 2026? | Will Reza Pahlavi lead Iran in 2026? | + threshold presence |
| Will Bitcoin outperform Gold in 2026? | Will Bitcoin outperform gold in 2026? | source **differs** |

So the binding constraint is **a missing instrument, not a missing market**. The registration's
prescribed next move - "the honest next move is a different venue *pair*" - is aimed at a cause the
measurement did not find. What is actually required is a **settlement-instant extractor for
Polymarket prose**, which may not be written and used in one step: it is new extraction logic, Gate
C's null worlds never exercised it, and measuring with an ungated instrument is the error the whole
protocol exists to prevent (A7).

**The provisional pair was deliberately left unpriced.** Putting a deviation on the table before the
instrument that produces it has passed a gate is how Look 1 spent its alpha.

### Claims withdrawn or corrected - all three were apparatus, none were inference

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 19.1 | "`resolution_source_differs` blocks 100% of 2.28M pairs" | **Withdrawn - the census double-reported** | A field *neither side supplied* was counted as *disagreeing*. Two thirds of those were Polymarket markets whose arbiter is prose the extractor cannot read. Worse: a reason that fires on every pair makes the **sole-blocker column identically zero**, destroying the one diagnostic that names the binding constraint. `compare_identities` now reports unavailable evidence once, as unavailable |
| 19.2 | "`settlement_time_differs` blocks the dual-listed pairs" | **Withdrawn - it was our input, not the venues** | All three genuinely dual-listed pairs were refused for "settling at different times". They do not: we were feeding a **nominal day boundary** into a check designed for a determination instant. The check is sound; the input was not. Reclassified as unrecoverable, which still refuses the pair - it cannot manufacture one - but attributes the refusal correctly (G1) |
| 19.3 | The near-miss list ranked by fewest blockers | **Withdrawn - the metric rewarded dodging checks** | Two markets with no threshold on either side *cannot* be blocked by `threshold_differs`, so the list filled with "Will Jesus Christ return before 2027?" against every Kalshi market sharing its settlement instant. Re-ranked on **scope agreement**, which is the question the list exists to answer - and it immediately surfaced the three real dual-listed pairs |

### Apparatus facts measured against the live API, not assumed

**Kalshi's order book is one-sided, and reading it directly inverts the trade.** The venue publishes
only resting bids: `yes_dollars` are bids to buy YES, `no_dollars` bids to buy NO. A bid to buy NO at
`q` **is** an offer to sell YES at `1 - q`, so the YES ask ladder is the NO bid ladder mirrored.
Measured on 14 two-sided markets against the venue's own quotes: **`bid == max(yes_dollars)` 14/14**
and **`ask == 1 - max(no_dollars)` 13/14** (the miss was one tick between two calls seconds apart).
An adapter that read `yes_dollars` as asks would price every purchase **at the bid**, manufacturing
an edge equal to the whole spread on every market - a false positive on every pair with no symptom
anywhere else in the stack.

**`close_time` is the determination instant; `expiration_time` is +7 days of administration.**
Measured on `KXBTCD`: a market titled "12pm EDT" has `close_time` 16:00Z and `expiration_time` seven
days later. And Kalshi lists the *same underlying on the same date at different hours* - 12pm and 5pm
BTC markets - so Gate C's settlement-time null world is not hypothetical, it is the venue's product
structure.

**Kalshi's fee schedule is UNVERIFIED.** `kalshi.com` returned HTTP 429 and the documentation host
404ed. The registered fallback applies. It did not affect this verdict because no pair was priced,
but the runner refuses to announce Gate C's *terminal* branch on an unaudited number and reports the
fee coefficient at which the verdict would flip instead (G3).

### Method note - four sweeps, one verdict

The sweep ran four times, each re-run to fix an apparatus or reporting defect (the double-count, a
`UnicodeEncodeError` in the near-miss printer that crashed *after* computing the verdict, the ranking
metric, the settlement-time reclassification). **The verdict was WITHHELD with 0 verified pairs every
time.** A8 forbids tuning until the result changes; the result never moved, and the re-runs bought
diagnosis rather than a different answer.

---

## Pass 18 - Gate C built and run; the registration falsified itself twice (2026-09-09)

`kairos/identity.py`, `gatec.py`, `tests/test_identity.py`. **GATE C: PASS** - power 1.000 on the
control, 0.000 in all seven registered null worlds, 400 pairs each, every oracle ceiling 1.000.

The result that matters is not the pass. It is that **building against the registration falsified
the registration twice**, and both defects were of a kind prose review does not catch.

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 18.1 | "Pairing evidence: resolution date, threshold, resolution source, scope, side polarity - **all five must agree**" (Gate C frozen parameters, Pass 17) | **Incomplete as registered** | The same registration names a **settlement-time mismatch** null world - same question, one settling at market close and one at a fixed clock time. Two such markets agree on **all five** listed fields. A matcher restricted to the frozen list therefore *cannot* refuse a world the same document requires it to refuse. Amended to six, with the settlement instant named explicitly. The registration was checkable, and building it is what checked it |
| 18.2 | The matcher's date handling | **Produced a FALSE PAIR** | `_strip_dates` matched `\b(?:19\|20)\d{2}\b` to remove years, deleting **any strike in 1900-2099**. Markets quoted at 2000 and 2050 both parsed to *no strike*, agreed on every other field, and were declared the same event - the catastrophic case, arising in the date handling rather than in the comparison. Fixed by taking the resolution year from the published close timestamp instead of inferring it from the title |

### The pass/fail column could not see the defect

Gate C's first run reported **0.000 in every null world and PASS**. The false pair was still there.

It was visible in exactly one place: the refusal-*reason* column read `threshold_differs 386/400`
while the fire rate read a clean 0.000. Fourteen threshold mismatches were being refused for the
wrong reason - `threshold_presence_differs`, because one side's strike had been deleted - and a
refusal for the wrong reason is a pass sitting on top of a broken check (G7). Had both sides carried
a year-like strike, the pair would have been declared identical.

**Lesson, now an axiom (G10): a gate must report why it refused, not only that it did.** An
aggregate rate cannot distinguish a check that works from a check that is accidentally shadowed by
another one.

### The world could not have caught it either

A year-like strike was reachable only as *arithmetic inside* `threshold_mismatch` (2500 x 0.8), so
the **control never carried one**. This is Pass 3's defect exactly - a control that does not contain
its own hypothesis - and it recurred five passes after being written down. 2000 is now in the strike
pool, so every world including the control exercises it.

### What makes the pass meaningful

Not the zeros. `tests/test_identity.py` removes each of the six comparisons in turn and shows that
**exactly one null world starts pairing each time**: every check is necessary, and each null world
is what makes its check necessary. A gate no broken instrument would fail is decoration.

The circularity trap from Pass 11 was designed out rather than avoided by care: ground truth
(`EventIdentity`) is visible only to the world generators and the oracle; the matcher sees only
published text and must **recover** the evidence, with the two venues phrasing the same event
differently so a template-matcher loses power immediately.

### The exhibit's finding, which is stronger than expected

Title similarity swept over 60 thresholds and reported at the one **most favourable to it** achieves
a best separation of **+0.000** between true pairs and near-misses. Non-positive: there is no cut at
which it beats chance. And the reason is measurable - for the source and settlement-time worlds the
similarity vector is *identical to the control's, pair for pair*, because a venue puts neither the
arbiter nor the settlement clock time in the title. The evidence that separates a hedge from a
double position is not in the text the eye compares.

### Named limitations, so the pass is not over-read

1. **Coverage of real venue phrasing is untested.** The text distribution is ours. This falsifies
   the matcher's *logic*, not its reach over titles neither venue has been asked for.
2. **The oracle ceiling proves a world contains a mismatch, not that a venue publishes it.** On real
   data "the matcher missed it" and "the venue never said it" are indistinguishable from inside the
   matcher and must be told apart by hand.
3. **Source-string normalisation is assumed.** Two venues naming one arbiter differently would cost
   **power, not false pairs** - the safe direction - but it makes the measured 1.000 an upper bound.

---

## Pass 17 - Class B redirected to cross-venue; Gate C registered (2026-09-09)

Method: `principles-20-solutions`, proportionality 4/4, Consensus-backed. The decision and its
falsifier are registered in [`PROTOCOL.md`](PROTOCOL.md) **Gate C**, written before a single paired
market was fetched.

### The null was real but narrow

Class B's canonical form is refuted *at this venue and instant*: 78 completable negRisk groups, zero
positive, closest `-0.006`. The obvious rescue was tested first and **failed**: Cheng et al. report
76.9% of combinatorial opportunities capped at ~14.8 shares, and our scan ran at 25 - so re-running
at **10 and 5** contracts a leg was the natural suspicion. It changed nothing (0 positive at both,
best unchanged at `-0.034`). **The null is not a sizing artefact**, and that hypothesis is closed.

The principal cause turns out to be selection, not sizing: **we scanned the one arbitrage form
Polymarket's NegRisk adapter exists to eliminate, on one venue, at a static instant.** The literature
locates surviving structural edges cross-venue (2-4%, Gebele et al.) and in-play (101 bps but capped
at retail scale, Cheng et al.). Our best intra-venue observation was 0.6%.

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 17.1 | Kalshi parlay markup is a Class B (riskless) opportunity | **Withdrawn before it was built on** | Kalshi publishes `mve_selected_legs`, so parlays have *no* semantic-identity problem - which made the route look ideal. But **a parlay cannot be statically replicated from its legs**: owning one of each of N legs pays *number-of-winners*, not $1-iff-all-win. Moshrefi's documented overpricing is therefore an **edge with variance, not an arbitrage**. Filed as a different hypothesis class, not pursued. Caught by checking the payoff algebra rather than the paper's abstract |
| 17.2 | "Kalshi parlays are untradeable - 0 of 1,600 quoted, all zero liquidity" | **Refuted - endpoint artefact** | The `/markets` cursor sweep returned 1,600 markets *all* of which were MVE parlay shards and *none* of which were singles, which is not what a venue looks like. Re-probed via `/events?with_nested_markets=true`: **87 of 132 nested markets (66%) two-sided quoted**, and every named series returns asks. **Sixth time an apparatus artefact nearly produced a false decisive negative** (G2) |

### The decision

**Pursue cross-venue (Polymarket <-> Kalshi), and build its null gate before its scanner** - exactly
what Decision 001 required of Class B, for exactly the same reason.

The false-positive generator is **semantic non-fungibility**: two markets that look identical and
resolve differently. It is the precise analogue of leg-set truncation, which Gate B measured as
carrying the *entire* Class B defence, and Gebele et al.'s contribution is that resolving event
identity is the prerequisite rather than a detail. So Gate C's null worlds are seven kinds of
near-miss pair - horizon, threshold, scope, resolution-source, settlement-time, negation, random -
each of which must be refused, against a positive control of genuinely identical events which must
be matched.

**Resolution divergence gets the exhaustiveness treatment**, not a flag: measured on resolved
dual-listed pairs, expressed as a rule-of-three upper bound that never reaches zero, and required to
be smaller than `edge / (edge + stake)` before any pair is called a candidate. `residual_failure_bound`
and `break_even_failure_rate` are reused unchanged.

### The kill rule is real

Bendezu measured the falsifier directly: in Ecuador the 2.0pp half-spread **equalled** the 2.1pp
cross-venue gap. So Gate C registers, before the data: **if the median executable deviation does not
clear both venues' combined round-trip costs on >= 200 verified pairs, Class B is concluded and the
programme ends.** Not "try a third venue" - end.

### Method note - the guard caught its author

Gate C was written into `PROTOCOL.md` without a STATUS line, and the Pass-16 guard failed the suite
immediately with *"gates with no STATUS line: ['C ...']"*. The guard was added one pass earlier
precisely because an unmarked gate cannot be told apart from a forgotten one - and its first catch
was the next gate its own author wrote.

---

## Pass 16 - Second sweep: what the first one missed (2026-09-09)

Pass 15 closed every item that announced itself as open. This pass looked for the ones that did not
announce themselves - dead code, untested modules, and gates with no status at all. Four real
findings.

### Findings

| # | Finding | Resolution |
|---|---|---|
| 16.1 | **`costs.py` had no direct behavioural tests** | It was heavily *used* by six suites as a fixture, which is not the same as being *checked* - and a fixture that is wrong makes every test built on it wrong in the same direction, silently. `tests/test_costs.py` adds 23 tests, including pinning the two figures the docs quote everywhere: **2.5pp required edge and a 5.0pp no-trade band at 0.50 / 30 days** |
| 16.2 | **`fetch_resolved_markets_windowed` had zero consumers** | Written for Look 3, then `collect_fresh` called `fetch_window` directly and the wrapper was never wired in. It produced no recorded result, so plain deletion is right - C9a's "retain what produced a result" does not apply to code that never ran (E1, C9) |
| 16.3 | **`AdapterError` was exported and never raised** | Deleted |
| 16.4 | **Gates 3-6 carried no STATUS line** | Every gate that ran had one; the four that had not were silent, so a reader could not tell *correctly blocked* from *forgotten*. All four now state what they are blocked on. **Quote persistence is filed explicitly under Gate 3** rather than floating as a loose caveat |

### A near-miss worth recording

The orphan detector also flagged **`brier_score_pointwise`** as dead. It is not - `brier_score`
calls it, and the reference count was an artefact of counting occurrences in concatenated source.
Checking before deleting is the only reason it survived.

This is the ambiguity E1 names: **a zero-caller is not evidence of dead code.** It is equally
consistent with a seam landed ahead of its consumer, or with a detector that is simply wrong. Three
of the four flagged symbols were genuinely dead; the fourth would have been a silent breakage of the
Brier scorer.

### Method note - the two kinds of open item

Pass 15 swept items that *declared* themselves open: the words "pending", "deferred", "TODO". Pass
16 found that class already empty and had to look for silence instead - a module with no test file,
a function with no caller, a gate with no status. **The second kind is harder to find and more
dangerous, because nothing about it looks wrong.** A stale "pending" at least admits it is a claim;
an unmarked gate and an untested cost model look exactly like finished work.

---

## Pass 15 - Open items closed (2026-09-09)

A sweep of every deferral, pending status and open limitation in the repo, triaged into **resolved**,
**declined with reason**, and **not resolvable here**. Leaving all three looking alike is how a stale
status becomes a false claim a later session acts on.

### Resolved

| item | outcome |
|---|---|
| **11** - manipulation gate | The size-scaled threshold is **withdrawn** and `min_manipulation_cost_multiple` deleted from `GateConfig`. A price-settled market is now refused **unconditionally** unless an `external_manipulation_analysis` is attached - a human-written string, deliberately not computable, because if it could be derived from fields we already hold the refusal would not be needed. Six tests, including that a **$1bn** measured cost no longer buys a pass |
| **1** - `q*` -> `q_ref` | Renamed in every live module. **Not blind:** `kairos.legset` uses `q*` for the break-even non-exhaustiveness rate, and a mass rename would have corrupted it - the exact hazard E3 deferred it for |
| **2, 5, 6, 8** | Done by later work six passes ago; the *statuses* were stale, not the work |
| Gate-1 deferral on `baseline.py` | Closed. Look 3 ran the >=1,500-event re-test at 1,966 events and rejected `C_logit`. The module is retained un-exported for reproducibility, **not pending** |
| Discovery breadth (Pass 14's open item) | The scan now sweeps the full reachable open universe from **both ends** of the volume distribution: **2,246 markets / 769 events / 78 groups priced**, against 604 / 74 / 6 before. Still no candidate; closest is **-0.6%** |
| `MAX_CONSECUTIVE_WINDOW_FAILURES` | Raised 3 -> 6, recovering the `2025-07` quarter which 500s at offsets 0-200 and serves normally from 500. **Does not re-open Look 3**, whose dataset is recorded and whose verdict stands |

### Declined, with reason

- **`MarketBaseline` -> `MarketReference` class rename.** Look 3 rejected the hypothesis; the class
  survives only so Gates 1-2a and Looks 1-3 stay reproducible. Renaming a refuted artifact is churn
  that would stale every results doc (C9a).
- **Unifying the two carry models.** Still latent, still masked by spread, still pinned by a
  regression test that fails if the gap widens. Changing `SettlementTerms` would move Gate 1's
  recorded numbers, so the honest state is *pinned*, not *fixed* (E3).
- **Splitting `SettlementTerms` into `settlement.py`.** Five files touched for a naming benefit;
  motivated only if Class B is built out.

### Not resolvable here - named, not hidden

- **Quote persistence.** Nothing models a counterparty withdrawing when hit, which is the usual
  reason a screen-visible arbitrage is not executable. It cannot be measured without placing live
  orders, so it is **Gate 3**, and it gates every candidate this scanner will ever produce.
- **Two permanently-broken quarters** (`2025-10`, `2026-01`) - HTTP 500 at every offset upstream.
  A recorded coverage hole in Look 3's sample, not a fixable defect.
- **Venue-wide open-market discovery.** `offset` caps at 2100 on open markets too; a full sweep
  needs date-windowed discovery, as Look 3 required for closed ones.

### Found by the sweep: a rejected protocol was vetoing Gate 0

`gate0.py` was reporting **FAIL**. The only failing condition was `strat_maxt` at 0.250 power - the
stratified protocol **Gate 0b already rejected**. Meanwhile `kairos`, the pipeline actually in use,
passed at 0.667 against a 0.500 floor with a worst null rate of 0.083.

`strat_maxt` was gated *while the adopt/reject decision was live*, which was right at the time. Once
Gate 0b answered it, leaving it gated meant a protocol deliberately not used was vetoing the verdict
on a different protocol - so Gate 0's headline was false about the thing it exists to certify.

**Demoted to an exhibit, and recorded loudly because the shape of the change resembles A8.** It is
not tuning a falsifier until the system passes: nothing about stratification is rescued, it stays
rejected, its numbers stay printed, and it simply stops gating something it was never about. Gate 0
now reports **PASS** - which is what it reported before `strat_maxt` was ever added.

The general form is worth stating: **a candidate under evaluation should not gate the incumbent.**
Adding a challenger to a gate is how you evaluate it; leaving it there after it loses makes the gate
report on the loser.

### Method note - a stale status is a false claim

Four items (2, 5, 6, 8) read "pending" while the work had been finished six passes earlier, and one
read *"`baseline.py` disabled pending a re-test at >=1,500 events"* after Look 3 had run exactly that
re-test at 1,966 events and rejected it. **A status is a claim about the project's state, and an
unmaintained one is a false claim a future session will act on** - the same failure mode as G8, one
level up from code.

---

## Pass 14 — Depth layer and the first live Class B scan (2026-09-09)

Gate B's depth was synthetic — the one part of the Class B stack with no real data behind it. This
pass replaced it with the real ask book and ran the first live candidate scan. Full result in
[`SCANB-RESULTS.md`](SCANB-RESULTS.md). **No candidate; the binding constraint is structural.**

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 14.1 | "29 of 35 groups were too thin to fill at size" | **Withdrawn — 0 were thin** | The scan merged "book too thin" and "book never loaded" into one counter. Separating them (G5) gave **too thin 0, unfetchable 29**. Read naturally the original says *the venue is illiquid*, which is a claim about the market that was really a claim about our fetching. Caught only because the counters were split |
| 14.2 | The 29 were a fetch failure | **Corrected again — they are untradeable legs** | All 29 were HTTP 404 from `/book`, and every 404 leg has `active=False`. Those legs cannot be bought, so the set cannot be completed and the buy-every-leg identity is unavailable at any price. **Not an apparatus fault — a structural refusal (D1)** |
| 14.3 | `enableOrderBook` / `acceptingOrders` indicate a tradeable leg | **Refuted by measurement** | On every 404 leg both were **True** while `active` was **False**. The two fields whose names mean "you can trade this" are exactly the ones that mislead; `active` is the only predictor |
| 14.4 | Top-of-book is the price you pay | **Refuted** | The CLOB sorts both sides **worst-first**: best ask is `asks[-1]` in 12/12 markets and `asks[0]` in 0/12, where `asks[0]` was 0.999 every time. `kairos.book` normalises once so no consumer rediscovers it |
| 14.5 | A VWAP can be passed to `effective_yes_cost` | **Refuted — double-charges spread** | That method takes a *mid* and adds `half_spread` to model crossing; a VWAP off the asks has already crossed. Added `effective_yes_cost_at`. Not the same as `maker=True`, which suppresses the spread but also swaps in the maker fee — taking the ask is a taker trade (C7) |

### Finding — Class B's constraint is assembly, not price

**82% of live groups (33/40) contain at least one untradeable leg.** Of the 6 that can be completed,
every one costs **3.4%–16.3% more than the $1 it pays**, at real VWAP for 25 contracts a leg.

The tradeable universe is therefore far smaller than the group count suggests: 74 events → 40 groups
of usable size → **6 completable**. Class B is constrained by whether a set can be *assembled*, well
before anything about whether it is *mispriced*.

### Method note — the same defect, three levels deep

G5 was violated at three separate layers in one session: the scanner merged thin-vs-failed;
`fetch_book` returned a bare `None` that erased the reason; and the first diagnostic sampled the
groups that *succeeded* while trying to explain the ones that failed. Each fix revealed that the
previous reading had been wrong, and the sequence of readings was:

> *"the venue is illiquid"* → *"our fetching is broken"* → *"the sets cannot be assembled"*

Only the third is true. The entire distance was covered by refusing to let an error and a
measurement share a counter. `fetch_book_result` now returns a named reason, and `fetch_book` is a
thin wrapper over it.

---

## Pass 13 — Exhaustiveness sample extended 75 -> 512 (2026-09-09)

The lever Pass 12 identified, pulled. Reproduce with `python exhaustiveness.py`.

| | trials | failures | bound (`3/n`) | smallest tradeable edge |
|---|---|---|---|---|
| Pass 12 | 75 | 0 | 0.0400 | ~5% |
| **Pass 13** | **512** | **0** | **0.0059** | **~1%** |

**512 fully-resolved negRisk groups, every one with exactly one winner.** Zero-winner groups 0/512;
multi-winner groups (which would falsify mutual exclusivity in the other direction) 0/512. Cost: 153
seconds of fetching. It moved the tradeable floor from ~5% to ~1%, a larger widening of the Class B
universe than any change to the scanner could produce.

### Survivorship checked before trusting the sample

A group where nothing won might be **voided** rather than resolved, and voided markets report
`["0","0"]` — which the clean-resolution filter drops. That would make the sample structurally
incapable of containing the failures it is looking for, and every number above would be an artefact.

Measured across **4,968 closed negRisk legs: zero voided, zero unparseable, zero settled between the
extremes.** The channel does not exist here. `exhaustiveness.py` re-checks it on every run and
reports the count rather than relying on this note (AXIOMS G5).

### Method notes

- **Three tests failed when the evidence improved, and that was correct.** They asserted "a 2% edge
  is refused", true at 75 trials and false at 512. Rewritten to derive their edges **from the
  measured bound**, so they state the mechanism rather than a constant. Editing the number would
  have silenced the very check they exist for — and a test that must be hand-adjusted every time the
  evidence moves is a test that will eventually be adjusted past a real regression.
- **The constant is now an output, not a literal.** `EXHAUSTIVENESS_TRIALS` was a magic number backed
  by an ad-hoc probe. It is generated by `exhaustiveness.py` and marked regenerate-never-hand-edit,
  because a bound typed in by hand is a trading rule with no evidence behind it.
- **The bound never reaches zero.** `3/n` shrinks but does not vanish, however many groups pass (A6).

---

## Pass 12 — Leg-set verification built (2026-09-08)

Gate B measured that the entire Class B false-positive defence sits **outside** the scanner. This
pass built that layer and measured the threat it defends against. Full result in
[`LEGSET-RESULTS.md`](LEGSET-RESULTS.md).

### Finding 1 — the truncation threat was far larger than the anecdote

Groups assembled the way an offset-paginated scan assembles them, checked against the authoritative
event listing:

| | |
|---|---|
| groups checked | 80 |
| **truncated** | **39 (49%)** |
| legs missing across those | **519 of 865 (60%)** |
| worst case | held **49 of 117** legs |

The census recorded a "53% arbitrage" produced by pagination truncation as a cautionary anecdote.
It is not an anecdote: **half of all groups are truncated, and those are missing three fifths of
their legs.** A group missing 60% of its legs sums 60% too low and presents as a spectacular
arbitrage. A scanner trusting an asserted leg set would not be slightly wrong; it would be wrong
about half the time.

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 12.1 | Exhaustiveness should be required via an explicit `negRiskOther` leg | **Refuted by measurement** | Only **36%** of negRisk events carry one, so the rule discards two thirds of the universe. Measured directly instead: across **75 fully-resolved groups, all 75 had exactly one winner**, including all 54 with no Other leg. Zero-winner groups: **0/75** |
| 12.2 | 0/75 means exhaustiveness is safe | **Refused** | Zero failures in 75 trials bounds the rate at ~**4%** (rule of three), not at zero (A6). And failure costs the **entire stake**, not the edge: break-even is `edge/(edge+stake)`, so **a sub-5% arbitrage is not worth taking** on a group with no Other leg. `exhaustive()` therefore takes the edge as an argument — it is a statement about the trade, not the group |
| 12.3 | `negRiskRequestID` groups markets | **Refuted before use** | It is **per-market**: 2,896 ids across 2,896 markets. Grouping on it yields singletons. One query established this; `negRiskMarketID` (436 groups / 2,896 markets) and event id are the real keys, and **0/70** sampled events spanned more than one group |

### Method notes

- **The authority is cross-checked, not trusted.** `/events/<id>` returns the full leg set, but
  `verify_leg_set` refuses it as non-authoritative if the held set contains a market the event does
  not list. Trusting an endpoint to be complete is the assumption that produced the problem.
- **A guard that asserted a property it could not check.** The first version of the Pass-12
  regression test grepped source text for `negRiskRequestID` near the word "group" — and matched the
  docstring recording the finding. Replaced with an AST walk for actual field reads (`.get(...)`,
  subscript), then negative-tested by re-pointing the grouping code at the wrong field. **AXIOM G7,
  committed while writing the guard for G7.**
- **The lever on Class B's universe is sample size, and it is cheap.** At 300 verified groups with no
  failures the residual bound falls from 4% to 1%, bringing a 2% edge inside tolerance. Extending the
  exhaustiveness sample widens the tradeable universe more than any change to the scanner would.

---

## Pass 11 — Gate B built and run (2026-09-08)

**Outcome: PASS.** Class A is closed (Look 3), so Class B is the only live hypothesis, and step 5 of
the registered execution order plus Decision 001 both name the same next step: its null gate, before
any scanner. Full result in [`GATEB-RESULTS.md`](GATEB-RESULTS.md).

The gate found two defects in itself before it found anything about Class B — which is the gate
working, and both are recorded rather than quietly fixed.

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 11.1 | Gate B's first PASS | **Withdrawn — the control was circular** | The positive control used `inject_arbitrage`, which bisects on `effective_yes_cost` to hit a target post-cost edge — i.e. it was defined by the very formula `scan` applies, so power 1.000 was guaranteed by construction rather than measured. **The same defect as the retracted Gate-2a demo** (Pass 3). Replaced by `obvious_arbitrage`, which scales quotes to a fixed *nominal* sum of 0.70 and never mentions the cost model; the circular version is retained as a labelled exhibit |
| 11.2 | The arbitrage-free worlds test the scanner | **Narrowed — most of them tested a boolean** | `truncated`, `non_exhaustive` and `thin_book` are all rejected by a structural refusal on a flag the world hands the scanner. That is flag-honouring, not detection. Added `marginal` — impeccable structure, unprofitable by exactly 0.005 after costs — so that **the cost arithmetic is the only thing standing between the scanner and a false fire**. It holds at every horizon |

### Finding — a latent inconsistency, found before the scanner existed

The repo holds **two carry models** and they disagree, increasingly with horizon:

| horizon | `SettlementTerms` implied | `CostModel.carry` | gap |
|---|---|---|---|
| 7 d | 0.00115 | 0.00115 | 0.00000 |
| 365 d | 0.05660 | 0.06000 | 0.00340 |
| **730 d** | **0.10714** | **0.12000** | **0.01286** |

One discounts (`1/(1+wt)`), the other is linear (`base·wt`). **1.29 points at two years exceeds a
plausible arbitrage**, at exactly the horizons where negRisk groups are most numerous — the census's
worked example was a *JD Vance 2028* group.

It does **not** currently cause false positives, and Gate B says why: at five legs `N × half_spread`
is 0.025, which swamps it. **The inconsistency is masked by costs, not absent** — a lower-spread
venue or a maker-execution assumption would unmask it.

Deliberately **not** unified (E3): the two models feed different recorded results and changing
`SettlementTerms` would move Gate 1's settlement numbers. The gap is pinned by a regression test
instead, so it cannot widen silently, and the scanner charges carry **once** through
`effective_yes_cost` against a nominal $1 payoff (C7).

### Finding — where the Class B risk actually lives

`truncated_believed` — a genuinely truncated group whose leg set is *asserted* complete — fires
**1.000 at every horizon**, and nothing inside the scanner can prevent it. A leg never seen cannot be
reasoned about.

So the gate's most useful output is a number it deliberately does not gate on: **the entire Class B
false-positive defence rests on leg-set verification upstream**, and this measures how much that
verification is carrying — all of it. Recorded as an exhibit, and as a binding constraint on any
scanner: completeness is a measured property with its own verification, never a field read off a
response.

---

## Pass 10 — What this log says about itself (2026-09-08)

A review of the whole arc, prompted by noticing that a defect recorded in Pass 4 had been committed
again in Pass 9. The findings are about the **project's own failure distribution**, and they changed
the axioms structurally.

### Finding 1 — the discipline was concentrated where the mistakes were not

Classifying every defect recorded during **execution** (Passes 4–9) by what actually went wrong:

| defect class | count | examples |
|---|---|---|
| **Apparatus** — the instrument produced a confident wrong number | **~18** | float-equality on resolutions; `start=None` skipping the carry adjustment; nominal `endDate` reporting 367 days for a 7-day market; a 403 that `curl` answered 200; `fetch_history` handed a dict; unstandardised features diverging to 4.82; `--limit 900` read as a data ceiling; horizon pinned to a constant; missing ceiling guard; aggregate-not-per-unit ceiling guard; a control lacking its own hypothesis; a test checking the wrong property; swallowed 500s read as "no markets"; a cache swept mid-run; a pagination ceiling read as the universe |
| **Inference** — the statistics were wrong | **~3** | selecting on the fit set; significance without materiality; error correlation confounded by anchoring |

**The statistical machinery has not yet returned a wrong answer.** Clustering, the wild bootstrap,
sealed holdouts, max-t multiplicity correction — every one has behaved. The instruments feeding them
have failed roughly six times as often.

Before this pass the axioms held **13 measurement rules and none about the instrument**. That is a
discipline aimed almost entirely at the part of the system that was working. **Group G — Apparatus
validity (G1–G9)** now exists, derived from this count rather than from intuition.

### Finding 2 — an append-only prose log does not prevent recurrence

Pass 4 recorded **G0.2**: a power comparison run inside worlds where the best obtainable result was
itself undetected measures the worlds, not the pipeline. It described the symptom, the diagnosis and
the fix. In Pass 9 the same defect was committed again in a new runner, which announced **"DEAD"**
with every ceiling below the power floor.

The cause was not forgetfulness about the *lesson* — it was that the *fix* had been implemented as
`GateReport.harness_valid`, a property of one class, which a new runner inherits nothing from.

Two changes, both landed:

- [`kairos/validity.py`](../kairos/validity.py) — the rule implemented **once**, callable, with the
  per-unit evaluation that Pass 9's second attempt also got wrong. `gate0b.py` now delegates to it.
- [`tests/test_regressions.py`](../tests/test_regressions.py) — recorded corrections re-expressed as
  executable guards, each naming the pass it came from and encoding the *property* rather than the
  line that was wrong. Its meta-guard fails when a new execution pass is added to this log with
  nothing guarding it; that guard was negative-tested against a synthetic Pass 10 before being
  trusted, and it immediately found three genuine gaps (Passes 5, 6, 7), now closed.

Generalised as **AXIOM G8**: *a correction that is not executable will recur.*

### Finding 3 — a live defect found by the review, with its damage measured

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 10.1 | `fetch_history` returning `[]` on failure is a harmless fallback | **Refuted — it was a permanent silent exclusion** | It caught bare `Exception`, set `hist = []`, and **cached it**. One transient network failure therefore excluded that market from *every subsequent run*, counted as `no_history`, with nothing recording that a fetch had ever failed. An empty cache entry is indistinguishable from a market that genuinely has no CLOB history, so the damage is undetectable case-by-case |

**Exposure measured, not assumed.** 618 of 14,005 cached histories (4.4%) were empty. Sixty were
re-fetched directly, bypassing the cache: **0 came back non-empty.** All sixty are genuinely empty
markets. By the rule of three that caps contamination at ≤5% of the 618 — **≤0.2% of the universe**
— so **no recorded result is affected**. The hazard was real and never fired.

Fixed by retrying and then **not caching the failure**: an empty entry now means *measured* empty.
Generalised as **AXIOM G5**.

### Method note

The one claim in this pass asserted from memory rather than measured — that `replicate.py` imports
`baseline` — was wrong in both directions: it does not, and the consumer that mattered (`census.py`,
Class B) had not been checked at all. Every other finding here came from a count or a probe.

---

## Pass 9 — Looks 2 and 3: the replication (2026-09-08)

**Outcome: Class A forecasting edge REJECTED on 1,966 fresh events.** Full result in
[`LOOK3-RESULTS.md`](LOOK3-RESULTS.md); the withheld intermediate run in
[`LOOK2-RESULTS.md`](LOOK2-RESULTS.md).

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 9.1 | `C_logit` `+0.01341` and `drift` `+0.01193` are effects awaiting confirmation | **Refuted** | On 983 disjoint out-of-sample events: `C_logit` `+0.00371` (**−72%**), `drift` `−0.00051` (**sign reversal**). Both were the maximum of a family selected at `p≈0.11`; both behaved exactly as the registration pre-committed they would |
| 9.2 | "Paginate deeper for more events" (the lever named at the end of Pass 8) | **Refuted — the lever did not exist** | Gamma refuses `offset` ≥ 2100 with HTTP 422 for *every* ordering and silently caps `limit` at 100. `--pages 60` and `--pages 21` return identical data. Look 2's registered *n* was unreachable by Look 2's registered method |
| 9.3 | The Polymarket resolved universe holds ~2,100 markets | **Corrected — it holds at least 26,143** | The ceiling is on *pagination*, not the universe. The same query inside an `end_date_min`/`end_date_max` window gets its own 2100 budget, and adjacent windows overlap by **0**. A quarterly sweep reaches 12× more markets |
| 9.4 | Three quarters of 2025–26 contain no resolved markets | **Corrected — they are HTTP 500 upstream** | An early probe returned `[]` on any error, so three permanently-broken quarters read as "no markets resolved then". `fetch_window` now returns failed offsets alongside markets so a broken window cannot masquerade as an empty one. The nine-month gap is recorded as a limitation |

### Method notes

- **Both pre-registered guards fired, and each by under 0.02pp.** `C_logit` came in at `p = 0.0335`
  against a registered `alpha = 0.025`, and at **0.987%** of the benchmark against a **1.000%**
  materiality floor. Chosen after the fact, either threshold had an easy sincere-sounding case —
  "two tests are really one family", "0.987% rounds to 1%". Both were frozen before the data was
  fetched, and each existed for a reason that predated this run by two gates. **This is the clearest
  demonstration in the project of what pre-registration buys.**
- **A registration can commit to something it should not have.** Look 2's decision rule says
  `baseline.py` is *deleted* on this outcome. **Amended 2026-09-08 — see `PROTOCOL.md` "Amendment".**
  The clause used a **file** as a proxy for a **hypothesis**, and the two do not coincide: the module
  also holds `SettlementTerms`, which `census.py` uses as the **Class B** carry model, and Class B is
  untested rather than refuted. Deletion would have retired a hypothesis nobody had tested and made
  Gates 1–2a and Looks 1–3 unreproducible in a workspace with no version control. Replaced by
  un-exporting the rejected classes from `kairos` plus an allowlist test that fails when a new
  consumer appears. Honouring a registration does not extend to destroying the evidence for its own
  result. Generalised as **AXIOM C9a**.
- **My own dependency claim was wrong, and Phase 1 of the method caught it.** I reported that
  `replicate.py` imports `baseline`. It does not — it imports `_fit_logit` from `gate1`, which
  imports `baseline`. More consequentially, I had not checked `census.py`, which is where the only
  *live* consumer was. E3 says inspect references before acting; the one time I asserted a reference
  set from memory instead of grepping it, I got both halves wrong.
- **The anti-drift guard was negative-tested before being trusted.** A rogue importer was planted in
  `kairos/_drift_probe.py`, the suite was confirmed to fail with it and pass without it, and the
  probe was removed. A gate that has only ever seen good input is an untested gate.
- **The disjointness guard earned its place immediately.** Look #1's cached pages had been swept
  between runs, and pagination drifts as markets resolve, so the reconstruction could easily have
  come back 730 or 733. It returned exactly 731 both times it ran. Had it not, the run would have
  voided itself rather than silently test partially-overlapping data.
- **A transient HTTP 500 killed a 909-event sweep**, and the retry that fixed it had to be careful
  not to retry 422 — which is the legitimate end-of-window signal, not a failure.

---

## Pass 8 — Apparatus audit before choosing what follows Gate 2a (2026-09-08)

Gate 2a closed with *"the next informative move is more events, not more models."* Before acting on
that, the dataset the two gates actually ran on was measured. Three defects, all in the apparatus
rather than in the market, and all invisible from the results tables.

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 8.1 | "731 independent events" is the available sample | **Corrected — the sample was capped, not exhausted** | `--limit 900` capped observations at 900. Removing it yields **820 events at the same 24 h lead** from the same cache, and **921 at a 72 h lead**. ~12% of available Class-A events were discarded by an argument default, and the power arithmetic in `GATE1-RESULTS.md` and `GATE2A-RESULTS.md` was computed against the capped figure |
| 8.2 | Longer horizons would shrink the universe | **Refuted by measurement** | Event yield *rises* with lead time to a peak near 72 h (921 events) before declining at 336 h (779). `min_points=5` was the binding constraint at short leads, not horizon availability |
| 8.3 | The gates measured "the market" | **Narrowed — they measured one point on a curve** | Every gate ran at `lead_hours=24` with daily-fidelity candles, which pins `days_to_resolution` to a median of **1.00** (p90 = 2.00). Horizon was a constant, not a variable. Page et al. and Moshrefi both report the market's calibration is a *function* of time to expiry; the gates sampled one point on it and generalised |
| 8.4 | The log-score benchmark of 0.336 reflects forecasting difficulty | **Corrected — it is diluted by near-resolved rows** | 45% of observations sit below 0.15 or above 0.85, with measured base rates of **0.033** and **0.976**. The market is nearly certain and nearly right there, so those rows contribute almost no information while pulling the mean score difference toward zero. Low effect size and low power are partly an artefact of what is being averaged over |
| 8.5 | "The next informative move is more events" | **Withdrawn as stated** | It presumed the sample was exhausted (8.1) and the design sound (8.3, 8.4). Both are false. The events were there and the design was averaging over a degenerate horizon and a diluted price range |

| 8.6 | The next move is to stratify the test by price band | **Rejected by Gate 0b** | The max-t correction works (null rejection 0.188 → 0.062), but test-only stratification detects *less* than not stratifying — 0.188–0.250 against 0.312–0.375 — and clears no power floor. Rejected before touching real data, which is what A7 is for. [`GATE0B-RESULTS.md`](GATE0B-RESULTS.md) |
| 8.7 | Gate 0b's first "DEAD" verdict | **Withdrawn — unearned** | Ceilings were 0.19–0.38, below the 0.50 floor, so the run compared two instruments inside worlds where neither could succeed. Same defect Gate 0 caught in Pass 4 (finding J), reintroduced by omitting the ceiling guard. Guard added, then corrected again to apply **per world** after `banded:lowmid` (ceiling 0.062) hid behind `banded:highmid` (1.000) |
| 8.8 | `inject_banded_signal` implements the concentrated-edge hypothesis | **Corrected — it did not** | The band was defined on `pi`, but every protocol sees only `market`. At `bias=1.6` a `pi=0.5` contract quotes at **0.83**, indistinguishable from an honest contract worth 0.83 — a signal concentrated in a band nothing could condition on. Band moved to the quoted price; two tests added asserting `stratify_by_price(market)` alone separates biased from honest. **Found by a check that was meant to confirm a diagnosis and refuted it instead**: band dummies scored 0.375 against a smooth price tilt's 0.500, which is impossible if the band is observable |

### Method notes

- **The data cache is volatile, and that is a reproducibility hazard, not an inconvenience.**
  `polymarket.cache_dir()` defaults to `tempfile.gettempdir()/ordo-kairos-cache`. On this machine
  something sweeps `%TEMP%` aggressively — almost certainly the same thing that freed 216 GB between
  sessions. Measured mid-session: `markets/` **gone entirely** and `history/` down from **1,683 files
  to 199**. Consequences, in increasing order of seriousness:
  1. A long fetch can be destroyed while it runs.
  2. **Every gate's exact dataset becomes unreproducible once its pages are swept.** The Gamma API
     paginates `closed=true&order=endDate&ascending=false`, so page *n* today is not page *n*
     yesterday — markets that resolved in between push the window forward. Re-fetching does not
     restore the old sample; it silently returns a different one.
  3. Look #2's registered disjointness rule depends on reconstructing look #1's 731 events from
     those pages. `replicate.py` therefore checks the reconstruction against the recorded count and
     **voids the run** on mismatch rather than proceeding on a partially-overlapping set.
  Mitigation: `ORDO_KAIROS_STATE` set to `<a cache dir outside the repo>`, outside both
  `%TEMP%` and the publish-eligible repo tree.
- **A passing test that checked the wrong property.** `test_the_signal_really_is_concentrated_not_diffuse`
  passed through every version of 8.8. It asserted *how much* of the range was mispriced and never
  that the mispricing was **visible** to anything downstream. A control world can fail to contain its
  own hypothesis while every number it produces looks plausible.
- **The disk-full blocker was stale.** Work was previously reported as constrained by C: at 912 KB
  free. Re-measured: **216 GB free**. Nothing was deleted to achieve that. A blocker is a
  measurement with a timestamp, and re-probing it cost one command — the same rule that caught the
  census's false 403 (Pass 5), applied to a decisive *negative* rather than a decisive positive.
- **A hand-written probe reported zero admissions at every lead time.** The bug was in the probe:
  `fetch_history` takes a token id and was handed a market dict. Caught only because
  `build_dataset` had produced 900 observations from the same cache minutes earlier. Fifth apparatus
  bug in this project to produce a confident, wrong, decisive-looking number.

---

## Pass 7 — Gate 2a run (2026-09-08)

**Outcome: ladder stopped at rung 2.** No leakage-free forecaster beat the market price. Full
result in [`GATE2A-RESULTS.md`](GATE2A-RESULTS.md).

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 7.1 | Forecast-**error** correlation measures ensemble diversity | **Corrected — confounded by anchoring** | For market-anchored models every error is dominated by the shared `q - y` term. Measured ρ(error) = 0.966 → 1.03 effective forecasters, while ρ(tilt) = 0.341 → **1.98**. Error correlation understated diversity ~2×. `tilt_correlations` added; both now reported. Begin et al.'s ρ≈0.70 remains right *for un-anchored* LLM agents — applying it here was a category error |
| 7.2 | Implicit: raw features are fine for a fitted tilt | **REJECTED** | Unstandardised, `maturity` diverged to log score **4.82** vs a 0.336 benchmark. Fixed with train-only standardisation. The fix **reordered every model** (best went `momentum` → `drift`) while leaving the verdict unchanged |
| 7.3 | Gate 2 can be run as one step | **Split** | **2a** = leakage-free deterministic models (done). **2b** = LLM, blocked because these markets resolved inside frontier training windows. Gate 2a does not license 2b: nothing beat the market, so there is no channel to add a model to |

### Convergent evidence, recorded

Gate 1 `C_logit` (+0.01341, p=0.1139) and Gate 2a `drift` (+0.01193, p=0.1174) agree to within 12%
on effect and 0.004 on p, by unrelated routes. Both imply ~1.2–1.3% of log score *may* exist and
that ~366 out-of-sample events cannot resolve it. Both independently size the re-test at
**~1,400–1,900 events**. Under A1 this is "not enough evidence", not "no effect".

### Refactor verification

`nullworld._fit_tilt` now delegates to the shared `forecasters.fit_logit_tilt` (E3, no parallel
implementations). Verified **bit-for-bit identical** to the pre-refactor inline loop across 12
configurations (max |Δ| = 0.000e+00), so Gate 0's recorded result stands without a 25-minute re-run.

---

## Pass 6 — Gate 1 run (2026-09-08)

**Outcome: `q_ref` REJECTED.** No transformation of the market price beat the raw quote out of
sample on 731 independent events. Full result in [`GATE1-RESULTS.md`](GATE1-RESULTS.md).

### Claims withdrawn

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 6.1 | `q_ref` improves on the raw market quote as a probability benchmark | **REJECTED on evidence** | `A_raw` is the Gate-2 benchmark. `baseline.py` is disabled by default and retained only against a named re-test trigger (≥1,500 events); deleting outright would violate A1, since `C_logit` was *underpowered* (p≈0.11 on a materially sized +0.0134), not disproven |
| 6.2 | Isotonic recalibration is a reasonable default family | **REJECTED** | `C_iso` scored **−0.039** vs raw — the worst of five and worse than the logistic form on identical data. Isotonic overfits here. Logistic wins the family question decisively |
| 6.3 | Implicit: "statistical significance identifies a survivor" | **Rule corrected** | `B_settle` was selected on **p = 0.0005** for a **+0.00008 nat** gain (0.02% of benchmark), then failed the sealed holdout at p = 0.3258. A tiny deterministic monotone transform produces near-zero variance in paired differences, so trivial effects are easy to detect. Survivors must now clear **significance AND materiality** (≥1% of benchmark log score) |

### On the mid-run rule change

`MIN_RELATIVE_GAIN` was added *after* seeing run 1. That is a forking path unless handled openly, so:
both runs are on record, and **the change does not alter the verdict** — with the threshold applied
`B_settle` fails materiality, `C_logit`/`D_both` already failed significance, no survivors remain,
and `A_raw` wins either way. Verified by re-running against the warm cache, not asserted.

### Recorded scope limit, not a finding

**Gate 1 did not test the settlement adjustment.** Median admitted market life is ~7 days, where the
wedge is ~0.11% — which is exactly why `B_settle` moved the score by 0.02%. Testing it requires
long-dated resolved contracts. Nothing here refutes Gebele & Matthes.

---

## Pass 5 — Feasibility census and Decision 001 (2026-09-08)

Full result in [`CENSUS-RESULTS.md`](CENSUS-RESULTS.md). **Decision: Gate 1 on Class A; Class B held
behind its own null gate.**

### Claims withdrawn or corrected

| # | Claim | Verdict | Replacement |
|---|---|---|---|
| 5.1 | Implicit: "data access is the constraint on Stage 0" | **Refuted** | All three venue APIs return 200 without auth. 877 independent events per 1,000-market page against a 300 requirement. Supply is not the constraint; **usable price-history density** is |
| 5.2 | Implicit: "Class B is deterministic, so it escapes the sample-size problem" | **Refuted** | Class B's problem is *identification*, not statistics, and it is worse. Three independent false-positive sources found in one afternoon: pagination truncation (a fake **53%** arbitrage), settlement carry (a fake 7–10% edge whose **sign reverses** once adjusted), and unstated group exhaustiveness |
| 5.3 | "Class B can be scanned before it is gated" | **Rejected** | Constraint introduced: no Class B scanner until a Class-B null gate exists on Gate-0 terms (AXIOMS A7) |

### Apparatus bugs found in the census itself

Four, each producing a confident wrong number: exact-equality on float resolutions (reported **0%
resolved**); a `None` start date (carry adjustment **silently never ran**); nominal vs actual horizon
(**367 days** reported for a market that traded **7 days**); and a `urllib` **403** on a host `curl`
had already reached, which would have recorded "price history unavailable" and killed Class A on a
false blocker.

**Rule extracted:** a Phase-1 probe is an apparatus and must be negative-tested like any gate. When a
probe returns a decisive-looking *negative*, re-probe with a second method before it enters the
decision — a false blocker eliminates candidates silently and nothing later re-opens them.

---

## Pass 4 — Gate 0 built and run (2026-09-08)

**Outcome: PASS** (worst null rate 0.067, power 0.667 against an oracle ceiling of 0.767). Full result and limitations in [`GATE0-RESULTS.md`](GATE0-RESULTS.md).

The null-world harness found three defects **before** any real data was touched. That is the gate
working as designed; each is recorded here rather than quietly fixed.

### G0.1 — Selecting on the fit set is broken

**Symptom.** The sealed protocol had **zero power** on every positive control, including one that
the in-sample protocol detected 100% of the time.

**Cause.** The first implementation split dev/holdout and then chose the best candidate by its
score *on the data it was fitted to*. An overfit noise candidate always wins that comparison, so
selection reliably picked the worst generaliser.

**Fix.** A three-way split by event — **fit / select / sealed holdout** — matching the
development → validation → sealed-holdout ladder already registered in `PROTOCOL.md` but not
implemented. Selection now happens on data the candidate has not seen.

**Note on A8.** Fixing the *pipeline* when the gate exposes a flaw is what Gate 0 is for. Tuning
the *null worlds* to make a broken pipeline pass is what A8 forbids. Only the former happened.

### G0.2 — The harness was undersized, which is not the same as the pipeline being inert

**Symptom.** Even after G0.1, power stayed at zero. It would have been easy — and wrong — to
conclude the pipeline could not detect anything.

**Diagnosis.** An **oracle** forecaster, built from the world's own generating parameters and
therefore unbeatable, was also undetectable at that sample size. The ceiling was zero, so the
pipeline's zero said nothing about the pipeline.

**Fix.** The oracle ceiling is now measured inside the harness on every positive control and
reported alongside Kairos's own power. When the oracle fails, the report says
`HARNESS UNDERPOWERED` and explicitly declines to draw a conclusion about the pipeline. World size
was raised from 60 to 750 events on the strength of the measurement below, not a guess.

### G0.3 — **The sample-size finding.** Detecting a market-relative edge needs hundreds of events

Measured oracle power against a heavily compressed market, one-sided `alpha = 0.05`:

| independent events | 20 | 40 | 80 | 160 | 320 | 640 |
|---|---|---|---|---|---|---|
| oracle power | 0.183 | 0.333 | 0.500 | 0.667 | **0.933** | 1.000 |

This is the most consequential output of the gate so far, and it constrains the whole programme:

- **Any evaluation set below ~300 independent events cannot support a fund/kill decision on the
  forecasting hypothesis**, no matter how many contract rows it contains.
- It is an upper bound in two ways: the control's edge is far larger than a realistic one, and the
  oracle is unbeatable. A realistic forecaster with a realistic edge needs **more**.
- It converts AXIOMS C3 from a principle into a number, and it feeds directly into `PROTOCOL.md`
  Gate 2 sizing.

### Recorded, not yet acted on

- The `naive` protocol's false-positive rate is catastrophic (26/30 on a provably null world in the
  first completed cell). This is an *exhibit*, deliberately retained: it is the empirical case for
  AXIOMS C3, C5 and C6, measured against our own code rather than asserted from papers.
- `cluster` (correct inference, in-sample selection) sits above nominal alpha. Correct inference
  alone does not fix selection bias.

---

## Pass 3 — Second contrarian review (2026-09-08)

Verdict: **the core project survives**; the corrections are about stopping the validation framework
from fooling itself. The single largest error was granting `q*` epistemic privilege it has not
earned.

### Claims withdrawn

| # | Claim as shipped | Verdict | Replacement |
|---|---|---|---|
| 3.1 | `q*` is the "fair probability" / "the market's actual belief" | **Retracted** | It is an *estimated benchmark*: the best frozen OOS probability benchmark constructible from market information at decision time. Prediction-market prices converge to different weighted means of participants' beliefs depending on utility and trading order (Yu et al. 2022) — there is no unique recoverable belief. See AXIOMS A2 |
| 3.2 | "Settlement undiscounting is arithmetic, not estimation" | **Retracted** | Applying a *known* wedge is arithmetic. Obtaining the correct wedge is estimation, and it is maturity-dependent, time-varying, and altered by market architecture (Gebele & Matthes 2026). It must earn inclusion via OOS ablation |
| 3.3 | "Applying settlement before recalibration means the corrections can't double-count" | **Retracted** | Sequential code order prevents ambiguity in execution order. It does **not** establish statistical orthogonality — the recalibration can still learn a distortion correlated with settlement horizon. Only the Gate-1 ablation settles it. See AXIOMS C7 |
| 3.4 | The demo's `+0.0000` vs `−0.0430` as "the number that justifies the repo" | **Retracted as evidence** | `MarketBaseline` was fitted on the same synthetic prices/outcomes it was then scored against. That is an in-sample functional demonstration and nothing more. See AXIOMS A5. Retained, relabelled, as a unit demo |
| 3.5 | "Hindcast is the `q*` comparison as an evaluation protocol" | **Retracted** | Hindcast scores against the **market price at `t₀`** — raw `q`, not our transformation. This is *useful*: it is an independent third-party baseline against raw `q`. Do not contaminate it |
| 3.6 | "Pure arbitrage" excluded as a class | **Retracted** | Invalid generalisation from one retail-scale NBA study. Structural, protocol/NegRisk, and cross-venue semantic arbitrage are separate classes with independent evidence (≈$40M historical extraction; ≈$1.12M protocol-executable; persistent 2–4% execution-aware cross-venue deviations) |
| 3.7 | "Independent LLM ensemble" | **Retracted** | Independence is a measurement, not a naming convention. Pairwise forecast-error ρ ≈ 0.70 for aligned agents; ten agents ≈ 1.4 effective independent forecasters (Begin et al. 2026). See AXIOMS C8 |
| 3.8 | `DSR > 0` as an independent universal pass condition | **Downgraded** | Secondary diagnostic. The project's actual hypothesis is a paired forecast-comparison, which needs dependence-aware inference on score differences, not a Sharpe statistic |
| 3.9 | `effective_sample_size()` feeding significance | **Downgraded** | Planning/eligibility heuristic only. The ρ=1 formula assumes a specific dependence structure, ignores unequal cluster sizes, and cannot see cross-event dependence through shared news regimes, participants or liquidity shocks. See AXIOMS C4 |
| 3.10 | 100× manipulation-cost multiple | **Rejected as a production rule** | An arbitrary safety factor standing in for an unmeasured quantity. A manipulator's payoff is not bounded by *our* position — it can include positions elsewhere and in the underlying. Replace with unconditional fail-closed until an externally grounded model exists. See AXIOMS A6, D4 |
| 3.11 | PredictionMarketBench as general execution validator | **Narrowed** | Four Kalshi episodes. Integration test, execution-replay smoke test, and reference implementation for maker/taker/fill/settlement semantics — not a certifier for other venues or categories |
| 3.12 | "LLMs cannot forecast" (implicit in Pass 2's framing) | **Retracted** | PolyBench: two of seven models profitable on timestamp-locked data. Forecasting competence is a per-model empirical hypothesis; only execution *discretion* is eliminated unconditionally |

### Corrective instruction status

| # | Instruction | Status |
|---|---|---|
| 1 | Demote `q*` to an estimated benchmark (`q_ref` / `MarketReference`) | **Resolved 2026-09-09.** Symbol rename done in every live module. **Not** blind: `kairos.legset` uses `q*` for the break-even non-exhaustiveness rate — unrelated — and a mass rename would have corrupted it (E3). The **class** rename is *declined*, not deferred: `MarketBaseline` is a Look-3-rejected hypothesis retained only for reproducibility, and renaming a refuted artifact is churn that would stale every results doc (C9a) |
| 2 | Separate informational benchmarking from execution economics | **Done.** `score`/`inference` carry the informational test; `costs`/`economics`/`sizing` carry execution. Verified by the C7 double-charge guards: carry is charged once (`effective_yes_cost`), and a crossed price uses `effective_yes_cost_at` |
| 3 | Remove "arithmetic, not estimation"; add the 4-way ablation | **Done** in `baseline.py`; ablation registered as PROTOCOL Gate 1 |
| 4 | Correct the synthetic `q*` demo caption | **Done** in `demo.py` and `README.md` |
| 5 | Cross-fit every learned baseline; sealed single-query final holdout | **Done.** Rolling expanding-window folds in `gate1.py`/`gate2.py`/`replicate.py`; sealed holdout queried once and, in Looks 2 and 3, correctly **not** queried because nothing earned it |
| 6 | Null-world meta-gate before alpha search | **Done and passed** — Gate 0 for Class A, Gate 0b for the stratified variant (rejected), Gate B for Class B |
| 7 | Downgrade `effective_sample_size()` to planning | **Done** in docstring; AXIOMS C4 |
| 8 | Log score primary, DSR secondary | **Done.** Every gate and look decides on the log score via `superiority_test`; DSR remains in `score.py` as a secondary diagnostic and has decided nothing |
| 9 | Stop calling the ensemble independent; measure ρ | **Done** in docs; sub-protocol in Gate 2 |
| 10 | `economics.py` = Level-0 screen; no naive annualisation | **Done** in docstring and docs; profit-vs-size curve deferred until a candidate requires it |
| 11 | Simplify the manipulation gate to unconditional fail-closed | **Resolved 2026-09-09.** The size-scaled threshold is gone, `min_manipulation_cost_multiple` deleted from `GateConfig`. A price-settled market is refused unconditionally unless an `external_manipulation_analysis` is attached — a human-written string, deliberately not computable. Six tests, including that a $1bn measured cost no longer buys a pass |
| 12 | Re-open structural arbitrage as a candidate class | **Done** — Class B in PROTOCOL §0 |
| 13 | Correct the Hindcast statement | **Done** in `SPEC.md` |
| 14 | Narrow PredictionMarketBench's role | **Done** in `SPEC.md`, EVIDENCE §7 |
| 15 | Freeze feature work and run the system | **Adopted** as AXIOMS E2 and the PROTOCOL execution order |

### Standing note on scope

At 3,117 lines and 101 tests, this project has not yet demonstrated one real out-of-sample edge.
More architecture is becoming the thing the project was created to avoid. Nothing new is built until
Gate 0 has run.

---

## Pass 2 — First contrarian review (2026-09-08)

| # | Claim as shipped | Verdict | Replacement |
|---|---|---|---|
| 2.1 | "Sizing is the principal cause of PnL" | **Retracted** | Sizing governs the wealth path *conditional on* an edge; it cannot create one. AXIOMS B1, B2 |
| 2.2 | Walsh & Joshi "+34.69% vs −35.17%" as a foundational number | **Magnitude retracted** | Three versions, three magnitudes, then a 2025 corrigendum recording implementation errors. Direction retained on independent sources (Hubáček 2019, Wunderlich 2026). AXIOMS A4 |
| 2.3 | Raw `q` as the skill baseline | **Superseded** | A friction-adjusted benchmark is required — though see 3.1: it is an estimator, not truth |
| 2.4 | "30 days determines fund/kill" | **Retracted** | Elapsed time is not evidence. The unit is independent informational trials |
| 2.5 | Half-spread + fees + wedge as adequate cost representation | **Narrowed** | A conservative screen for killing candidates, never a validator. AXIOMS D6 |
| 2.6 | 5-minute BTC as the exclusion | **Generalised** | The manipulability of the settlement reference is the disease; the horizon is a symptom. AXIOMS D4 |
| 2.7 | "Maximize speed of execution" (original brief) | **Inverted** | Maximise speed of *falsification*. AXIOMS B4 |

---

## Pass 1 — Initial design (2026-09-08)

Original brief: *"design, spec and plan this out for maximizing speed of execution and
maximizing profitability."* The literature inverted the first half of that brief before any code was
written, and the resulting design — LLM as researcher, deterministic evaluator, abstain by default,
kill as the null decision — has survived two contrarian passes unchanged in its core.
