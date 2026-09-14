# Ordo Kairos — Pre-Registered Protocol

Written **before** Stage 0 runs. Changing anything here after seeing a result is a new trial and
must be recorded in [`CORRECTIONS.md`](CORRECTIONS.md) with a reason. Governed by
[`AXIOMS.md`](AXIOMS.md); evidence in [`EVIDENCE.md`](EVIDENCE.md).

Registered 2026-09-08.

---

## 0. Pre-registered decisions (frozen)

| Decision | Value | Axiom |
|---|---|---|
| Primary scoring rule | **Log score** | C1 |
| Primary hypothesis | `E[logscore(p, y) − logscore(q_ref, y)] > 0` | C1, B1 |
| Primary inference | Paired score differences, block/cluster bootstrap at the event level; wild-cluster bootstrap when clusters are few | C4 |
| Secondary diagnostics | Brier + calibration/refinement decomposition, reliability, DSR | C1 |
| ROI | Reported, never selected on | C2 |
| Null action | Abstain | A1 |
| Null decision | Kill | A1 |
| Final holdout | Sealed; queried **once**, after everything is frozen | C6 |
| Materiality floor | `MIN_RELATIVE_GAIN = 0.01` of the benchmark, **and** significance | C1 |
| Re-testing a hypothesis on more data | Alpha-spending registered **before** the run — see below | C5, A8 |

### Re-tests are second looks, and must be registered as such

Gates 1 and 2a are **look #1** on the hypothesis "something beats the raw market price." They
returned `+0.0134` at `p=0.114` and `+0.0119` at `p=0.117` — the shape that most tempts a re-test on
more data. Re-running the same test on a superset of the same markets at nominal `alpha` is **look
#2 reported as if it were the first**, and inflates the false-positive rate by construction.
Alpha-spending controls this even when the number and timing of looks was never fixed in advance
(DeMets & Lan 1994; Lakens et al. 2021), so the absence of an original schedule is not an excuse.

**Binding rules for any re-test:**

1. The spending schedule is written into this file **before** the data is assembled, not after.
2. The observed effect from look #1 is an **upper bound** on the true effect, never the planning
   value. It is the maximum of 5 baselines (Gate 1) or 4 forecasters (Gate 2a), so it carries a
   selection filter; at the power these gates ran at, selected estimates are substantially inflated
   (Jaksic et al. 2026). A sample size derived from `+0.012` is optimistic and must be stated as
   such.
3. The materiality floor applies unchanged. Significance without materiality is not a finding — that
   is what Gate 1 established when `B_settle` won at `p=0.0005` on 0.02% of the benchmark.

---

## Look 2 — Replication on disjoint events

> **REGISTERED 2026-09-08, before any new data was fetched.** Everything below was frozen while the
> only data on disk was look #1's 20 cached pages. Run with `python replicate.py`.
>
> **STATUS: RUN 2026-09-08 — WITHHELD.** 115 fresh events against a registered requirement of 700.
> The cause is an apparatus ceiling, not a shortage of markets: Gamma refuses `offset` past 2100 for
> every ordering. Superseded by Look 3. See [`LOOK2-RESULTS.md`](LOOK2-RESULTS.md).

### Why this is a replication and not an alpha-spent second look

The natural instinct is a group-sequential design: treat look #1 as an interim analysis at
information fraction `t₁ = 731/N` and spend the remaining alpha at look #2. **That is not available
here, and claiming it would be the exact post-hoc move A8 forbids.** Look #1 was conducted at the
full nominal `alpha = 0.05` with no registered boundary. A spending function assigns alpha to looks
*in advance*; retrofitting an O'Brien–Fleming boundary — which happens to spend almost nothing early
and would therefore leave nearly all of the 0.05 available now — is choosing the schedule after
seeing that the first look failed. There is no honest schedule that leaves look #2 anything, because
look #1 already had permission to reject at 0.05 and did not.

So the accumulating-data framing is abandoned. **Look #2 tests on events that were not in look #1
at all.** A test on disjoint data is a genuine independent replication: no alpha is shared, none
needs to be spent, and the full `alpha = 0.05` is available because this is the first time these
observations have ever been tested.

### Frozen design

| Decision | Value | Why this and not otherwise |
|---|---|---|
| **Lead time** | `lead_hours = 24`, **identical to look #1** | 72 h yields ~12% more events, but changing it makes look #2 a *different experiment* rather than a replication, and destroys the ability to say the look-#1 effect did or did not reproduce. Horizon variation is a separate future experiment and is **not** folded into this one |
| **Row cap** | none (`--limit` removed) | The cap was an argument default that discarded ~12% of available events (Correction 8.1) |
| **Pagination** | `--pages 60` (40 pages deeper than look #1) | Fixed **now**, before seeing any yield. Pages are ordered newest-first, so the new pages are older markets |
| **Test set** | **only** events whose `cluster_id` is absent from look #1's 731 | Enforced in code by set difference against a recomputed look-#1 event set, not by assumption |
| **Look #1 events** | excluded entirely — not test data, not training data | They are temporally *newer* than the fresh set, so using them to train a model tested on older events would leak the future |
| **Splits** | rolling temporal splits and a sealed holdout **internal to the fresh set**, same construction as look #1 | Fresh set is self-contained; sealed holdout queried once (C6) |
| **alpha** | 0.05 one-sided, split Bonferroni across 2 pre-specified tests → **0.025 each** | Two look-#1 near-misses are carried forward; testing both at 0.05 doubles the error rate |
| **Materiality** | `MIN_RELATIVE_GAIN = 0.01` of benchmark, unchanged | C1 |
| **Benchmark** | raw market price `q` | Gate 1 rejected `q_ref` |

### The two pre-specified tests, named before the run

1. **H1 — `C_logit`.** Logistic recalibration of the market price in logit space, cross-fitted.
   Look #1: `+0.01341`, `p = 0.1139`.
2. **H2 — `drift`.** The `drift_per_day` price-path forecaster, train-only standardised.
   Look #1: `+0.01193`, `p = 0.1174`.

**No other model is tested.** The full Gate-1 baseline family and the full Gate-2a ladder are *not*
re-run as tests — running 5 + 4 models and reporting the best is the search that made look #1's
effect an upper bound in the first place. Others may be reported as descriptive context, explicitly
labelled non-inferential.

### Pre-committed expectation about magnitude

Look #1's `+0.012` to `+0.013` is the **maximum of 5 baselines and of 4 forecasters** respectively,
measured at low power. Selected estimates under those conditions are substantially inflated
(Jaksic et al. 2026; Gelman & Carlin 2014), so **the replication is expected to show a smaller
effect than look #1, and a smaller effect is not evidence that the method failed.** It is evidence
about magnitude. This is recorded now so it cannot be offered as an excuse afterwards.

### Stopping rule for data collection — binding

Fetch to `--pages 60` and stop. **Do not fetch further because the result was not significant.**
If the fresh set yields fewer than **700 independent events**, the shortfall is reported with an
explicit power statement and the run proceeds anyway; under A1 that is *"not enough evidence"*, never
*"no effect"*. Continuing to collect until a p-value cooperates is optional stopping by another name.

### Decision rule — written before the numbers

| Outcome | Action |
|---|---|
| Either test significant at 0.025 **and** material | That hypothesis proceeds to Gate 3 (execution realism). The other does not, whatever it scored |
| Both fail, fresh events ≥ 700 | **Class A forecasting edge is rejected at this venue and scale.** ~~`baseline.py` is deleted rather than disabled.~~ **See the amendment below.** No further model work on Polymarket resolved markets |
| Both fail, fresh events < 700 | Underpowered. Verdict withheld. The honest next move is a different venue or a forward paper test, **not** another re-test of the same universe |

### Amendment 2026-09-08 — "delete `baseline.py`" replaced, and why

The decision rule above committed to deleting `baseline.py`. **That clause used a *file* as a proxy
for a *hypothesis*, and the two do not coincide.** Verified before acting:

| component in `baseline.py` | status | live consumer |
|---|---|---|
| `LogitRecalibration` | **REJECTED** — it *is* `C_logit` | `gate1._fit_logit`, reached by `replicate.py` |
| `MarketBaseline` | rejected at Gate 1 (`D_both`) | `gate1._fit_both`, `demo.py` |
| `SettlementTerms` | **ALIVE** | **`census.py` — the Class B carry model**, where it reverses the sign on every long-dated negRisk group |

Deleting the file would therefore have (a) removed a working component of **Class B, which Look 3
never tested and which is untested rather than refuted**, and (b) made Gates 1–2a and Looks 1–3
unreproducible — in a workspace that is not a git repository, so irreversibly. A result whose code
has been deleted is an assertion, not a result.

**What replaces it.** The rejection is enforced where it actually bites, and by a test rather than
by prose (prose does not survive a future session):

1. `LogitRecalibration` and `MarketBaseline` are removed from `kairos.__all__` and from the package
   namespace. They remain importable from `kairos.baseline` for the scripts that reproduce recorded
   results.
2. `SettlementTerms` stays exported, explicitly because Class B uses it — not because Class A
   rescued it.
3. `tests/test_baseline.py::TestRejectedHypothesisIsContained` asserts the rejected names are absent
   from the package surface, that the settlement model is still present, that the retained code
   still runs, and that **no file outside a named allowlist imports a rejected class**. The last one
   is the anti-drift guard, and it was negative-tested against a deliberately planted rogue importer
   before being trusted.

**This amendment does not touch the verdict, the alpha, the materiality floor, or the two
hypotheses.** It changes only the disposition of code after the verdict, and it is recorded here
rather than applied silently because amending a registration after seeing its result is exactly the
move that needs a paper trail.

**General rule extracted (AXIOMS C9 clarification):** a decision rule must name the *hypothesis* it
retires and the *path* it retires it from. Naming a file is a proxy that fails whenever one module
serves two hypothesis classes.

---

## Look 3 — the same replication, on a universe offset pagination could not reach

> **REGISTERED 2026-09-08, before any windowed market data was fetched.** Frozen while the only
> outcome-bearing data on disk was look #1's 731 events and look #2's 115.
> Run with `python replicate.py --windowed`.
>
> **STATUS: RUN 2026-09-08 — NEITHER HYPOTHESIS REPLICATED. Class A forecasting edge REJECTED.**
> 1,966 fresh events, 983 tested out of sample. `C_logit` `+0.00371` (p=0.0335, 0.987% of benchmark)
> failed both the registered `alpha = 0.025` and the 1% materiality floor, each by under 0.02pp;
> `drift` reversed sign to `−0.00051`. Look #1's effects shrank 72% and 104% respectively, exactly
> as pre-committed. Sealed holdout **not** queried. See [`LOOK3-RESULTS.md`](LOOK3-RESULTS.md).

### Why Look 2 could not answer, and why this is not optional stopping

Look 2 ran exactly as registered and returned **WITHHELD**: it needed 700 fresh events and the
universe yielded **115**. The cause is an apparatus ceiling, measured afterwards against the live
API with a second method:

| probe | result |
|---|---|
| `offset` = 1900, 2000 | 100 markets each |
| `offset` ≥ 2100, **every** ordering, with and without `order` | **HTTP 422** |
| `limit` = 500, `limit` = 1000 | silently capped at 100 |
| the same query inside an `end_date_min`/`end_date_max` window | **its own 2100 budget** |
| two adjacent quarterly windows | **overlap = 0 markets** |
| quarterly sweep, 2021–2026 | **26,143 resolved markets** vs 2,100 |

So `--pages 60` and `--pages 21` return identical data, and Look 2's registered sample size was
never reachable by the method it registered. **This is not "fetch more because the p-value
disappointed."** The stopping rule exists to forbid collecting until significance; what happened is
that the retrieval mechanism could not deliver the pre-registered *n*, which is an apparatus defect,
and it is diagnosed and fixed before the target is changed. The target is not being changed.

### Frozen design — inherits Look 2 unchanged except where stated

| Decision | Value |
|---|---|
| **Retrieval** | quarterly `end_date_min`/`end_date_max` windows, swept **newest-first**, `fetch_resolved_markets_windowed` |
| **Window order** | chronological, newest first. **Not** "windows with the most markets" — that would select windows on a property of the sample |
| **Excluded events** | **all 846 already seen** — look #1's 731 *and* look #2's 115. Look #2's numbers have been read, so those events are spent |
| **Stopping** | sweep windows in the registered order until **1,500 fresh events** are admitted, then stop. Chosen because Gates 1 and 2a independently sized the re-test at 1,400–1,900 events, not because of any Look-2 result |
| Lead time, alpha, materiality, the two hypotheses, splits | **unchanged from Look 2** |

**The stopping count is a sample-size target, not a significance target.** It is fixed here, before
the data exists, and the run stops when it is met whatever the p-values are doing. If the sweep
exhausts all 24 windows below 1,500 fresh events, the verdict is WITHHELD again and the registered
next move stands: a different venue or a forward paper test.

### What Look 2's numbers may and may not be used for

Look 2 measured `C_logit +0.02468 (p=0.3928)` and `drift +0.05338 (p=0.0915)` on 115 events. These
are **not** evidence and **not** a planning input:

- They are outcome data that has now been seen, so those 115 events are excluded from Look 3
  entirely — reusing them would make Look 3 a second look on part of its own sample.
- They must not be offered as "encouraging". At 115 events the estimate is enormously noisy, and it
  is the larger of two, so it carries the same selection inflation already registered against look
  #1's `+0.012` (A1, and Jaksic et al. 2026).

Two hypothesis classes run in parallel against the same evidence machinery. They are **not** ranked
theoretically — they compete (E4).

- **Class A — Forecasting edge.** Can a forecaster add information beyond `q_ref`? Prioritise
  **early, high-uncertainty markets**, where TimeSeek finds LLMs relatively most competitive and
  where the market's own aggregation is slowest.
- **Class B — Structural edge.** Can a language model discover semantic/payoff relationships across
  contracts that deterministic code then *proves* mispriced and executable? This uses the LLM's
  comparative advantage — language and relationship discovery — rather than asking it to be a
  superior probabilistic trader. The LLM proposes; deterministic code verifies payoff identity,
  book depth, and executable profit, and decides (D5).

---

## Gate 0 — Null-world falsification of Kairos itself

> **STATUS: PASSED 2026-09-08.** Worst null rejection rate 0.067 against nominal 0.05; power 0.667 on the strong control against an oracle ceiling of 0.767. See [`GATE0-RESULTS.md`](GATE0-RESULTS.md) for the full table and its limitations.

**This ranks above all strategy discovery (A7).** Before asking whether Kairos can find an edge,
ask whether it can correctly find *nothing*.

Run the **complete** research workflow — including any LLM mutation/research loop — against:

- martingale / zero-predictability synthetic markets
- shuffled outcomes
- time-shifted information
- irrelevant and pure-noise features
- microstructure placebos with realistic noise
- synthetic fair markets

**Pass — both conditions:**

1. **False positives.** No null world's rejection rate exceeds what chance allows at `alpha`,
   judged by the exact binomial tail rather than an invented tolerance.
2. **Power.** The strong positive control is detected at least `POWER_FLOOR` of the time. A pipeline
   that never reports an edge passes condition 1 trivially while being useless.

**Fail:** if Kairos repeatedly produces statistically convincing "alpha" where none exists, **the
research pipeline is falsified and Stage 0 stops.** Fix the pipeline. Do **not** tune the null
worlds until it passes (A8).

**The oracle ceiling.** Every positive control is also run through an *oracle* forecaster built from
the world's own generating parameters. No method can beat it, so its detection rate is the power
ceiling at that sample size. This is what separates the two possible causes of a power failure:

- oracle detected, Kairos not → **the pipeline is inert.** Fix the pipeline.
- oracle also not detected → **the sample is too small.** Gather more events. Saying anything about
  the pipeline from this case would be an error (A1: "not enough evidence" ≠ "no edge").

**Measured sample requirement (Gate 0 run, 2026-09-08).** Oracle power against a heavily compressed
market, one-sided `alpha=0.05`:

| independent events | 20 | 40 | 80 | 160 | 320 | 640 |
|---|---|---|---|---|---|---|
| oracle power | 0.183 | 0.333 | 0.500 | 0.667 | **0.933** | 1.000 |

**A market-relative forecasting edge needs hundreds of independent events to detect — not dozens.**
This is a hard constraint on Gate 2 and on Stage 0's feasibility, and it was not visible before the
harness was built. Any evaluation set below ~300 independent events cannot support a fund/kill
decision on Class A, however many contract rows it contains.

### Gate 0b — the stratified protocol (pre-registration, written before the run)

> **STATUS: RUN 2026-09-08 — test-only stratification REJECTED.** The max-t correction passed
> (uncorrected search rejects a true null at 0.188 against nominal 0.05; corrected 0.062), but the
> protocol detects **less** than not stratifying on both signal shapes and clears no power floor.
> No stratified result may be reported from real data. The fit-level variant is untested and is not
> being built. See [`GATE0B-RESULTS.md`](GATE0B-RESULTS.md).

Gates 1 and 2a both tested a **single average over the whole sample**. The favourite-longshot
literature says the market's error is not uniform across price, and Page et al. say it is not
uniform across time-to-expiry either. Testing inside strata is therefore a live candidate — and it
is also a *search*, so it needs its own Gate 0 before it may touch real data (A7).

**Frozen before any stratified result was seen:**

- **Price bands.** `longshot [0.02,0.15) · lowmid [0.15,0.40) · mid [0.40,0.60) · highmid
  [0.60,0.85) · favourite [0.85,0.98)`, in `kairos.nullworld.PRICE_STRATA`. Taken from where the
  published bias claims live, not from our data. **Moving a boundary after seeing a result converts
  the test into a search over cut points, which the correction below does not cover** (A8, C7).
- **Minimum stratum size.** 20 independent events. Below that the stratum is excluded before
  anything is computed, and the exclusion is reported (`MIN_STRATUM_CLUSTERS`).
- **Correction.** Max-t against a shared cluster resample (`inference.max_statistic_test`). One
  resample per replicate, every stratum recomputed on it, so the correlation between strata is
  preserved rather than assumed. Studentised, because comparing raw means hands the maximum to the
  smallest stratum by construction.
- **Gate condition.** `strat_maxt` is gated on false-positive rate **and** power. A correction that
  restores the rejection rate by making the test unable to detect anything has not fixed the search.

**Both null-world questions must be answered, and the second is the one that decides it:**

1. Does the correction control the false-positive rate? *(measured: yes)*
2. Does stratifying detect more than not stratifying — on a signal of the shape the hypothesis
   actually posits, i.e. **concentrated in one band**? `inject_signal` misprices at every price, so
   it can only answer this for a diffuse edge. `inject_banded_signal` exists for the concentrated
   case and `gate0b.py` runs the comparison.

**A stratified result on real data is admissible only if `strat_maxt` clears both conditions.**
If it wins on concentrated signal and loses on diffuse, the protocol choice is a *bet on the shape
of the signal* and must be registered here before the run, not chosen once the answer is visible.

---

## Gate B — Null-world falsification of the Class B pipeline

> **STATUS: PASSED 2026-09-08.** Fire rate **0.000** across six arbitrage-free worlds × five horizons
> (1,000 groups each); the independent positive control detected at **1.000**. The naive scanner
> fires at up to **1.000** in the same worlds. See [`GATEB-RESULTS.md`](GATEB-RESULTS.md).

Gate 0 asks whether the pipeline invents *forecasting skill*. Gate B asks whether it invents
*riskless profit*, which requires no forecasting to be wrong about — a different failure mode, so a
different gate. `docs/CENSUS-RESULTS.md` **Decision 001** held Class B behind it because its
false-positive mode was **unmeasured and severe** (A7).

**Arbitrage-free worlds, all of them:** fair groups at 7 d–2 y; fair + quote noise; truncated leg
sets; non-exhaustive outcome spaces; real edges on an unfillable book; and a **marginal** group
unprofitable by exactly 0.005 after costs.

**The marginal world is the one that matters.** Every other null is rejected by a *structural
refusal* — a boolean saying the leg set is incomplete or exhaustiveness unverified — which tests
flag-honouring rather than arithmetic. In `marginal` the structure is impeccable and only the fee,
spread and carry calculation stands between the scanner and a false fire.

**Pass — both conditions**, as Gate 0: no arbitrage-free world's fire rate exceeds chance on the
exact binomial tail, **and** a genuine fillable edge is detected at least `POWER_FLOOR` of the time.
A scanner that refuses everything passes the first trivially.

**The positive control must not be defined by the detector.** The first version bisected on
`effective_yes_cost` to hit a target post-cost edge — the scanner's own formula — so detection was
guaranteed by construction. That is the retracted Gate-2a demo defect. The gating control now scales
quotes to a fixed **nominal** sum of 0.70, which is riskless under any defensible cost model.

**Carry is charged once (C7).** `effective_yes_cost` already includes it, so the payoff stays a
nominal $1 and is never discounted a second time.

### What Gate B does not license

Passing licenses a **candidate generator**, never a confirmed arbitrage (A5, D1). Two limits are
load-bearing:

1. ~~**Completeness is handed to the scanner as a boolean.**~~ **CLOSED 2026-09-08** — see
   [`LEGSET-RESULTS.md`](LEGSET-RESULTS.md). The `truncated_believed` exhibit fires **1.000 at every
   horizon** and no arithmetic inside the scanner can prevent it, so the defence was built outside
   it: `kairos.legset.verify_leg_set` checks a held leg set against the authoritative
   `/events/<id>` listing, and `scan_verified` refuses anything not carrying a verification.
   The threat was measured at the same time and is **larger than the census anecdote**: real groups
   assembled through offset pagination are **49% truncated**, missing **60%** of their legs.
   **Exhaustiveness is now arithmetic, not a flag.** Only 36% of groups carry an explicit
   `negRiskOther` leg, but **512/512 resolved groups had exactly one winner** — bounding the failure
   rate at **0.59%**, which is still not zero, because failure costs the whole stake rather than the
   edge. Break-even is `edge/(edge+stake)`, so the tradeable floor is **~1%** (it was ~5% at a
   75-group sample; extending it is the cheapest lever there is). Regenerate with
   `python exhaustiveness.py`; never hand-edit the constants.
2. ~~**Depth is synthetic.**~~ **CLOSED 2026-09-09** — `kairos.book` prices each leg at the VWAP to
   fill the target size off the real ask book. A counterparty who withdraws on being hit remains
   unmodelled and is still Gate 3.

---

## Gate C — Cross-venue structural mispricing, and the semantic-identity null gate

> **STATUS: NULL GATE PASSED 2026-09-09. MEASUREMENT RUN 2026-09-09 — WITHHELD.**
>
> `python gatec.py`: the matcher pairs true cross-venue pairs at **1.000** and pairs at **0.000** in
> all seven registered null worlds, 400 pairs each, every world's oracle ceiling 1.000. The gate run
> changed two things in this registration, both recorded rather than quietly applied: the frozen
> evidence list was **incomplete**, and the first version of the matcher produced a **false pair**.
>
> `python scanc.py`: **0 verified pairs** out of ~8.7M same-date candidates against a registered
> floor of 200, so the verdict is WITHHELD and **the kill rule does not fire**. The zero is
> **structural, not empirical** — see below — and the measured blocker is not the one this
> registration predicted.
>
> **REGISTERED 2026-09-09, before any paired market data was fetched.** Frozen while the only
> venue data on disk was Polymarket's, and while nothing had paired a Polymarket market to a Kalshi
> one. Runs: `python gatec.py` (the null gate) then `python scanc.py` (the measurement).
> Method: `principles-20-solutions`, proportionality 4/4, Consensus-backed.

### Why this hypothesis, and what it replaces

Class B's canonical form is **refuted at this venue**: 78 completable negRisk groups across the full
reachable open universe, **zero** with a positive post-cost edge, closest `-0.006`; and re-running at
10 and 5 contracts a leg changed nothing, so it is not a sizing artefact.

The principal cause of that null is now identified: **we scanned the one arbitrage form Polymarket's
own NegRisk adapter exists to eliminate, on a single venue, at a static instant.** The literature
locates the surviving structural edges elsewhere:

| finding | source |
|---|---|
| **$40M realised profit** extracted from Polymarket arbitrage; two forms, *rebalancing* and *combinatorial* | Saguillo et al. 2025, `10.48550/arxiv.2508.03474` |
| Combinatorial episodes concentrated **in the final minutes of live play**, 101 bps median, **76.9% capped at ~14.8 shares** | Cheng et al. 2026, `10.48550/arxiv.2605.00864` |
| **Cross-platform deviations of 2-4%**, persistent, *structural rather than informational*; ~6% of events dual-listed; 100k events, 10 venues | Gebele et al. 2026, `10.48550/arxiv.2601.01706` |
| Polymarket vs Binance options: **5.6-6.3pp** mean gap, AR(1) half-life ~4h, profitable after conservative costs | Portnaya 2026, `10.48550/arxiv.2606.19517` |
| **Limits to arbitrage are directly measurable**: Ecuador's 2.0pp half-spread equalled the 2.1pp cross-venue gap | Bendezu 2026, `10.2139/ssrn.6434079` |

Cross-venue is chosen over the alternatives because its documented effect (2-4%) is **4-7x our best
observed intra-venue deviation (0.6%)**, both venues are publicly reachable without authentication
(verified 2026-09-09), and it reuses the existing cost model, book-depth layer and verification
discipline rather than needing new machinery.

**Rejected, with reasons recorded so they are not silently revisited:**

- **Kalshi parlay markup.** Legs are explicitly published (`mve_selected_legs`), so it has no
  semantic-identity problem — which made it look ideal. But **a parlay cannot be statically
  replicated from its legs**: owning one of each of N legs pays *number-of-winners*, not
  $1-iff-all-win. Parlay overpricing is therefore an **edge with variance, not a riskless
  arbitrage**, and belongs to a different hypothesis class. Filed, not pursued.
- **In-play combinatorial.** Real (290 episodes) but capped at ~14.8 shares and requiring continuous
  live monitoring. Retail-scale ceiling, disproportionate apparatus.
- **Polymarket vs listed options.** Largest documented gap, but needs an options pricing model and
  delta hedging — a much larger build for a relative-value trade that is also not riskless.

### The hypothesis, stated so it can fail

> **H:** For events listed on both venues and verified to be the *same* event, the executable price
> deviation — measured at size off both real order books, net of both venues' round-trip costs — has
> a **positive median**.

Failing means the deviation is consumed by friction, which is Bendezu's measured finding on three
Latin American elections and is the outcome this registration expects to be tested against, not the
outcome it hopes for.

---

### Gate C — the semantic-identity null gate (runs first, always)

**The false-positive generator is semantic non-fungibility**: two markets that *look* identical and
resolve differently. It is the exact analogue of leg-set truncation, which Gate B measured as
carrying the entire Class B defence — and Gebele et al.'s whole contribution is that resolving event
identity is the prerequisite, not a detail.

So no pairing pipeline touches real paired data until it can correctly find **nothing** in worlds
built to contain no true pair (A7).

**Null worlds — every pair below is NOT the same event, and must be refused:**

1. **Horizon mismatch** — same subject, different resolution date ("by Dec 2026" vs "by Mar 2027").
2. **Threshold mismatch** — same underlying, different strike ("BTC above $100k" vs "above $120k").
3. **Scope mismatch** — same actor, different question ("wins the election" vs "wins the popular
   vote").
4. **Resolution-source mismatch** — same question, different arbiter or certification standard.
5. **Settlement-time mismatch** — same question, one settling at market close and one at a fixed
   clock time.
6. **Negation pair** — X on one venue, NOT-X on the other. These are *complements*, not identities;
   a pipeline that treats them as the same event has inverted a sign.
7. **Random pairing** — unrelated markets, the floor case.

**Positive control:** genuinely identical events — same underlying, same threshold, same resolution
date, same resolution semantics — which the pipeline must pair. A matcher that refuses everything
passes every null trivially and is worth nothing, exactly as in Gate 0 and Gate B.

**Pass — both conditions, as every gate here:**

1. **False positives.** No null world's pairing rate exceeds what chance allows, on the exact
   binomial tail rather than an invented tolerance.
2. **Power.** True pairs are matched at least `POWER_FLOOR` of the time.

**Gated per unit, never in aggregate** (`kairos.validity`, AXIOMS G3/G4), and the exhibit alongside
it is a **naive title-similarity matcher**, retained because the size of its failure is the argument
for every refusal the real matcher makes.

### What the null gate found — run 2026-09-09, 400 pairs per world

| world | truly same? | matcher | naive exhibit | refused by |
|---|---|---|---|---|
| identical (control) | yes | **1.000** | 1.000 | — |
| horizon mismatch | no | 0.000 | 1.000 | `resolution_date_differs` 400/400 |
| threshold mismatch | no | 0.000 | 1.000 | `threshold_differs` 400/400 |
| scope mismatch | no | 0.000 | 1.000 | `scope_differs` 400/400 |
| resolution-source mismatch | no | 0.000 | 1.000 | `resolution_source_differs` 400/400 |
| settlement-time mismatch | no | 0.000 | 1.000 | `settlement_time_differs` 400/400 |
| negation pair | no | 0.000 | 1.000 | `polarity_differs` 400/400 |
| random pairing | no | 0.000 | 0.590 | `scope_differs` 385/400 |

Every world's oracle ceiling is 1.000, so no false-positive rate here is a statement about a
contaminated world. **Each of the six comparisons is necessary**: `tests/test_identity.py` removes
them one at a time and shows that exactly one null world starts pairing each time.

**The gate found a false pair on its first run, and the pass/fail column did not show it.** The
date-stripper matched `\b(?:19|20)\d{2}\b`, which deleted *any* strike in 1900–2099 — so two markets
quoted at 2000 and 2050 both parsed to no strike, agreed on everything else, and were declared the
same event. What exposed it was the refusal-*reason* column reading `threshold_differs 386/400`
while the fire rate read a clean 0.000. Fixed by taking the resolution year from the published close
timestamp instead of guessing it out of the title; the residual ambiguity (a strike equal to its own
resolution year) now fails closed, and can cost power but provably cannot produce a false pair.

**The exhibit's result is stronger than "the naive matcher over-fires."** Swept over 60 thresholds
and reported at the one most favourable to it, the best achievable separation between true pairs and
near-misses is **+0.000** — non-positive. There is no similarity cut at which it does better than
chance. The reason is measurable rather than rhetorical: for the source and settlement-time worlds
the similarity vector is *identical* to the control's, pair for pair, because a venue puts neither
the arbiter nor the settlement clock time in the title. The evidence that separates a hedge from a
double position is not in the text the eye compares.

---

### Frozen parameters

| decision | value | why this |
|---|---|---|
| Venues | Polymarket (Gamma + CLOB) and Kalshi (`trade-api/v2`) | Both verified publicly reachable, unauthenticated, 2026-09-09 |
| Pairing evidence | resolution date, **settlement clock time**, threshold/strike, resolution source, scope, and side polarity — **all six must agree** | Any single one disagreeing makes the payoff non-identical, which is the whole failure mode. **Amended 2026-09-09 from five to six, after the null gate falsified the list**: this registration's own settlement-time null world agrees on all five originally frozen fields, so a matcher restricted to them could not refuse it. Recorded rather than silently widened (`CORRECTIONS.md` Pass 18) |
| Deviation measured | **executable**, at size, off both real ask/bid books | An edge at the touch is not an edge at size (D1). Top-of-book comparison is what makes cross-venue gaps look larger than they are |
| Target size | 25 contracts a side, **and** reported as a curve over 5/10/25/50 | Size was held at one value in the negRisk scan and had to be re-run to refute a sizing artefact; C11 says do not hold a design variable constant |
| Costs | Both venues' round-trip: fee + half-spread + carry, charged **on both sides** | Capital is locked at two venues simultaneously, so carry is paid twice. Kalshi's fee schedule must be **verified against its published terms before the run**; pending that, the conservative quadratic form is assumed |
| alpha | 0.05 one-sided | Single pre-specified hypothesis; no family to correct |
| Materiality | deviation must exceed the **round-trip cost on both venues combined** | A statistically real 0.3% gap inside a 2% cost is not an edge (Gate 1's lesson) |

### The resolution-divergence bound — registered as arithmetic, not a flag

Semantically identical markets can still resolve **differently**; that is semantic non-fungibility
realised, and it is the catastrophic case, because both legs lose rather than one. This is
structurally the same problem as negRisk exhaustiveness and gets the same treatment:

- measure the divergence rate on **resolved** dual-listed pairs;
- express it as a **rule-of-three upper bound**, never as zero (A6);
- require `bound < edge / (edge + stake)` before any pair is called a candidate.

`kairos.legset.residual_failure_bound` and `break_even_failure_rate` are reused unchanged. The
measurement is generated by a script and its constants are **regenerated, never hand-edited**, as
`exhaustiveness.py` established.

### What the measurement found — run 2026-09-09, `scanc.py`

4,156 Polymarket descriptors against 114,540 Kalshi descriptors from 12,616 events (both venues swept
to the depth their APIs reach — Polymarket's offset ceiling, Kalshi's cursor exhaustion), blocked on
resolution date across 132 shared dates into **8,765,271** same-date candidate pairs.

| outcome | count |
|---|---|
| verified as the same event | **0** |
| agreeing on everything either venue **publishes** | **1** |
| agreeing on scope | 3 |

**The zero is structural.** Polymarket publishes no determination instant: `endDate` is a day
boundary — **65% at exactly 00:00Z, ~95% day-boundary across 788 open markets** — so under the
six-piece evidence rule above, no Polymarket/Kalshi pair *can* verify, whatever the venues list.
Reading this 0 as a statement about how many events the two venues share would take an instrument's
ceiling for the world's floor (AXIOMS G12).

**What it does establish is more useful than the count.** The scope check — the one that could have
failed on vocabulary alone, "Bitcoin" against "BTC" — agreed on three real dual-listed events, and
one of them agrees on every piece of evidence either venue publishes:

| Polymarket | Kalshi | blocked only by |
|---|---|---|
| Will Trump recognize Somaliland before 2027? | Will Trump recognize Somaliland? | unrecoverable: source, settlement time |

So **the venues share events and the matcher recognises them.** That first run concluded the binding
constraint was a missing instrument rather than a missing market. **Gate C2 built the instrument and
refuted that conclusion** — see below.

The single provisional pair was **deliberately left unpriced**. Putting a deviation on the table
before the instrument that produces it has passed a gate is how Look 1 spent its alpha.

### What Gate C2 found — re-run 2026-09-09 with the extractor in place

> **STATUS: PASSED, THEN RE-MEASURED — VERDICT UNCHANGED, WITHHELD.** `gatec.py` passes with nine
> null worlds (power 1.000, every null 0.000). `scanc.py`: 4,103 Polymarket against 115,379 Kalshi
> descriptors from 12,716 events, 8,690,013 same-date candidate pairs, **0 verified**.

The extractor works — it reconstructs the Somaliland market's `endDate` from that market's own prose
to the minute. What it revealed is that the genuinely dual-listed pairs **are not the same event**.

Of the **3** pairs that agreed on scope — the ones a human would call the same market — the blockers
were `resolution_source` unavailable (2), **`settlement_time_differs` (2)**, `threshold_presence`
(2), `modality` unavailable (1), `resolution_source_differs` (1).

| | Polymarket | Kalshi |
|---|---|---|
| market | Will Trump recognize Somaliland before 2027? | `KXRECOGSOMALI-29-27`, "Before 2027" |
| determination instant | **2027-01-01T04:59Z** | **2027-01-01T15:00Z** |

**Ten hours and one minute apart**, both labelled "before 2027". An event in that window resolves YES
on Kalshi and NO on Polymarket, so a position held across the two as a hedge **is not a hedge** —
both legs lose. The same gap appears on the second pair. This is the semantic non-fungibility this
gate was registered to catch, measured on live markets rather than assumed, invisible in every title,
and present on the pairs that look *most* identical.

**Pass 22 withdrew the conclusion drawn here.** This section originally read that the venues "list
very few mutually fungible events". They do not: `recall.py` surfaced 22,866 token-overlap candidates
and **26 of the top 26 are plainly the same event, of which the matcher paired 0**. The count of 3
was a property of the matcher, not the venues. Gate C's **power 1.000 was circular** — its positive
control was published by the same generator its parser was written against (AXIOMS G14).

### Gate C2 — the settlement-instant extractor

> **REGISTERED 2026-09-09, before the extractor was written and before it was pointed at any paired
> data.** Runs: `python gatec.py` (extended null worlds) then `python scanc.py`.

The measurement above is blocked on one missing instrument. This registers it, and registers the
null worlds it must survive first, because it is new extraction logic and Gate C's existing worlds
never exercised it (A7).

**The correction that prompted it.** `scanc.py` treated Polymarket's settlement clock time as
unrecoverable on the grounds that `endDate` is a day boundary. That was too broad. The Somaliland
market's prose says *"by December 31, 2026, 11:59 PM ET"* and its `endDate` is `2027-01-01T04:59Z` —
**the same instant**. 04:59Z is not a placeholder, it is midnight-ET. So the time is not
unrecoverable; it is **unconfirmed**, and the fix is a cross-check rather than an assumption.

**What the extractor must do.**

1. Recover a determination instant from the rules prose — `<Month> <D>, <YYYY>, <H>:<MM> <AM/PM>
   <TZ>` and `on <Month> <D>, <YYYY> at <H> <AM/PM> <TZ>` — converting to UTC. `ET` resolves through
   `America/New_York` so daylight saving is handled by the zone database rather than a hardcoded
   offset; `UTC`/`GMT` map to UTC; **any other zone is unrecoverable.**
2. **Confirm it against `endDate`, to the minute.** Agreement makes the instant recoverable.
   Silence in the prose makes it unrecoverable. *Disagreement* also makes it unrecoverable, and is
   counted — two sources contradicting each other is the one case that must never be resolved by
   picking a favourite (A6). This is the leg-set pattern: use the authority, but verify it.

**Modality becomes the seventh piece of evidence.** *"Will X happen **by** T"* and *"Will X be true
**at** T"* are different events — a barrier and a digital — and they carry the same timestamp. An
extractor that returns an instant while discarding which of the two it came from would **create**
the semantic non-fungibility this whole gate exists to catch. Recovered from prose on Polymarket
(`by`/`before` → deadline, `on … at` → instant) and from `yes_sub_title` on Kalshi (`Before …` →
deadline; `On …`/`At …`/a strike → instant). Unrecoverable on either side fails the pair closed.

This is the **second** amendment to Gate C's frozen evidence list, after the settlement instant
itself in Pass 18. Both were found by building against the registration, and both are recorded here
rather than quietly applied.

**Two new null worlds, and one strengthened control:**

| world | must be | why |
|---|---|---|
| **Modality mismatch** | refused | Same subject, same timestamp, one phrased as a deadline and one as an instant. Agrees on all six previously registered fields. |
| **Prose-instant contradiction** | refused | The rules text states a time that contradicts the structured close timestamp. Tests the confirmation rule; a pipeline that trusts either source alone passes this by accident. |
| **Control: prose-only vs structured** | paired | The same event where one venue publishes the instant only in prose and the other structurally. This is the real cross-venue case, and a matcher that cannot do it has no power where it matters. |

**Pass conditions are unchanged** — no null world above chance, control above `POWER_FLOOR`, gated
per unit. **The extractor may not be used by `scanc.py` until `gatec.py` passes with these worlds
in it.**

### The stopping rule was followed: the venue-pair branch is exhausted

> **RUN 2026-09-09, `python venues.py`.** The rule below says that under 200 verified pairs the
> honest next move is *a different venue pair*. That move was made, as a **feasibility probe before
> an adapter** — building one costs a day and three of the four checks kill a candidate in a minute.

A venue can host this measurement only if it publishes **all three** of: resolution rules, a
determination **instant**, and order-book **depth**. Gate C2 measured why the instant is not a
formality, and D1 measured why the touch is not depth.

| venue | reachable | rules | determination instant | depth | verdict |
|---|---|---|---|---|---|
| Polymarket | yes | prose | prose-confirmed on ~7% | CLOB | incumbent |
| Kalshi | yes | structured | structured | yes | incumbent |
| **PredictIt** | yes | **none — no rules field at all** | 116/590 carry a bare date, **never a clock time** | **none — top-of-book only** | unusable |
| **Smarkets** | yes | 19/60 events | **0/55 structured, 0/55 from prose** | yes, real ladder | unusable |
| Manifold | yes | — | — | AMM | play money, resolved at the **creator's discretion** — not a data limit, a payoff-identity impossibility |
| Metaculus | HTTP 403 | — | — | — | no money at stake; a forecast source, not a venue |
| Insight / Limitless | 401 / 404 | — | — | — | authenticated or gone |

**No publicly reachable third venue publishes a determination instant.** Smarkets is the near miss —
real exchange, real ladder, real rules on some events — and it publishes no settlement time at all,
which after Gate C2 is known to be the difference between a hedge and two losing legs.

**This section's conclusion was withdrawn by Pass 22 and is retained for the record.** It read that
Class B cross-venue is NOT TESTABLE and that F3 created a deadlock. Both were wrong:

- **NOT TESTABLE** rested on the claim that the venues share few fungible events. `recall.py`
  falsified it: 26 of the top 26 token-overlap candidates are the same event and the matcher paired
  **0**. Recall, never measured until Pass 22, is ~0.
- **The F3 deadlock was a misreading.** F3 forbids *"broker integration, live capital, or production
  executor"*. Reading market data with an application key is none of the three. The constraint was
  quoted without being checked.

The third-venue inventory above still stands as a measurement — PredictIt and Smarkets genuinely do
not publish what Gate C requires — but it answers a question that was not the binding one.

### Gate C3 — the recall floor and the adjudicated alignment table

> **REGISTERED 2026-09-09, before the alignment table was built and before any price data was
> fetched for any pair in it.** Runs: `python align.py` (surface + adjudicate) then
> `python scanc.py --alignment` (measure).

Pass 22 measured what four passes had assumed: the matcher's recall on real venue text is **0/26**,
against a false-positive rate of 0.000 across nine adversarial null worlds. It is a maximally
conservative instrument, and every conclusion drawn from its verified count measured the instrument.

**Precision transfers out of a null world; power does not** (AXIOMS G14). So this gate registers the
missing half.

#### The recall floor

**`RECALL_FLOOR = POWER_FLOOR = 0.50`.** Deliberately the repo's existing constant rather than a new
one — inventing a threshold *after* seeing that the old instrument scored zero is how a floor gets
chosen to be clearable. The justification is Gate 0's, unchanged: an instrument that misses more than
half of what it is looking for cannot support a null, because its count is then a statement about
the instrument (G12).

**Binding:** `scanc.py` may not announce any verdict — including WITHHELD — unless measured recall
against the frozen table is at or above the floor. Below it, the run reports *no verdict* in the
sense `kairos.validity` already means it.

**Precision may not be traded for recall.** The nine null worlds must still return rates
indistinguishable from chance on the exact binomial tail. A matcher that buys recall by loosening is
the failure this whole protocol exists to prevent (A7, A8).

#### The adjudicated alignment table

Gebele et al. built a **human-validated** cross-platform dataset; that is the method, and it is
adopted here rather than a runtime fuzzy matcher, which would add an ungated instrument and a
dependency.

**Construction, frozen now:**

1. **Candidates are surfaced mechanically** — token overlap through an inverted index, using no check
   the matcher makes, so a pair the matcher would refuse for date, source, threshold or modality
   reasons still appears. Cherry-picking is excluded by construction.
2. **Adjudication happens before any price is fetched.** The table is built from titles and rules
   only. This is the one protection that matters, because the adjudicator knows which answer is
   convenient, and it is enforceable: no book is fetched until the table is frozen.
3. **Every pair records its label and its reason**, so the table is auditable rather than asserted.

**Three labels, defined before use:**

| label | definition | how it may be used |
|---|---|---|
| **IDENTICAL** | A YES on one venue and a NO on the other pays exactly $1 in **every** state of the world | Riskless leg of Class B. Counts toward the 200-pair floor |
| **FUNGIBLE-WITH-BASIS** | Same underlying question, but with a **measurable** divergence risk — a deadline gap, a different arbiter — so the two can resolve differently in states that can be enumerated | Counts toward the floor **only** with a divergence bound below `break_even_failure_rate` at the measured edge |
| **DISTINCT** | Different events. Includes every near-miss Gate C registers | Never counted. Refusing these is what the gate measures |

**FUNGIBLE-WITH-BASIS is the correction Pass 22 identified.** The programme had been converting a
quantifiable basis risk into a binary disqualifier — the Somaliland pair settles 10h01m apart and was
refused outright — while the repo's own Gate B pattern says the opposite: express residual risk as a
**rule-of-three bound** and compare it to `edge / (edge + stake)` **at the measured edge**. Same
machinery, `kairos.legset.residual_failure_bound` and `break_even_failure_rate`, reused unchanged.

**A basis-risk inventory is reported per pair.** For every aligned pair the mechanical checks still
run and their disagreements are recorded — not as refusals now, but as the named ways the two legs
can come apart. **No pair is described as riskless unless every mechanical check agrees.**

#### What is not being relaxed

The mechanical checks are not deleted and their thresholds are not tuned. What changes is their
*role*: scope identity moves to adjudication, because token-set equality was measured at 0 recall;
the rest become evidence attached to a pair rather than a veto over it. **Gate C's null worlds
continue to gate**, and the alignment table is required to label all nine of them DISTINCT — a table
that cannot refuse the registered near-misses is not evidence, it is a wish.

### Stopping rule — binding

Sweep the dual-listed universe **once**, to whatever depth the two APIs reach, and stop. Do **not**
extend the sweep because the result disappoints. If fewer than **200 verified pairs** are found, the
verdict is WITHHELD as underpowered — *"not enough evidence"*, never *"no effect"* (A1).

### Decision rule — written before the numbers

| outcome | action |
|---|---|
| Median executable deviation **exceeds** combined round-trip costs, on >= 200 verified pairs | A candidate class exists. Proceeds to Gate 3 (execution realism), which is where quote persistence and settlement-timing risk live |
| Median executable deviation **does not** clear costs | **Class B is concluded and the programme ends.** Both hypothesis classes will have been tested and rejected. Record it and stop — do not open a third venue looking for a better answer |
| Fewer than 200 verified pairs | WITHHELD. The honest next move is a different venue *pair*, not a re-test of this one |

### What this gate does not cover, named now

- **Settlement-timing mismatch.** The two venues may resolve at different times, so a "hedged"
  position is not flat in between. Gate 3.
- **Quote persistence.** Nothing models a counterparty withdrawing on being hit. Gate 3.
- **Venue access is jurisdiction-dependent** and is an **operator precondition**, not a technical
  question. Nothing in this repo assumes or asserts eligibility to trade either venue, and no result
  here implies a trade is permissible.
- **F3 stands.** No broker integration, no live capital, no production executor.

---

## Class C — Cross-venue convergence, and Gate D

> **STATUS: GATE D.0 RUN 2026-09-14 — SPLIT VERDICT. Class C is NOT refuted as measured, and IS
> refuted inside the registered tradeable band.** 140 aligned pairs, 81 priced at 25 contracts a
> side. Unbanded: largest gap `+0.09775` against a median four-crossing round trip of `0.02824`, so
> the falsifier does not fire. Banded: **52 of the 81 priced pairs are longshots** the
> market-selection preconditions exclude at every gate, and on the 29 that remain the largest gap is
> `+0.05000` against a median round trip of `0.08638` — refuted. The widest gap in the whole table
> sits on a pair quoted at 3.8 cents.
>
> **The verdict therefore turns on a precondition no scanner in this repo has ever enforced**
> (`price_in_band` lives in `kairos.gate` and `kairos.sizing` only — `scanb.py` and `scanc.py` do not
> apply it either). Both readings are reported; neither is chosen here. See
> [`GATED-RESULTS.md`](GATED-RESULTS.md) and `CORRECTIONS.md` Pass 26.
>
> No price *history* has been fetched for any pair on either venue, so **no pair is spent**. The
> convergence pipeline is **not** built: Gate D.0 licenses Gate D (the null gate) at most, and the
> banded reading does not license even that. Runs, in order: `python gated.py` (the DOA arithmetic),
> then `python gated.py --nulls` (the convergence null gate), then `python scand.py` (the
> measurement).

### Why this is a new class and not a rescue of Class B

Class B cross-venue measured the cost of **buying YES on one venue and NO on the other and holding
to settlement**: 117 priced pairs, zero clearing costs, median `-0.09579` (`-0.08338` at zero fees).

That result does **not** refute the literature it was built on. Gebele et al. measure a *price gap at
the touch*; this measured *the executable cost of a hedge held to resolution*. Both can be true: a
persistent 2-4% gap can exist and be unreachable by a trade that crosses two books and then pays
carry at both venues for a ~114-day median horizon.

**Class C is the other way of trying to reach it:** enter on the gap, exit when it closes, never hold
to settlement. It is a genuinely different hypothesis with genuinely different risk — **there is no
riskless leg.** It requires the gap to actually converge, and it loses if the gap widens first. It
must not inherit any of Class B's licences.

### Gate D.0 — the dead-on-arrival check, which runs before anything is built

**A convergence round trip crosses four books, not two.** Entry buys both legs; exit sells both.
Class B's measurement bought two legs and let settlement pay the rest. So Class C pays *more*
transaction cost and *less* carry, and it is only better if the carry saved exceeds the two extra
crossings.

Indicatively, from the Class B run: of the `0.0834` zero-fee cost, carry at 114 days accounts for
roughly `0.019`, leaving about `0.065` of pure crossing cost for two legs. **Four crossings is
therefore around `0.13`, against carry savings of at most `0.019`.** On those figures Class C is
worse than the hypothesis that already failed.

So Gate D.0 is registered as the **first** thing that runs, and it needs no time-series data at all:

> **Measure, on the existing 140-pair alignment table, the full four-crossing round-trip cost and
> the observed entry gap. If the largest observed gap does not exceed the median round-trip cost,
> Class C is refuted and no convergence pipeline is built.**

This is deliberately a cheap falsifier placed ahead of an expensive build. It is also the honest
reading of the prior: **the arithmetic currently points against this hypothesis, and that is recorded
here before the number is produced so it cannot later be presented as a surprise.**

### The hypothesis, stated so it can fail

> **H:** For cross-venue pairs verified fungible, conditional on the executable gap exceeding a
> pre-registered entry threshold, the gap narrows enough within a pre-registered horizon to cover a
> four-crossing round trip, with a positive median across pairs.

### The variant, chosen and frozen

Two forms exist and they are not interchangeable:

| variant | crossings | isolates the gap? | exposure |
|---|---|---|---|
| **Hedged** — long the cheap leg, long the opposite side on the dear venue | 4 | yes | the gap only |
| **Unhedged** — long the cheap leg alone, sell when it converges toward the other venue | 2 | no | the underlying event |

**The hedged variant is registered.** The unhedged one is cheaper and is *not* a convergence test at
all: it is a directional bet whose profit is dominated by whether the event happens, and a positive
result from it would be uninterpretable. Choosing the cheaper instrument here would be choosing the
one that cannot fail cleanly.

### Gate D — the convergence null gate

**The false-positive generator is bid-ask bounce.** Any two noisy price series will show apparent
convergence after a large observed gap, because a large gap is partly measurement error and error
mean-reverts by construction. A convergence detector that has not been shown to find nothing in
uncorrelated noise is measuring its own sampling (A7).

**Null worlds — every one contains no harvestable convergence, and must be refused:**

1. **Independent random walks.** Two unrelated price paths with bid-ask noise. Any apparent gap
   closure is bounce.
2. **Common-factor with a permanent spread.** Both series track the same event, separated by a
   constant structural offset that never closes — the venue-convention case Class B measured.
3. **Convergence slower than the horizon.** A real mean-reverting spread whose half-life exceeds the
   registered holding period, so the trade exits before the gap closes.
4. **Convergence below costs.** A real, fast, mean-reverting spread whose amplitude is smaller than
   the four-crossing round trip. The discriminating null: structure impeccable, only the arithmetic
   says no.
5. **Gap widens first.** A spread that converges eventually but breaches a stop en route. Tests that
   the exit rule is priced, not assumed.

**Positive control:** an injected mean-reverting spread with a half-life inside the horizon and an
amplitude comfortably above the round trip. And — the lesson of AXIOMS G14 — **the control must be
generated by a process the detector was not written against.** Gate C scored 1.000 power on its own
parser's dialect and 0/26 on real text; a convergence control drawn from the same model as the
detector would repeat that exactly.

**Pass — both conditions, per unit, as every gate here:** no null world profits above chance on the
exact binomial tail; the control is detected at least `POWER_FLOOR` of the time.

### Frozen parameters

| decision | value | why this |
|---|---|---|
| Entry threshold | executable gap > **2×** the measured four-crossing round trip | A threshold at 1× has zero margin for the gap widening before it closes |
| Holding horizon | **7 days**, then exit at market regardless | Portnaya measures an AR(1) half-life of ~4h on a comparable wedge; 7 days is ~40 half-lives, so failure to converge inside it is a finding about the pair, not the window |
| Stop | exit if the gap **doubles** against entry | Registered because null world 5 exists to test it |
| Exit | gap closes to ≤ 25% of entry, **or** horizon, **or** stop — whichever first | Frozen so "hold a little longer" is unavailable after the fact |
| Sizing | 25 contracts a side, curve over 5/10/25/50 | C11 |
| Costs | four crossings, both venues, plus carry over the realised holding period | Carry is now *short*, which is the whole economic claim — so it must be measured, not assumed away |
| alpha | 0.05 one-sided | Single pre-specified hypothesis |
| Pair set | **only pairs whose price history has never been fetched** | See below |

### Data discipline — the part most likely to be violated

The 140-pair table's **snapshot** prices have been seen. Their **histories** have not. That
distinction is thin, and it is exactly where a forking path would open, so:

1. Class C selects pairs by the adjudicated alignment table **only** — never by their observed gap.
2. The Class B snapshot may be used for the **cost arithmetic** (Gate D.0) and for nothing else. It
   may not inform entry thresholds, pair selection, or horizon.
3. Any pair whose history is fetched becomes **spent**. It may be used once. Re-running the
   convergence test on the same histories after a failure is look #2 reported as look #1, which is
   the defect Look 2 exists to document.

### Stopping rule — binding

Fetch history once, to the depth both APIs reach, and stop. Below **200 pairs with usable history on
both venues**, the verdict is WITHHELD as underpowered — *"not enough evidence"*, never *"no
effect"* (A1).

### Decision rule — written before the numbers

| outcome | action |
|---|---|
| Gate D.0 fails — the largest gap does not exceed the median round trip | **Class C is refuted before it is built.** No pipeline, no history fetched |
| Gate D fails | No measurement runs. Fix the detector; do not tune the worlds (A8) |
| Median convergence profit clears the four-crossing round trip on ≥ 200 pairs | A candidate class exists. Proceeds to Gate 3 (execution realism) — which for this class also has to model **the exit**, since a convergence trade that cannot be closed is an outright position |
| Median does not clear | **Class C is concluded.** With Class A and Class B already rejected, that is the end of the registered programme |

### What this does not cover, named now

- **Convergence is not arbitrage.** There is no state of the world in which this position is
  guaranteed whole. Nothing in Class C may be described as riskless at any point.
- **Exit liquidity.** Gate 3. A gap that closes on a screen you cannot trade out of is not a profit.
- **Adverse selection.** The gap may be wide *because* one venue knows something. Neither Gate D nor
  the measurement can distinguish that from friction; only a resolved-outcome study can.
- **Venue eligibility remains an operator precondition** this repo neither assumes nor asserts.
- **F3 stands.** No broker integration, no live capital, no production executor.

---

## Gate 1 — Does `q_ref` earn its existence?

> **STATUS: RUN 2026-09-08 — `q_ref` REJECTED.** No transformation beat the raw quote on 731
> independent events. Gate 2 uses raw `q`. Isotonic removed from the family; `C_logit` was
> underpowered (p≈0.11 on +0.0134), not disproven at the time. **Re-tested and REJECTED by Look 3**
> on 1,966 fresh events (`+0.00371`, p=0.0335 vs registered α=0.025, 0.987% vs a 1% floor), so the
> deferral is closed. `baseline.py` is retained un-exported for reproducibility, not pending.
> See [`GATE1-RESULTS.md`](GATE1-RESULTS.md) and [`LOOK3-RESULTS.md`](LOOK3-RESULTS.md).

`q_ref` is an estimator, not truth (A2). It must beat the raw quote out of sample or be deleted.

Four frozen baselines, each fitted **strictly on prior resolved markets** and evaluated on unseen
later events:

| # | Baseline |
|---|---|
| **A** | Raw quote `q_raw` only |
| **B** | Settlement adjustment only |
| **C** | Statistical recalibration only |
| **D** | Settlement + recalibration |

**Rules.**
- Rolling/expanding temporal splits. No evaluation outcome may participate in fitting.
- Compare recalibration families — logistic/beta in logit space (Ojeda et al.) against identity and
  against isotonic — rather than assuming one.
- Propagate estimation uncertainty; Le finds ~half of raw slope variation may be noise.
- **Keep the simplest survivor** (C9). A more complex baseline that does not produce a reproducible
  OOS gain over a simpler one is removed, not retained "for later".
- Do not select the winner on the final test set.

This gate also settles the double-counting question that code order cannot (C7): if B and D are
indistinguishable, the settlement adjustment is being re-learned by the recalibration and one of
them goes.

---

## Gate 2 — Forecast superiority

> **STATUS: 2a RUN 2026-09-08 — ladder stopped at rung 2.** No leakage-free forecaster beat
> the market price; best was `drift` (+0.01193, p=0.1174). Pooling machinery deliberately NOT
> built. **2b (LLM) is blocked on leakage** - these markets resolved inside frontier training
> windows. See [`GATE2A-RESULTS.md`](GATE2A-RESULTS.md).

Primary test as registered in §0, on frozen out-of-sample observations.

- Resample at the highest meaningful event cluster; preserve chronology and regime structure.
- Model dependence **across** nominal events that share news regimes, settlement variables, or
  common drivers (C3).
- Report both `p` vs `q_raw` **and** `p` vs `q_ref`. Hindcast supplies an independent third-party
  `p` vs `q_raw` comparison; do not modify it to use `q_ref` (EVIDENCE §7). If the two stories
  diverge sharply, investigate before proceeding.
- Report power. "Not enough evidence yet" ≠ "no edge" (A1).

**Ensemble sub-protocol.** Before any weighting machinery, measure pairwise forecast-error
correlation `ρᵢⱼ` and report the effective number of independent forecasters (C8). Then run, in
this order, and stop at the first that is not beaten:

1. market alone
2. best single model
3. simplest cross-model pool
4. market-anchored simple pool

Sophisticated weighting is built only if it beats these on frozen OOS data (C9, E1). Prefer source
diversity that measurably reduces residual correlation over vendor diversity that does not.

---

### Gate 3.0 — Class M: does the fill arrive at all?

> **REGISTERED 2026-09-14, before it was built and before any book depth was fetched for the
> measured set.** Runs: `python gate3.py`.
>
> **STATUS: RUN 2026-09-14 — BOTH VARIANTS CLEAR. Class M survives.** 248 books measured; median
> touch depth **148 contracts** against median one-sided daily flow of **5,420** — the queue turns
> over ~36 times a day and only **2.4%** of markets fail to clear it. At 25 contracts posted:
> (a) **$1,228/yr**, (b) **$780/yr**, against a $104.70 floor.
>
> **Both pre-committed expectations were refuted**: these markets are wide and *active*, not quiet,
> and **(a) beats (b) at every size** because paying two ticks for priority is wasted when the queue
> turns over anyway. The first gate in this programme whose adverse prior did not survive contact.
>
> **The verdict is size-dependent and this registration froze no size** (C11 violation,
> `CORRECTIONS.md` Pass 30.2), so the curve is the result: `$246` at 5 contracts to `$76,078` at
> 2,000. The large rows are the least trustworthy — they rest on a 3.9% retention measured on
> *aggregate* flow, and an entrant posting 500 against a 148-deep touch **is** the book rather than a
> share of it. See [`GATE3-RESULTS.md`](GATE3-RESULTS.md).

Gate M measured what a fill is **worth**: `R(60) = +0.00039`, 3.9% of the quoted half-spread. It
measured nothing about whether a fill **happens**. That is this gate, and it is the last cheap
question in the programme.

**Why no null gate.** A7 requires one before any *search*. This is a single registered arithmetic on
two measured quantities — resting depth and realised flow — with no hypothesis space to search and
no estimator to be fooled, exactly as Gates D.0 and 4.0 were. Saying so explicitly because skipping a
null gate is normally the error, not the plan.

#### Decision-rule specification — units, weighting, preconditions

*The house rule since `CORRECTIONS.md` Pass 28.2, applied before anything is decided.*

| element | value |
|---|---|
| **Units of the threshold** | **dollars per year, absolute.** Never a rate — Pass 27.1, where a 43% return on $24.40 cleared a rate floor and meant nothing |
| **Weighting** | **flow-weighted across markets**, unweighted reported beside it — Pass 28.1 |
| **Preconditions applied** | the longshot band (Pass 26.1) and tick room > 1 (Gate M.0), identical to the set Gate M measured `R` on, so the two numbers multiply legitimately |
| **Primary statistic** | expected annual fills × `R(60)`, at measured depth and measured flow |
| Floor | **$104.70/yr**, 10× the taker ceiling, unchanged from Gate M.0 so the two are comparable |

#### The two strategies an entrant actually has, and both are measured

| | queue position | capture per fill |
|---|---|---|
| **(a) Join the back** | behind all resting size at the touch | the full quoted half-spread × retention |
| **(b) Improve by one tick** | first | `(spread − 2 ticks) / 2` × retention |

(a) fills only after the resting queue is consumed, so expected daily fills are
`max(0, side_flow − touch_depth)`. **Where a day's one-sided flow is smaller than the size already
resting, an entrant is never filled and the strategy earns exactly zero**, whatever the spread.

(b) trades price for priority. It is reported as the **generous** variant — it assumes an entrant is
never outbid, which is false the moment an incumbent requotes, and it collects all the adverse
selection by being first in line for informed flow. `R(60)` was measured on aggregate flow, not on
best-quote flow, so applying it to (b) **overstates** (b).

#### Pre-committed expectation

Gate M.0 measured 77.4% of flow sitting in one-tick markets, which are excluded here by the tick-room
precondition. The remaining markets are wide **because they are quiet**, so the expectation is that
flow per market is small relative to resting depth and that (a) approaches zero fills. **The
interesting number is (b)**, and the expectation is that it clears the $104.70 floor while remaining
far below anything that would fund the work. Recorded so neither outcome can be presented as a
surprise.

#### Stopping and decision rules — written before the numbers

Fetch the book once per eligible market, to the depth the API reaches, and stop. Below **50 markets
with a usable book**, WITHHELD as apparatus (A1, G12).

| outcome | action |
|---|---|
| Neither variant clears the floor | **REFUTED. Class M closes and the registered programme ends** — every hypothesis class tested and none survives |
| Only (b) clears | Class M survives **only as a quote-improvement strategy**, and the next question is competitive response, which is a new registration and is not licensed here |
| Both clear | Class M survives. Gate 4 (capacity) re-runs against the maker numbers rather than the taker ones |

#### What it does not cover

- **Competitive response.** Nothing models an incumbent requoting when improved upon, which is the
  central risk of variant (b).
- **Adverse selection at the touch.** `R(60)` is an aggregate-flow number applied to best-quote fills,
  which flatters (b).
- **Maker rewards** remain excluded, and cut for.
- **Partial fills and cancellation** are unmodelled.
- **F3 stands.** No broker integration, no live capital, no production executor, no quoting.

---

## Gate 3 — Execution realism

> **STATUS: NOT RUN — blocked on having a candidate, not forgotten.** Class A was rejected (Look 3)
> and the Class B scan produced no candidate across the full reachable open universe, so there is
> nothing whose execution could be tested. **Quote persistence lives here**: nothing yet models a
> counterparty withdrawing when hit, which is the usual reason a screen-visible arbitrage is not
> executable, and it gates every candidate the scanner will ever produce.


Replay against real book, fee, fill and settlement semantics.

- PredictionMarketBench is the **reference implementation and smoke test**, not a certifier — four
  Kalshi episodes cannot establish execution realism for another venue or category (D6).
- Microstructure work on Polymarket sources trade direction from on-chain `OrderFilled` events, not
  the public feed (~59% agreement).
- A strategy intended for a venue ultimately requires that venue's historical replay.
- Do **not** build a generic LOB simulator (E1, D6).

---

## Gate 4 — Capacity and economics

> **STATUS: NOT RUN — blocked on Gate 3.** Capacity is a question about a strategy that survives
> execution realism. Running it now would size something that does not exist (E1).
>
> **Gate 4.0 is not blocked on it — see below.** The ordering above is correct for *"is there an
> edge"* and wrong for *"is there a business"*, and that distinction is itself a constraint.

### Gate 4.0 — the capacity ceiling, measured before another edge is searched for

> **REGISTERED 2026-09-14, before it was built and before any capacity number was produced.**
> Frozen while the only economic figures on disk were Class B's and Class C's per-contract edges.
> Runs: `python gate4.py`.
>
> **STATUS: RUN 2026-09-14 — FLOOR CLEARED, AND THE FLOOR CANNOT BEAR THE WEIGHT.** 82 pairs priced;
> **78 do not clear their own round trip**, 3 clear but are longshots, **1 clears in band**.
> Deployable capital across the whole reachable universe: **$24.40**. Generous annual ceiling:
> **$10.47**. That is a 43% return on capital, so it passes the registered 6% floor — **because the
> floor is scale-free and the constraint is a magnitude.** The hurdle is *not* being changed after
> the fact; the defect is recorded (`CORRECTIONS.md` Pass 27.1) and the finding is stated in the
> units the question was asked in. The registration already said clearing this floor is **necessary,
> never sufficient**, and left the operator hurdle unset: any hurdle above ten dollars a year fails.
> **Capacity is the binding constraint, established by magnitude rather than by the test.**
> See [`GATE4-RESULTS.md`](GATE4-RESULTS.md).

**Why this runs now, out of order.** Gate 4 sits behind Gate 3, which is behind having a candidate.
So the one measurement that can kill the programme for free is scheduled after every expensive
thing in it. That is a **policy constraint**, not an evidential one: nothing about capacity requires
a surviving candidate, because capacity is a property of the *venue* — depth, horizon and the size
of the opportunity set — not of the strategy that would exploit it. Gate D.0 established the
pattern: a cheap falsifier placed ahead of an expensive build, whose adverse prior is recorded
before the number exists.

**What it measures.** For the reachable opportunity set, at measured depth:

```
annual value = edge_per_contract x fillable_contracts x opportunities_per_year x hit_rate
             - annual_fixed_cost
```

`kairos.economics.StrategyEconomics` already carries this and has never been given measured inputs.
Three of the four are measurable now. **`opportunities_per_year` is not** — no price history has
been fetched, so recurrence is unobserved, and PROTOCOL Gate 4 forbids annualising a short sample
as though frequency were stationary.

**So the unmeasured term is inverted rather than invented.** The gate reports the **recurrence rate
required to clear the hurdle** — how many times a year the whole measured opportunity set must
reappear for this to be a business — and the reader judges that number against the venue. This is
the same move `scanc.py` makes with the unverified Kalshi fee: an unmeasured input becomes a
reported dependency, never a silent assumption (AXIOMS A6, G3).

#### The hurdle, fixed before the number

| decision | value | why this |
|---|---|---|
| **Objective floor** | the repo's own `CostModel.settlement_wedge_annual` = **6%/yr** on capital locked | Deliberately an existing constant, not a new one. The cost model already charges this as the opportunity cost of locked collateral, so a strategy that cannot beat it is **strictly worse than not trading** — it pays itself less than the carry it is charged. A floor invented today, after four failed hypotheses, would be a floor chosen to be clearable |
| **Operator hurdle** | **not set here** | PROTOCOL Gate 4: *"the hurdle is what the same effort earns elsewhere, not zero."* That is the operator's opportunity cost and this repo does not know it. Passing the objective floor is **necessary, not sufficient** |
| Sizing | 25 contracts a side, curve over 5/10/25/50 | C11, unchanged |
| Capital per opportunity | the measured all-in entry cost at that size | Not notional. What is actually posted and locked |
| Horizon | measured per opportunity: settlement for Class B, the registered 7 days for Class C | Bounds how often the *same* capital can be redeployed |
| `hit_rate` | **1.0**, and labelled optimistic | Latency, races and partial fills are unmeasured. Setting it below 1 would be inventing a number in the direction of the expected answer |
| `annual_fixed_cost` | **0.0**, and labelled optimistic | Research, data and operator time are real costs that belong here. Charged at zero so the ceiling cannot be blamed on an overhead estimate |

**Every optimistic assumption above is deliberate.** The ceiling is built to be unreachably
generous — perfect fills, free infrastructure, free research, instant redeployment — so that a
failure cannot be attributed to a harsh test, exactly as Gate D.0 compares the largest gap to the
median cost.

#### Pre-committed expectation, recorded before the run

The visible Class C opportunity set at the time of registration is two pairs worth roughly
`$1.54` combined at 25 contracts, against a 140-pair table, and Class B's completable groups were
uniformly negative. **The expectation is therefore that the ceiling lands orders of magnitude below
any defensible hurdle, and that the binding constraint on this programme is capacity rather than
edge discovery.** This is written down now so a confirming result cannot be presented as a
discovery, and so a contradicting one is visible as the surprise it would be.

It is also a sketch, and `CORRECTIONS.md` Pass 26.3 records what happened the last time a sketch
inside a registration was treated as a measurement: the Class C cost estimate was wrong by a factor
of four, in its own favour. **This expectation carries no weight against the number.**

#### Stopping rule — binding

Measure the reachable opportunity set **once**, to the depth the APIs already reach, and stop. Do
not widen the universe because the ceiling disappoints. If nothing prices, the verdict is WITHHELD
as an apparatus failure, never as a capacity finding (AXIOMS A1, G12).

#### Decision rule — written before the numbers

| outcome | action |
|---|---|
| Ceiling clears the 6%/yr floor on deployed capital at a plausible recurrence | Capacity is **not** the constraint. Gate D and Gate 3 become worth their cost, and the operator hurdle is then the live question |
| Ceiling is below the floor, or requires an implausible recurrence | **Capacity is the binding constraint, and it is external.** No further edge search is licensed: more discovery optimises a non-constraint. The remaining moves are structural — a different role (maker rather than taker), a different market, or a different product — and each is a new registration, not a continuation of this one |
| Nothing prices | WITHHELD. Apparatus, not capacity |

#### What Gate 4.0 does not cover, named now

- **Recurrence is not measured.** It is inverted and reported. A required rate that looks plausible
  is not evidence that the rate obtains.
- **It is a Level-0 screen** (D3). It may kill a candidate; it may not certify one. A survivor is
  re-expressed as `net_profit(size)`, built only when a candidate requires it (E1).
- **Impact is unmodelled.** Profit declines nonlinearly with deployed size; the ceiling assumes it
  does not.
- **It says nothing about whether an edge exists.** A capacity ceiling is not a statistical result
  and may not be reported as one.
- **Venue eligibility remains an operator precondition** this repo neither assumes nor asserts.
- **F3 stands.** No broker integration, no live capital, no production executor.


`edge × fillable × frequency − costs` is a **Level-0 screening upper bound** (D3). It may kill a
candidate; it may not certify one.

- Do not annualise a short sample as though opportunity frequency were stationary. Label such
  figures scenario estimates. The "$154/yr" Polymarket NBA figure is pedagogy, not a forecast.
- A surviving candidate is re-expressed as a profit-versus-size curve `net_profit(size)`, because
  fill price, impact, fill probability and edge decay are endogenous to deployed size.
- Build that machinery only when a surviving candidate requires it (E1).
- The hurdle is what the same effort earns elsewhere, not zero.

---

## Class M — Maker rather than taker, and Gate M.0

> **REGISTERED 2026-09-14, before it was built and before any spread or volume number was
> produced.** Runs: `python gatem.py`.
>
> **STATUS: RUN 2026-09-14 — NOT REFUTED.** 4,200 open markets swept, 1,436 in band and quotable.
> Median spread **2.0 ticks**, so the registered condition passes. Gross capture **3.2564%** per
> dollar of flow; ceiling **$29.3M/yr** on the **$532M/yr** of flow in the 902 markets that have
> tick room, against a $104.70 floor.
>
> **The registered condition was the wrong weighting for its own hypothesis.** It weights markets
> equally; the hypothesis is about flow, and **77.4% of flow sits in one-tick markets** where an
> entrant cannot improve the quote. A two-page sample of the volume head returned median 1.0 tick
> and REFUTED. Both readings are reported; the condition is not rewritten after the fact
> (`CORRECTIONS.md` Pass 28.1).
>
> **The constraint moved**: taker capacity was $24.40 and immovable; maker capacity is flow, and the
> binding constraint becomes **adverse selection and queue position**, which this gate does not
> measure. It licenses **Gate M** — an adverse-selection measurement on real trade data — and
> nothing else. It licenses no claim that market making here is profitable. See
> [`GATEM-RESULTS.md`](GATEM-RESULTS.md).

### Why this class exists

Gate 4.0 measured the taker ceiling at **$10.47/yr** on **$24.40** of deployable capital and
established that capacity is the binding constraint. Every measurement in this repository is a
**taker** measurement: the cost model's `half_spread` is charged as a cost on every crossing, and
`maker_fee_coeff` has sat at `0.0` unused.

A maker inverts the largest cost term — the spread becomes revenue rather than expense — and, more
importantly, **changes what the constraint is**. A taker's opportunity set is *visible mispricings*,
which measured $24.40. A maker's is *flow that crosses their quote*, which scales with venue volume.
That is a different quantity, not a larger one, so Class M may not inherit any of Class B's or
Class C's licences and its capacity must be measured on its own terms.

### The hypothesis, stated so it can fail

> **H:** On the reachable open universe, in-band markets quote a spread wide enough for an entrant
> to improve on, and the resulting gross capture per unit of flow is large enough that a plausible
> share of venue volume clears the hurdle.

### Gate M.0 — the dead-on-arrival check

**The primary falsifier is tick room, not spread size.** A market already quoted at **one tick**
offers an entrant nothing: the quote cannot be improved, so the only way in is the back of an
existing queue, and queue position — not spread — then decides whether anything fills. An aggregate
spread that looks attractive while sitting entirely in one-tick markets is a spread that is not
available to a new participant.

| decision | value | why this |
|---|---|---|
| **Primary condition** | the median in-band market must quote **more than one tick** | Room to improve the quote is the precondition for every other maker number meaning anything |
| Price band | `price_in_band`, **applied** | The exclusion Pass 26 found unenforced in every scanner. A 1-tick spread on a 0.4c contract is a 50% relative half-spread and is an artefact, not an opportunity |
| Gross capture | `spread / 2`, net of the maker fee, per contract | What a maker earns buying at bid and selling at ask, **before adverse selection** |
| Floor | the maker ceiling must exceed the measured taker ceiling (**$10.47/yr**) by an **order of magnitude** | Absolute and internally sourced, not a rate — `CORRECTIONS.md` Pass 27.1. Below 10x, a structural change has not changed the structure; it has moved a number while adding machinery |
| Flow | **inverted, never invented** | Venue flow that would cross *our* quote is unobservable without quoting. The gate reports the annual flow required to clear the floor; it does not assume a share |
| Volume units | `volumeNum` **assumed dollars, unverified** | Reported at both readings, as `scanc.py` does with the Kalshi fee (A6, G3) |

### Pre-committed expectation, recorded before the run

**This gate is expected to pass, and passing it is expected to mean very little.** Polymarket does
real volume and quoted spreads on liquid contracts are visible; an aggregate gross-capture figure
will almost certainly look large next to $10.47. That is why the primary condition is tick room
rather than spread size — a condition that can actually fire — and why the decision rule below
licenses only a measurement and never a build.

If this gate is reported as evidence that market making is profitable, it has been misread.
**Everything that determines maker profitability is excluded from it.**

### What is deliberately excluded, and which way each cuts

| excluded | direction |
|---|---|
| **Adverse selection** — you are filled preferentially when the price is about to move against you | Against. This is the whole of maker P&L and it is unmeasured |
| **Queue position and competition** — existing makers are already there | Against |
| **Inventory risk** — an unbalanced book is a directional position | Against |
| **Polymarket's maker rewards** (`rewardsMaxSpread`, `rewardsMinSize` are published) | **For.** So a REFUTED verdict here refutes **spread capture**, not market making with rewards, and must not be reported as the latter |

### Decision rule — written before the numbers

| outcome | action |
|---|---|
| Median in-band spread is **one tick or less** | **REFUTED.** There is no room for an entrant to quote; spread capture is unavailable whatever its size. Class M closes |
| Tick room exists **and** the ceiling clears 10x the taker ceiling | **NOT REFUTED.** Licenses **Gate M — an adverse-selection and queue-position measurement** on real trade data. It licenses no executor, no quoting, and no capital (F3) |
| Tick room exists, ceiling below 10x | **REFUTED.** The structural change did not change the structure |
| Nothing prices | WITHHELD as apparatus (A1, G12) |

### Gate M — Adverse selection and queue position

> **REGISTERED 2026-09-14, before the estimator was written and before any price history was
> fetched for any market in the measured set.** Runs, in order: `python gatem.py --nulls` (the null
> gate), then `python scanm.py` (the measurement).
>
> **STATUS: NULL GATE PASSED, MEASUREMENT RUN 2026-09-14 — NOT REFUTED, AND THE MAGNITUDE OUTRANKS
> THE VERDICT.** Seven null worlds, all PASS, including two at the **95.7% staleness** the real
> series was measured to have. 237 markets, 276,421 pooled observations.
>
> `R(60) = +0.00039`, interval `[+0.00023, +0.00056]` — strictly above zero, so the spread survives.
> Against a median quoted half-spread of `+0.01000` that is **3.9% retained, 96.1% taken by informed
> flow**. The same estimator on an *uninformed* world at the same staleness returns `+0.00928`, so
> the instrument can see a surviving spread; it is not seeing one here.
>
> Gate M.0's `$29.28M/yr` gross ceiling becomes **~$1.14M/yr** net, at a 100% capture rate that is
> impossible when incumbents hold 77.4% of flow at one tick. **The tick test attenuates toward zero,
> which flatters the maker, so NOT REFUTED is the less trustworthy of the two verdicts here.**
>
> Proceeds to Gate 3, whose content for this class is **queue position** — nothing here measures
> whether the fills would arrive. See [`SCANM-RESULTS.md`](SCANM-RESULTS.md) and `CORRECTIONS.md`
> Pass 29.

Gate M.0 established that there is a market to compete in. **This gate asks whether an entrant
would win, and it is the one that decides.** A 3.26% gross spread per dollar of flow is what a maker
collects *if the flow is uninformed*; the whole business of market making is that it is not.

#### The hypothesis, stated so it can fail

> **H:** On in-band markets with tick room, the half-spread a maker captures exceeds the signed
> permanent price impact suffered over the horizon an entrant's inventory would be held.

Failing means informed flow takes more than the spread pays — which is the default expectation for
an entrant with no queue priority, no latency advantage and no flow-internalisation.

#### Decision-rule specification — units, weighting, preconditions

*Written first, per `CORRECTIONS.md` Pass 28.2. Three gates in a row shipped a correct measurement
under a decision rule that was dimensionally wrong, mis-weighted, or silently dropped a standing
precondition. That rule is applied here before anything else is decided.*

| element | value |
|---|---|
| **Units of the threshold** | price units per contract, both sides. `half_spread` and `impact` are the same quantity in the same units, so the comparison is dimensionless and no rate/magnitude confusion is possible |
| **Weighting of the statistic** | **flow-weighted across markets**, and reported unweighted beside it. Gate M.0's defect was weighting markets when the hypothesis was about flow; the same hypothesis is at stake here |
| **Standing preconditions applied** | `price_in_band` (longshot exclusion, Pass 26.1); tick room > 1 tick (Gate M.0 — a market an entrant cannot quote in is not in the population); minimum observation count per market |
| **Primary statistic** | signed permanent impact at the registered horizon, **net of the bounce component**, versus half the quoted spread |
| Horizon | **60 minutes**, with the term structure at 1/5/15/60 reported. Frozen because the shape across horizons is what separates bounce from information |
| alpha | not applicable — this is a deterministic comparison of two measured price quantities, not a significance test. No alpha is spent |

#### The estimator, and why direction is inferred rather than read

Adverse selection is `D_t x (p_{t+k} - p_t)`, where `D_t` is trade direction. Direction is the hard
part and this venue makes it harder:

- **The public feed's own direction flag is refuted as a source.** Dubach 2026 measured it matching
  on-chain truth **~59%** of the time (AXIOMS D6). Using it would produce a biased impact estimate
  from a coin flip.
- **On-chain `OrderFilled` is ground truth** and requires an RPC, log decoding and a new dependency.
  Out of proportion for a gate that can be refuted more cheaply.
- **The tick test** infers direction from the price series alone and is a published method with a
  known error mode. It is what this gate uses, and its weakness is registered here rather than
  discovered later: `D_t` is computed from `p_t - p_{t-1}`, so `D_t` and the subsequent move are
  **mechanically correlated through bid-ask bounce**, biasing impact upward at short horizons.

**That bias is the whole reason the term structure is the statistic rather than a single number.**
Bounce is transient and mean-reverting, so a bounce-driven impact **decays** as the horizon grows.
Information is permanent, so an information-driven impact **persists**. The shape across 1/5/15/60
minutes separates them; a single-horizon number cannot, and would measure the instrument.

> #### Amendment 2026-09-14 — the statistic is the realized half-spread, and the sign above is wrong
>
> **Recorded before the estimator was run on any real or synthetic data**, found while writing it.
>
> Two errors in the paragraphs above. Working the pure-bounce case explicitly: with a constant true
> value `V`, bid `V - s/2` and ask `V + s/2`, a trade at the ask gives `D = +1` and
> `E[p_{t+k}] = V` for **every** `k`, so `E[D (p_{t+k} - p_t)] = -s/2` at every horizon.
>
> 1. **The bounce bias does not decay with the horizon.** It is a constant `-s/2` offset, because it
>    comes from `p_t` sitting on one side of the spread, not from noise in `p_{t+k}`. The registered
>    premise that the term structure separates bounce from information *by decay* is false for this
>    estimator.
> 2. **The sign was backwards.** Bounce biases measured impact **downward** — toward making the maker
>    look more profitable — which is the dangerous direction for a gate whose pass licenses more
>    spend, not the harmless one the registration assumed.
>
> **The fix is to measure the quantity the question is actually about.** Negating it gives the
> standard **realized half-spread**:
>
> ```
> R(k) = mean over trades of  D_t x (p_t - p_{t+k})
> ```
>
> In pure bounce `R(k) = +s/2`: the maker keeps the half-spread, which is the correct answer rather
> than a bias to be corrected. Under informed flow the price moves *with* the trade, so `R(k)` falls
> and can go negative — the maker pays. **`R(k)` already nets gross capture against adverse
> selection**, so no separation of bounce from information is required, and `E[p_{t+k}] = m_{t+k}`
> under uninformed flow makes the traded price an unbiased stand-in for the unpublished midquote.
>
> Adverse selection is then reported as the decomposition `quoted_half_spread - R(k)` rather than
> estimated directly.
>
> **The term structure is retained, with its role corrected**: it no longer separates bounce from
> information, it shows **how fast information arrives**. `R` flat in `k` means uninformed flow;
> `R` declining in `k` means the fills are informed and the horizon decides how much it costs.
>
> **The primary statistic and the decision rule below are restated accordingly:** flow-weighted
> `R(60)` versus zero, with `R(60) <= 0` refuting. Comparing `R` to the half-spread would
> double-count, since `R` is already net. Everything else in this registration — null worlds,
> preconditions, weighting, stopping rule, horizon — stands unchanged.

#### The null gate — runs first, always

**The false-positive generator is bid-ask bounce**, exactly as Gate D registered for convergence. An
estimator that has not been shown to find nothing in a world of pure bounce is measuring its own
sampling (A7).

> #### Amendment 2026-09-14 (second) — the null worlds were labelled for the replaced statistic
>
> **Recorded before the null gate was run.** The amendment above changed the statistic from signed
> impact to `R`, and the worlds below were written for the statistic it replaced. Under `R` they are
> mislabelled: a pure-bounce world returns `R = +s/2`, not `~0`, because **a maker in a bounce-only
> world genuinely profits**. "No harvestable adverse selection" is not the null for this gate — it is
> the *success* case.
>
> **The correct mapping.** The claim under test is maker profitability, so:
>
> | world contains | estimator must report | role |
> |---|---|---|
> | **informed flow** (the spread is taken) | `R <= 0` | **null** — a false `R > 0` here licenses spend on a losing strategy, which is the dangerous direction |
> | **uninformed flow** (the spread is kept) | `R ~ +s/2` | **power** — an estimator reporting losses everywhere refutes everything and is worth nothing |
>
> The worlds listed below are retained, **re-assigned to the power side**, and three informed-flow
> nulls are added: permanent impact above the spread, impact exactly at break-even (the
> discriminating case), and a toxic-minority burst, which is the realistic shape.
>
> **This is the fourth decision-rule defect in four gates** (Passes 26.1, 27.1, 28.1, and this),
> against zero measurement defects. It is further evidence for Pass 28.2 rather than an exception to
> it, and it was caught by the rule that pass extracted.

**Null worlds — reassigned to the power side by the amendment above; uninformed flow, where the
maker keeps the spread and the estimator must report `R ~ +s/2`:**

1. **Pure bounce.** A constant true value; the observed price alternates bid/ask. Any measured impact
   is mechanical. *The discriminating null* — structure impeccable, only the estimator's own
   correlation between `D_t` and the next move stands between it and a false fire.
2. **Random walk, no bounce.** Fills are unbiased; impact must be zero at every horizon.
3. **Random walk plus bounce.** Both mechanisms at once, which is the realistic shape of an
   uninformed market.
4. **Drifting market, uninformed flow.** A genuine trend that trades do **not** predict. Tests that
   the estimator does not read trend as adverse selection.
5. **Wide spread, no information.** Bounce amplitude large relative to the drift, so the naive
   estimator fires hardest here.

**Positive control:** a series with genuinely informed flow — trades that systematically precede a
permanent move. **Generated by a process the estimator was not written against** (AXIOMS G14): Gate
C scored power 1.000 on its own parser's dialect and 0/26 on real text, and a control drawn from the
estimator's own model would repeat that exactly.

**Exhibit:** the naive single-horizon estimator at k=1 on raw trade prices, retained because the size
of its failure is the argument for the term structure.

**Pass — both conditions, per unit, as every gate here:** no null world's measured impact exceeds
chance at the registered horizon, **and** the informed control is detected at least `POWER_FLOOR` of
the time. An estimator that reports zero everywhere passes the first trivially.

#### Stopping rule — binding

Sample the in-band, tick-room universe **once**, to the depth the API reaches, and stop. Do not widen
it because the result disappoints. Below **100 markets with usable history**, the verdict is WITHHELD
as underpowered — *"not enough evidence"*, never *"no effect"* (A1).

#### Decision rule — written before the numbers

| outcome | action |
|---|---|
| Flow-weighted `R(60)` **at or below zero** | **REFUTED. Class M closes, and with Classes A, B and C already closed, the registered programme ends.** Informed flow takes at least the whole spread, which is the entrant's default condition |
| Flow-weighted `R(60)` **above zero**, on ≥ 100 markets | A maker edge is **not excluded** at this venue. Proceeds to Gate 3 (execution realism), which for this class must model queue position — the thing that decides whether the fills arrive at all |
| Gate M's null gate fails | No measurement runs. Fix the estimator; do not tune the worlds (A8) |
| Fewer than 100 markets | WITHHELD |

#### What this gate does not cover, named now

- **Queue position is not measured.** A favourable spread you never get filled at is not revenue.
  This gate measures the cost of the fills you *do* get, not the probability of getting them.
- **Polymarket's maker rewards are excluded**, and cut for. A REFUTED verdict refutes spread capture
  against informed flow, not rewards farming, which is a different hypothesis with a different
  revenue source.
- **Inventory and competitive response are unmodelled**, and cut against.
- **The tick test is not ground truth.** On-chain `OrderFilled` is, and is not used here.
- **Trade prices are not midquotes.** Historical quotes are not published, so the series is what
  traded, and that is the source of the bounce bias the term structure exists to handle.
- **F3 stands.** No broker integration, no live capital, no production executor, no quoting.

---

## Class R — Subsidy capture, and Gate R

> **REGISTERED 2026-09-14, before `gater.py` was written and before any reward score was computed.**
> Runs: `python gater.py`. Method: `principles-20-solutions`, proportionality 4/4, Consensus-backed.
>
> **STATUS: RUN 2026-09-14 — NOT REFUTED on the registered rule, and the verdict is not robust.**
> 120 incentivized markets priced from 1,902 swept; median daily pool **$5**, median competitor
> score **2,336**. Best net on the frozen rule: **+$6,324/yr at 20 contracts, `s = 0`** — negative at
> every larger size (−$28k at 100, −$900k at 2,000).
>
> **The registration double-counts adverse selection** (`CORRECTIONS.md` Pass 31.2): Gate M's `R(60)`
> is already net of it, so charging `0.0096` against a capture of zero charges it twice. Under the
> Gate-M-consistent accounting every distance is positive, `+$8k` to `+$40k`/yr. **The two readings
> disagree in sign at every size above 20.** The frozen rule was run as the verdict and the
> consistent reading reported beside it; a verdict whose sign depends on an accounting choice is not
> a finding, and that is the result.
>
> Two to three orders of magnitude above Class C (`$10.47/yr`) and Gate 3.0 (`~$1,200/yr`), and
> still not a business. **The deciding term — what `own/(own+competitors)` does when an entrant
> arrives — cannot be measured from outside the congestion.** Maker rebates and holding rewards
> remain untouched. See [`GATER-RESULTS.md`](GATER-RESULTS.md).

### Why this is a new class

Classes A, B, C and M all tested hypotheses whose counterparty was an **informed trader**, and all
four were beaten by that counterparty — Class M by a measured 96.1% of the spread. Class R's
counterparty is **the venue**, which pays by published rule rather than by opinion. That is a
different principal cause, so Class R inherits none of the prior licences.

Polymarket runs **three** subsidy programmes, of which this repository has examined zero: liquidity
rewards (paid for resting orders), maker rebates (a share of taker fees, paid on fills), and holding
rewards (`holdingRewardsEnabled`, paid for holding). Gate M.0 recorded rewards as an unmodelled term
that "cuts for" and every gate since has excluded them.

### The mechanism, taken from the venue's published rule rather than a summary

```
S(v, s) = ((v - s) / v)^2 * b        v = max spread, s = distance from midpoint, b = size
Q_one   = scored bids on m + scored asks on m'
Q_two   = scored asks on m + scored bids on m'
Q_min   = max(min(Q_one,Q_two), max(Q_one/c, Q_two/c))    midpoint in [0.10,0.90], c = 3.0
Q_min   = min(Q_one, Q_two)                               midpoint outside it: two-sided required
Q_final = Q_epoch / sum(Q_epoch)_n                        proportional share of the daily pool
```

**Reading the primary source inverted this gate's own premise.** The method run that produced this
registration selected "quote at the `max_spread` edge to earn rewards while minimising fills." The
published formula scores `((v-s)/v)^2`, which is **zero at the edge** and maximal at the midpoint:
rewards pay quadratically more for the tighter quote, which is also the position of maximum adverse
selection. **That tension is the gate**, and it was invisible in the second-hand summary the
candidate was generated against.

### The hypothesis, stated so it can fail

> **H:** There exists a quote distance `s` at which the subsidy earned exceeds the adverse selection
> incurred by resting there, summed over the incentivized market set.

### Decision-rule specification — units, weighting, preconditions

*House rule since Pass 28.2, and Pass 30.2's omission is not repeated: the size is frozen as a curve.*

| element | value |
|---|---|
| **Units** | **dollars per year, absolute.** Never a rate (Pass 27.1) |
| **Weighting** | per-market net, summed; per-market curve reported so no single market carries the verdict |
| **Preconditions** | longshot band (Pass 26.1); tick room > 1; **a published `rewards_daily_rate`** — a market with no pool cannot pay |
| **Primary statistic** | `max over s of [ pool x share(s) - fills(s) x 0.0096 ]`, summed |
| **Adverse selection** | **0.0096/contract, measured by Gate M** — carried as a measured constant, not re-derived |
| **Posted size** | curve over **20 / 100 / 500 / 2000** contracts (C11 — Pass 30.2) |
| **Quote distance** | curve over `s` in tenths of `max_spread`, 0.0 to 1.0 |
| Floor | **$104.70/yr**, unchanged from Gates M.0 and 3.0 so all three compare |

### Competitor share is measured, not assumed

`share(s)` is computed by scoring the **real book** with the venue's own formula — every resting
level within `max_spread` of the midpoint, scored and summed — then `own / (own + competitors)`.
This is the one term that could have been fudged, so it is taken from the same book fetch the other
gates use and never parameterised.

### Pre-committed expectation

Subsidy pools are designed to compensate makers "commensurate with the risk they bear" (Feng et al.
2019), and the prediction-market AMM literature is about **bounding the subsidizer's loss**
(Moallemi et al. 2026; Chen et al. 2007). A pool sized to offset adverse selection does not exceed
it except by accident or by competitor absence. **The expectation is a marginal positive at small
size that vanishes as share normalises against entrants** — a congestion game, not an edge.
Recorded before the number exists.

### Stopping and decision rules — written before the numbers

Sweep once, to the depth the API reaches. Below **20 incentivized markets**, WITHHELD as apparatus.

| outcome | action |
|---|---|
| Best net at any `s` is **≤ 0** | **REFUTED. Class R closes and the registered programme ends** — every hypothesis class tested, none survives |
| Net clears the floor | Class R survives. The next question is competitor response to entry, which is a **new registration**, not licensed here |
| Fewer than 20 incentivized markets | WITHHELD |

### What this does not cover

- **Competitor response.** Your share falls when others enter; the measurement is a snapshot of
  today's competition, not an equilibrium.
- **Maker rebates and holding rewards** are reported where published but not modelled.
- **Quote-and-cancel farming is out of scope** — it is what the liquidity-mining literature calls a
  manipulative practice, and venues detect it. This gate measures honest resting only.
- **Epoch mechanics, the $1 minimum payout, and cancellation** are unmodelled.
- **F3 stands.** No broker integration, no live capital, no production executor, no quoting.

---

## Class F — Funding-rate carry, and Gate F

> **REGISTERED 2026-09-14, before `gatef.py` was written and before any carry P&L was computed.**
> Runs: `python gatef.py --nulls` (the null gate), then `python gatef.py` (the measurement).

### Why this is a new class

Classes A, B, C, M and R all traded **prediction markets**. Class F is a different venue, a
different instrument, and a different economic mechanism, so it inherits none of their licences.

A delta-neutral carry holds spot long against a perpetual short and collects the funding longs pay
shorts. **It is not arbitrage.** Schmeling et al. trace crypto carry to "(i) demand from smaller,
trend-chasing investors seeking leveraged upside exposure and (ii) the limited deployment of
arbitrage capital because of regulatory and margin frictions", and state that taking the other side
"is risky due to **spikes in margins and liquidations amid drawdowns**". **The carry is paid
compensation for bearing crash risk**, and it is the negatively-skewed structure Brunnermeier et al.
documented in FX: smooth accumulation, violent unwind.

### The hypothesis, stated so it can fail

> **H:** On reachable venues, realized funding carry net of four crossings and of liquidation losses
> exceeds the opportunity cost of the capital the position locks, on a sample that contains an
> adverse move.

### Decision-rule specification — units, weighting, preconditions

| element | value |
|---|---|
| **Units** | **return on deployed capital**, plus absolute dollars at a stated capital base. Capital is `spot notional + perp margin`, never notional alone — quoting carry against notional is the single largest inflation vector in the public numbers |
| **A rate is legitimate here, unlike Gate 4.0** | Pass 27.1 refuted comparing a *rate* to a *magnitude*. Here both sides are rates on the **same denominator** (deployed capital), so the comparison is dimensionally sound. The absolute figure is reported beside it anyway |
| **Weighting** | per instrument, reported separately. BTC, ETH and SOL had 15.5%, 24.7% and 34.8% negative-funding periods in the same window — they are not one trade |
| **Preconditions** | venue reachable from the operator's jurisdiction; funding history available; instrument in the liquid set |
| **Design variable (C11)** | **leverage on the perp leg**, curve over 1 / 2 / 3 / 5 / 10. Leverage raises return on capital and lowers the liquidation threshold simultaneously; holding it at one value would hide the entire trade-off |
| Costs | four crossings (buy spot, short perp, cover perp, sell spot) at the venue's taker fee, plus funding paid when the rate is negative |
| Hurdle | `CostModel.settlement_wedge_annual` = **6%/yr** on deployed capital — this repo's own constant, unchanged since Gate 4.0 |

### Measured apparatus limits, recorded before the run

- **`fapi.binance.com` returns HTTP 451 — Unavailable For Legal Reasons** from the operator's
  jurisdiction. The deepest-liquidity venue is legally unreachable. This is an **operator
  precondition** of the kind Gate C refused to assume, and nothing here asserts eligibility to trade
  any venue.
- **OKX caps funding history at ~98 days** (296 records; page 3 returns genuinely empty, verified
  against a retrying fetcher so the limit is not a swallowed error — Pass 9). dYdX publishes hourly
  funding but only ~41 days.
- **Therefore the real sample cannot be guaranteed to contain a drawdown**, and the measurement
  alone cannot answer the question. **The null gate carries the crash discipline.**

### Gate F — the null gate, and it is the whole gate

**The false-positive generator is a sample without an unwind.** Any carry backtest over a calm window
shows smooth accumulation, because that is what the strategy does right up until it doesn't. An
estimator that has not been shown to report a loss in a world that liquidates is measuring the
premium and ignoring the risk it is paid for.

**Null worlds — carry does NOT pay once risk is counted, and the estimator must report a loss:**

1. **Liquidation cascade.** Steady positive funding, then an upward move that breaches the perp
   leg's margin. The discriminating null: the funding column looks perfect throughout.
2. **Bear regime.** Funding flips negative and stays; the carry is paid *by* you.
3. **Margin spike.** A move large enough to force deleveraging at the worst price, short of full
   liquidation.
4. **Costs exceed carry.** Genuine positive funding too small to clear four crossings.

**Power worlds — carry genuinely pays, and the estimator must find it:**

5. Steady positive funding, modest volatility, no breach.
6. A high-funding regime with survivable volatility.

**Exhibit:** the **naive carry sum** — funding totalled with no liquidation model — retained because
the size of its failure in world 1 is the argument for the whole gate.

**Pass — both conditions:** no null world reports a profit above chance on the exact binomial tail,
**and** the power worlds are detected at least `POWER_FLOOR` of the time. An estimator that reports
losses everywhere passes the first trivially.

### Pre-committed expectation

Measured on OKX over the 98 days to 2026-09-14: **BTC +4.55%, ETH +3.26%, SOL +2.26% annualized
gross**, before any cost. **BTC's gross carry is already below the 6% hurdle**, so the expectation is
refutation at every leverage that survives liquidation, and survival only at leverages whose
liquidation threshold a crypto drawdown clears routinely. Recorded before the number exists.

The published figures are not disputed — they are **regime numbers**. Carry has exceeded 40% p.a. in
boom periods. That the reachable window shows 4.55% is itself the finding: **this is a regime
exposure, not a harvest.**

### Stopping and decision rules — written before the numbers

Fetch each venue's history once, to the depth its API reaches, and stop. Below **3 instruments with
usable history**, WITHHELD as apparatus.

| outcome | action |
|---|---|
| Null gate fails | No measurement runs. Fix the estimator; do not tune the worlds (A8) |
| Net return on capital ≤ 6% at every leverage | **REFUTED. Class F closes** |
| Net clears 6% at some leverage **and** that leverage survives the null worlds | Class F survives; the next question is venue eligibility and counterparty risk, which is a **new registration** |
| Fewer than 3 instruments | WITHHELD |

### What this does not cover

- **Counterparty and exchange default.** Pindza measures these as *more damaging than price
  crashes*; FTX is the realized case. Unmodelled and cuts against.
- **Crowding.** Arbitrage capital growth measurably lowers carry returns; the measurement is a
  snapshot of today's competition.
- **Basis risk between venues** if the legs sit on different exchanges.
- **Venue eligibility is an operator precondition** this repo neither assumes nor asserts. Binance is
  451 from here.
- **F3 stands.** No broker integration, no live capital, no production executor.

---

## Class M2 — The subsidised maker, and Gate M2

> **REGISTERED 2026-09-14, before `gatem2.py` was written and before any rebate figure was
> computed.** Runs: `python gatem2.py`.
>
> **STATUS: RUN 2026-09-14 — NOT REFUTED, AND SUBSIDY-DEPENDENT.** Net **$139,450/yr** at 2,000
> posted contracts across 195 markets against a $104.70/yr floor, carried by the **maker rebate**
> (3.6x the spread) and not by the spread or by holding rewards. Holding rewards pay 3.25% on
> capital costing 6% and contribute **−$10,725**. Full result in
> [`GATEM2-RESULTS.md`](GATEM2-RESULTS.md). Class M survives as a *subsidy-dependent strategy* and
> must never be reported as an edge; **subsidy persistence is a new registration and is not
> licensed here.**

### Amendment 1 — two errors in this registration, recorded 2026-09-14 after the run

Recorded rather than silently edited, per the standing rule. **Neither reached the arithmetic**,
because the runner reads each market's live `feeSchedule` rather than the table below.

1. **The rate table is stale in one row.** Live, `sports_fees_v3` pays a **15%** rebate, not 20%,
   and a second sports schedule (`sports_fees_v2`, **0.03 / 25%**) exists that the published table
   omits entirely. Verified across 11 distinct live schedules on 1,445 markets.
2. **"81 of 100 markets sampled are `politics_fees`" is wrong.** Unfiltered the universe is **52%
   sports, 20% politics**; after this gate's own band and tick-room preconditions politics is
   **20 of 195**. The claim below that the 75% overcharge falls on "the dominant category" names the
   wrong category. The correction that survives is stronger and simpler: **0.07 is the maximum of
   every live rate**, so `taker_fee_coeff` overstates costs everywhere and understates them nowhere.

See [`CORRECTIONS.md`](CORRECTIONS.md) Pass 33.1–33.2.

### Why Class M has to be re-opened

Gate M measured that a maker **retains 3.9% of the quoted half-spread** — `R(60) = +0.00039` per
filled contract — and every gate since has treated maker rebates and holding rewards as "excluded,
and cutting for". Examining them changes the arithmetic by an order of magnitude, so the exclusion
cannot stand.

Polymarket runs **three** subsidy programmes and they are structurally different:

| programme | paid for | competition-normalised? | measured |
|---|---|---|---|
| Liquidity rewards | orders **resting** near the midpoint | **Yes** — your share falls as makers arrive | Gate R: knife-edge |
| **Maker rebates** | contracts you were the **maker** for | **No** | this gate |
| **Holding rewards** | **merely holding** an eligible position | No | this gate |

**The rebate's independence from competition is the whole point.** The pool is
`rebateRate x total taker fees` and your share is `your_fee_equivalent / total_fee_equivalent`, so
the two scale together and **your rebate per filled contract is `rebateRate x fee`, whatever other
makers do.** Gate R's congestion game does not apply here.

### The published mechanics, taken from the venue

Taker fee, confirmed identical in shape to `CostModel.fee()`:

```
fee = C x feeRate x p x (1 - p)          C = shares, p = price
```

**Makers are never charged.** `feeSchedule.takerOnly` is `true` on every market inspected, which
retrospectively confirms this repo's `maker_fee_coeff = 0.0` default.

| category | feeRate | rebateRate |
|---|---|---|
| Crypto | 0.07 | 20% |
| Sports | 0.05 | 20% |
| **Finance, Politics, Mentions, Tech** | **0.04** | **25%** |
| Economics, Culture, Weather, Other | 0.05 | 25% |
| **Geopolitics** | **0 — fee-free** | **none: no fee, no rebate** |

**Holding rewards: 3.25% annualised** on eligible position value, sampled hourly, paid daily,
**funded from the Polymarket treasury** and explicitly "variable and subject to change at
Polymarket's discretion."

### The correction this forces on every prior gate

`CostModel.taker_fee_coeff` defaults to **0.07**, described as "the shape of Kalshi's published
trading fee", and every Polymarket cost in Gates B, C, D.0 and 4.0 was charged at it. **81 of 100
markets sampled are `politics_fees` at 0.04** — a **75% overcharge** on the dominant category.

Direction: costs were **overstated**, so those refutations were conservative and stand a fortiori.
Class C's unbanded NOT-REFUTED would be *more* not-refuted. The alpha on those looks is spent and
they are **not re-run**; the error is recorded (`CORRECTIONS.md` Pass 33) and the correct
per-category rate is used here.

### The hypothesis, stated so it can fail

> **H:** With rebates and holding rewards included, a maker's total per-contract economics exceed
> the spread-only figure by enough to clear the floor at a size whose fills are achievable.

### Decision-rule specification — units, weighting, preconditions

| element | value |
|---|---|
| **Units** | **absolute dollars per year** (Pass 27.1), with the per-contract decomposition beside it |
| **Weighting** | per market, summed; per-category reported, because the fee rate and rebate rate both vary by category |
| **Preconditions** | longshot band (Pass 26.1); tick room > 1 (Gate M.0); **`feesEnabled`** — a fee-free market pays **no** rebate, so geopolitics is excluded by arithmetic rather than by choice |
| **Per-contract model** | `RETENTION x s` (Gate M, measured) **+** `rebateRate x feeRate x p(1-p)` (published) |
| **Holding rewards** | 3.25%/yr on position value, applied to capital actually held, **reported separately** — it is a treasury subsidy, not a market edge |
| Size curve (C11) | 25 / 100 / 500 / 2000, as Gate 3.0 |
| Floor | **$104.70/yr**, unchanged from Gates M.0, 3.0 and R so all four compare |

### Pre-committed expectation

At `p = 0.5` in politics the rebate is `0.25 x 0.04 x 0.25 = 0.0025` per filled contract against a
measured spread retention of `0.00039` — **about 6.4x**. The expectation is therefore that total
maker economics land roughly **7x** Gate 3.0's figures, that holding rewards at 3.25% **fail** the
6% capital hurdle on their own, and that the binding constraint reverts to Gate 3.0's queue
question: how much taker flow can actually be filled. Recorded before the numbers.

**And the honest counterweight, recorded now:** holding rewards are a **treasury-funded customer
acquisition subsidy**, variable at the venue's discretion. Maker rebates are funded by fees the venue
chose to introduce and could withdraw. **A subsidy the counterparty can switch off with one decision
is not an edge; it is a promotion**, and any figure resting on it carries a single-decision failure
mode that no amount of measurement can hedge.

### Decision rule — written before the numbers

| outcome | action |
|---|---|
| Total net below the floor at every size | **REFUTED.** Class M closes for good |
| Clears the floor | Class M survives **as a subsidy-dependent strategy**, and must be reported as such — never as an edge. Next question is subsidy persistence, which is a **new registration** and is not licensed here |
| Fewer than 50 markets priced | WITHHELD |

### What this does not cover

- **Subsidy persistence.** Both programmes are discretionary. Unmodelled here and the dominant risk;
  now registered separately as **Class S** below. Gate M2's verdict does not wait on it and does not
  borrow from it.
- **Queue position** still binds — rebates require fills (Gate 3.0).
- **Adverse selection** is already in `RETENTION`; the rebate is additive to it, not a substitute.
- **F3 stands.** No broker integration, no live capital, no production executor, no quoting.

---

## Class S — Subsidy persistence, and Gate S

> **REGISTERED 2026-09-14, before `gates.py` was written and before any cadence, direction or
> hazard figure was computed.** Runs: `python gates.py`.
>
> **STATUS: NOT RUN.**

### Why this class exists

Gate M2 returned **NOT REFUTED at $139,450/yr**, and **77% of the gross is the maker rebate**. The
registered consequence was that subsidy persistence becomes its own registration. This is it.

### The objection to this gate existing at all, addressed before anything is built

**Subsidy persistence is a forecast about a private company's future business decision.** Polymarket
does not publish its treasury, its subsidy budget, or its intentions. No amount of archaeology on
schedule version strings turns that into a measurement, and a gate that implied otherwise would
manufacture the appearance of evidence — the precise failure mode this protocol exists to prevent.

So **this gate does not forecast persistence, and any output claiming to is void.** It measures three
observable things and answers a different, answerable question:

> **How long must the subsidy hold for the strategy to pay back — and is that horizon short or long
> compared with the longest interval over which the venue's terms have actually been observed to
> hold?**

The first half is arithmetic. The second half is a measured interval with a named uncertainty. The
comparison is a *ratio of two quantities in months*, which is commensurable (Pass 27.1) and can fail.

**`NO VERDICT` is a first-class and expected outcome here**, per `kairos.validity` and AXIOMS
G12/A1: an instrument's ceiling is not the world's floor, and "the apparatus cannot see this" is a
result, not a failure.

### The survivorship problem, named before it can be laundered

**Every live schedule is alive. There are zero observed withdrawals.** A cadence measured on a
programme that has never been withdrawn cannot estimate the hazard of withdrawal — it can only bound
it. The registered treatment is the **rule of three**: with zero events in `n` independent
observation units, the 95% upper bound on the per-unit event probability is `≈ 3/n`.

The gate therefore reports an **upper bound on the annual withdrawal hazard**, never a point
estimate, and never a survival probability. If the bound is uninformative (wide enough to admit
near-certain withdrawal), that is the finding and it is reported as such.

### What is already known, declared now so it cannot be re-sold as a finding

From the Gate M2 sweep (1,445 markets, 11 live `feeSchedule` variants) — **already collected, already
published in [`GATEM2-RESULTS.md`](GATEM2-RESULTS.md)**:

| schedule | feeRate | rebateRate | maker's take = `rate x rebateRate` |
|---|---:|---:|---:|
| `sports_fees_v2` | 0.03 | 25% | **0.0075** |
| `sports_fees_v3` | 0.05 | 15% | **0.0075** |
| `crypto_fees_v2` | 0.07 | 20% | 0.0140 |
| `politics_fees`, `finance_prices_fees`, `tech_fees`, `mentions_fees` | 0.04 | 25% | 0.0100 |
| `weather_fees`, `culture_fees`, `economics_fees`, `general_fees` | 0.05 | 25% | 0.0125 |

**The two sports schedules carry an identical maker take to four decimal places** while the taker fee
differs by 67%. If `v2 -> v3` is a temporal revision, the venue raised the taker fee and returned the
maker exactly what it returned before — a **repricing that took the whole increase for the house and
left the maker untouched**.

**That conditional is the entire gate, and it is not yet established.** Both schedules are live
simultaneously (235 and 523 markets), which is equally consistent with two coexisting variants for
different sports products and no temporal succession at all. Determining which is S1's job. Stating
the invariant here means a run that confirms it is confirming a **pre-registered** observation rather
than announcing a discovery (AXIOMS G14 — a pattern found by the process that went looking for it
proves nothing on its own).

### The hypothesis, stated so it can fail

> **H:** The strategy's payback horizon is shorter than the interval over which the venue's maker
> terms have been observed to hold, and observed revisions have not cut the maker's take.

### The three measurements

**S1 — Cadence.** Enumerate live schedules; test whether version suffixes are **temporal succession**
by comparing the market-creation-date distributions of each version cohort. Succession requires
cohorts that are *separated*, not interleaved. If interleaved, there is no succession and no cadence.
Report the observation window per schedule in months, and total **schedule-months** observed.

**S2 — Direction.** For each established succession pair, compute `Δ(rate x rebateRate)` — the change
in the maker's per-contract take. **Weighted by rebate dollars at risk in the Gate M2 run, not by
market count** (Pass 28.1: weighting by the wrong unit passed a condition that the flow failed).

**S3 — Reference class.** Comparable subsidy programmes — exchange maker-rebate schemes, DeFi
liquidity mining, prediction-market maker incentives — and their observed lifetimes at constant
terms. Graded per [`EVIDENCE.md`](EVIDENCE.md). **Expected to be grade B or U**, i.e. hypothesis
source only and never a planning input (A3). It is registered so that its weakness is on the record
before it is consulted, not argued about afterwards.

### Decision-rule specification — units, weighting, preconditions

| element | value |
|---|---|
| **Units** | **months**, on both sides of the comparison. Required-payback-months vs observed-stability-months |
| **Weighting** | rebate **dollars at risk** from the Gate M2 run, never market count (Pass 28.1) |
| **Preconditions** | the Gate M2 universe: longshot band (Pass 26.1), tick room > 1, `feesEnabled`. A fee-free market has no subsidy to lose and is out of scope by arithmetic |
| **Payback model** | months for Gate M2's net to repay build cost **plus** the 6% capital hurdle already charged in Gate M2 |
| **Build cost (C11)** | a **curve**, not a point: 0 / 1 / 3 / 6 person-months at a rate stated in the runner. A design variable is not held at one value |
| **Hazard** | **upper bound only**, by rule of three on schedule-months with zero withdrawals. Never a point estimate |
| Floor | inherited: the strategy must still clear **$104.70/yr** after the payback period, or the question is moot |

### Pre-committed expectation

Two of nine distinct schedule families carry version suffixes, so **if** succession is established
the cadence is likely on the order of **months, not years** — and payback at any non-trivial build
cost will land in the same range. The expectation is therefore that **the ratio is near 1 and the
gate does not cleanly separate**, that the hazard bound is **wide and uninformative**, and that the
honest outcome is **NO VERDICT on persistence** with a usable number only for required horizon.

Recorded before the numbers. **If the run produces a clean separation in either direction, that is
the surprise, and Pass discipline applies: the rule below is not edited afterwards.**

### Decision rule — written before the numbers

| outcome | action |
|---|---|
| Required payback exceeds observed stability at **every** build cost including zero | **REFUTED.** The strategy cannot pay back inside any interval the terms have been observed to hold. Class M2 is re-labelled a decaying promotion |
| Weighted-majority of rebate dollars sit under schedules whose revisions **cut** the maker's take | **REFUTED as durable.** Same re-labelling |
| Payback well inside observed stability **and** no revision cut the maker's take | **NOT REFUTED.** Class M2 stays subsidy-dependent — never an edge — and the binding constraint moves to execution |
| Version suffixes are **not** temporal succession, or fewer than 2 succession pairs | **NO VERDICT.** The apparatus cannot measure cadence. Not a failure of the hypothesis, and **not licence to proceed as if it had passed** |
| Hazard bound admits near-certain withdrawal | Reported as the dominant term whatever else the gate finds |

### Null gate — required before the estimator touches real schedules

Per AXIOMS A7, the estimator must find nothing in worlds built to contain nothing:

- **No-structure world:** schedules with no version suffixes. Must report *no cadence*, not a cadence.
- **Interleaved world:** version suffixes whose creation dates are fully interleaved. Must report
  *no succession* — this is the confound the real data may contain, so the estimator must fail it.
- **Churn world:** schedules revised at random with a maker take drawn independently each time. Must
  **not** report stability.
- **G14 guard:** the null worlds are generated by a process that does **not** share the detector's
  assumptions about how version strings encode order.

Pass requires false-positive rate inside the exact binomial tail **and** power ≥ `POWER_FLOOR`.

### What this does not cover

- **The venue's finances, budget, and intentions.** Unobservable. The dominant term, and no part of
  this gate estimates it.
- **Withdrawal without warning.** A single decision has no cadence; the rule-of-three bound is the
  only honest statement about it, and it is a bound.
- **Regulatory change** to either programme.
- **Competitive response.** The rebate does not dilute, but the spread does, and Gate M2 already
  showed the spread is only 23% of the gross.
- **F3 stands.** No broker integration, no live capital, no production executor, no quoting.

---

## Gate 5 — Paper forward test

> **STATUS: NOT RUN — blocked on Gate 4.**


Live prices, zero capital, frozen model and baseline. Sufficient independent events by the Gate 2
criterion — not by elapsed days. A deadline is project management, not evidence.

---

## Gate 6 — Tiny bounded live mandate

> **STATUS: NOT RUN, AND NOT REACHABLE.** F3 forbids live capital until every prior gate has passed
> in order. Two of them have not been reached and one hypothesis class is rejected outright.


Smallest fundable size. Kill switch armed before the first order. Sizing per `sizing.py`:
uncertainty-shrunk fractional Kelly, hard caps, drawdown halt. No LLM in the order path (D5).

---

## Market-selection preconditions (apply at every gate)

Exclude before any of the above:

- Markets whose resolution a participant could economically move, absent an externally grounded
  manipulation analysis — **fail closed** (D4, A6).
- Ambiguous or dispute-prone resolution criteria.
- Depth below intended size (D1).
- Horizons where our latency makes the opportunity implausible (D2).
- Longshots, where fee structure mechanically worsens post-fee returns.

---

## Execution order after the corrections in `CORRECTIONS.md`

**Freeze feature work (E2).** In order:

1. ~~Run the null-world falsification harness (Gate 0).~~ **DONE — PASSED.**
2. ~~Run a raw-market forecasting adapter against Hindcast.~~ **NOT RUN.** Superseded: Gate 2a found
   no channel for an LLM to add to, and Zhang et al. 2026 measured frontier models losing 16–31% of
   real capital on these venues — leakage-free evidence at a fraction of Hindcast's cost.
3. ~~Run the `q_ref` OOS ablation ladder (Gate 1).~~ **DONE — `q_ref` REJECTED.**
4. ~~Run at least one genuinely contamination-resistant forecasting set.~~ **DONE — Look 3.**
   1,966 fresh events, **Class A forecasting edge REJECTED.**
5. Investigate structural arbitrage (Class B) as a separate non-forecasting hypothesis.
   **IN PROGRESS — Gate B PASSED 2026-09-08; leg-set verification built and validated 2026-09-08.**
   A scanner is licensed as a candidate generator, and the completeness hole Gate B identified is
   closed ([`LEGSET-RESULTS.md`](LEGSET-RESULTS.md)).
   ~~(a) extend the exhaustiveness sample~~ **DONE 2026-09-09 — 512 groups, bound 0.0059, floor ~1%.**
   ~~(b) scan live open groups~~ ~~(c) order-book depth~~ **BOTH DONE 2026-09-09** —
   [`SCANB-RESULTS.md`](SCANB-RESULTS.md). Depth is now the real ask book priced at VWAP-to-fill,
   not a modelled field. First live scan: **no candidate**, and the binding constraint is
   **structural** — 82% of live groups contain a leg that cannot be bought, so the set cannot be
   assembled at any price. Of the 6 completable groups, all cost 3.4–16.3% more than the $1 they pay.

   ~~**Next:** (d) extend discovery beyond the top ~800 open markets by volume. The scan is
   volume-ordered and shallow, and low-attention contracts are exactly where Sethi & Kline and
   Abínzano et al. locate surviving mispricing — so the current null is strongest precisely where an
   edge is least expected.~~ **WITHDRAWN 2026-09-14 — already satisfied when it was written.**
   `scanb.open_neg_risk_markets` sweeps **both** volume orderings across the whole offset-reachable
   universe, and `SCANB-RESULTS.md` records it. The genuine remaining limit is different: Gamma's
   `offset` caps at 2100, so the sweep reaches the universe *offset pagination* reaches, not the
   venue. Past it needs date-windowed discovery for open markets, as Look 3 built for closed ones —
   **not registered, not licensed.** See `CORRECTIONS.md` Pass 26.4.
   (e) Quote persistence remains unmodelled and is Gate 3.
6. **Report survivors and failures before adding code.**

**Surviving hypotheses as of 2026-09-08: Class B only.** Class A is closed at this venue and scale.

For every module proposed after this point: *what surviving experiment requires this?* If the answer
is "a paper says we might need it later," do not build it (E1).

Report: files changed, claims removed or renamed, test results, null-world results, Hindcast raw-`q`
results, `q_ref` ablation results, surviving hypotheses, and **which code can now be deleted**.

No broker integration, live capital, or production executor (F3).
