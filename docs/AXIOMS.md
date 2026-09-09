# Ordo Kairos — Axioms

Standing rules that outrank convenience, deadlines, and elegance. Each is numbered and stable:
cite them by number in code, commit messages, and reviews. Adding one requires evidence; removing
one requires a falsifier, recorded in [`CORRECTIONS.md`](CORRECTIONS.md).

Evidence for each is in [`EVIDENCE.md`](EVIDENCE.md). The operating procedure they govern is
[`PROTOCOL.md`](PROTOCOL.md).

Last revised 2026-09-08, after the second contrarian pass.

---

## A — Epistemic

**A1. The null decision is kill.**
Absence of evidence of an edge is not evidence of an edge. "Not enough evidence yet" and "the edge
is false" are different verdicts and must be reported differently, with power stated.

**A2. Nothing in this system has epistemic privilege.**
Every benchmark is an estimator with uncertainty — including the market reference. Prediction-market
prices are equilibrium objects shaped by beliefs, risk aversion, wealth, liquidity, structure,
time-to-resolution, and even trading order; there is no uniquely recoverable "market belief" behind
the quote. Name benchmarks as estimators (`q_ref`), never as truth (`q*`, "fair probability").

**A3. A claim is only as strong as its weakest cited source.**
A zero-citation preprint reporting one month of one deployment is a **hypothesis source**, not
evidence. Label it so at the point of use.

**A4. Direction and magnitude are separate claims.**
A replicated direction does not license a reported effect size. Where a paper's magnitude has moved
across versions or been corrected, cite the direction and refuse the number.

**A5. In-sample demonstration is never evidence of out-of-sample superiority.**
A transformation fitted on data and then scored on that same data demonstrates that the code runs.
It demonstrates nothing else, and must never be captioned as justification.

**A6. "We did not measure it" is not evidence of safety.**
Unmeasured risk fails closed. Never invent a safety factor to make an unknown appear measured.

**A7. A system that cannot find nothing in a null world cannot be trusted to find something in a
real one.**
Falsify the instrument before using it. This axiom ranks above all strategy discovery.

**A8. Do not tune the falsifier until the system passes it.**
Adjusting a null world because the pipeline failed it converts the test into a formality.

---

## B — Causal order

**B1. The order is fixed:**

```
incremental information over q_ref → economic edge after friction → capacity → sizing → wealth path
```

Never `sizing → edge`.

**B2. Sizing governs the wealth path conditional on an edge; it cannot create one.**
Growth, drawdown and ruin are downstream of sizing. Expected value is not. Any guarantee attached to
a betting rule carries an antecedent (`p` beats `q` *and* liquidity suffices) — the antecedent is the
whole problem.

**B3. Research is a cost centre, not an edge.**
It is budgeted where it subtracts. Cheap hypothesis generation makes this worse, not better.

**B4. At retail scale, selectivity is the binding constraint, not speed.**
Optimise speed of falsification, not microseconds to market.

**B5. Do not collapse distinct frictions into one number.**
Informational benchmarking and execution economics are separate concerns. Correcting a friction
into the probability benchmark and then charging for it again in the cost model double-counts it.

---

## C — Measurement

**C1. The primary score is pre-registered before any result is seen.**
Primary: **log score** — local, information-theoretically interpretable, and aligned with the
log-utility (Kelly) frame already in use. Brier and its calibration/refinement decomposition are
diagnostic only. Changing the primary after seeing results is a forking path, not an insight.

**C2. ROI measures profitability and does not measure skill.**
It is reported and never selected on.

**C3. Rows are not observations.**
Count independent information. Twenty contracts on one election are not twenty observations, and
dependence also runs *across* nominal events through shared news regimes, participants, information
sources, and liquidity shocks.

**C4. A conservative cluster count is a planning heuristic, not an inference procedure.**
`n_eff` may gate eligibility. It must not be handed to a significance formula as if it were an IID
count. Inference uses dependence-aware resampling at the event/block level.

**C5. Logging trials does not neutralise adaptive overfitting.**
Experiment 417 exists because the agent saw 1–416. Logging is necessary and insufficient.

**C6. A holdout queried more than once is training data.**
The sealed final holdout is queried exactly once, after everything is frozen. No agent and no human
sees repeated final-holdout scores.

**C7. Sequential code order does not establish statistical orthogonality.**
Applying transformation X before Y prevents ambiguity about execution order. It does not prevent Y
from re-learning what X removed. Only an out-of-sample ablation can settle that.

**C8. Ensemble independence is a measurement, not a naming convention.**
Different vendor names do not imply independent information. Measure pairwise forecast-error
correlation and report effective forecaster count before claiming diversity.

**C9. Complexity must earn its place out of sample.**
Where a simpler baseline is not beaten reproducibly on held-out data, the simpler one wins and the
complex one is deleted.

**C9a. "Deleted" means removed from the live path, not erased from the record.**
A retirement rule must name the **hypothesis** it retires and the **path** it retires it from. Naming
a file instead is a proxy, and the proxy fails the moment one module serves two hypothesis classes —
`baseline.py` held a rejected Class A transformation and a live Class B carry model, so deleting it
would have retired a hypothesis nobody had tested. Retire by removing the rejected thing from the
public surface and fencing it with a test that fails when a new consumer appears; keep the code that
produced a recorded result runnable, because a result whose code has been deleted is an assertion,
not a result. Erasure is only correct where the artifact is *itself* the hazard (a secret, a live
credential), never where it is merely refuted.

**C10. Cutting the sample into strata is a search, whatever it is called.**
Reporting the band that worked is selection, and the winning band's own p-value is not a p-value.
Strata must be frozen from external evidence before the run, corrected against the distribution of
the maximum, and the cut points are frozen too — moving a boundary after seeing a result is a search
over cut points that no correction on the strata covers.

**C11. A design variable held at one value has not been tested; it has been assumed.**
Every result is conditional on the values the apparatus happened to fix. When the literature says a
quantity varies with X and the whole sample sits at one X, the finding is about that X and the
generalisation is unearned. Measure the distribution of every design variable before interpreting an
average over it.

**C12. An average over a sample where most rows carry no information measures the dilution.**
Rows on which the benchmark is nearly certain and nearly right contribute almost nothing to a mean
score difference while contributing fully to its denominator. Low effect size and low power can be
properties of what is being averaged over rather than of the effect, and the two are distinguishable
only by looking at the composition of the sample.

---

## G — Apparatus validity

*Added 2026-09-08 from a count, not an intuition. Of the defects recorded in
[`CORRECTIONS.md`](CORRECTIONS.md) during **execution** (Passes 4–9), roughly **eighteen were
apparatus and three were inference**. The statistical machinery — clustering, bootstrap, sealed
holdouts, multiplicity correction — has not yet returned a wrong answer. The instruments feeding it
have, constantly. Before this group the axioms held 13 measurement rules and none about the
instrument, which put the discipline almost entirely where the mistakes were not.*

**G1. The apparatus is the least-tested code in the project, and it is where the errors are.**
A probe written in thirty seconds to answer a question decides that question. Budget scepticism by
where defects actually occur, not by where the intellectual difficulty feels greatest.

**G2. Re-probe every decisive result with a second method.**
This has paid four times: a 403 that `curl` answered 200; `fetch_history` handed a market dict
instead of a token id, returning zero admissions at every lead; a "paginate deeper" lever that did
not exist; three quarters reported empty that were HTTP 500. A decisive *negative* needs this as
much as a decisive positive — an apparatus fault and a real finding look identical.

**G3. No runner may announce a verdict without first asserting its own validity precondition.**
If the best obtainable result in a unit is itself undetectable, a comparison run there measures the
unit and not the instruments. Implemented once in [`kairos/validity.py`](../kairos/validity.py) —
never re-implemented per runner, which is exactly how it was lost between Pass 4 and Pass 9.

**G4. A validity precondition is evaluated per unit, never in aggregate.**
Guarding on the best ceiling across units lets a dead unit hide behind a healthy one and still
contribute its ordering to the verdict.

**G5. A swallowed error becomes a fact, and a cached one becomes permanent.**
"Measured zero" and "failed to measure" must never be the same value (A6). Returning `[]` on an
exception turned three broken quarters into "no markets resolved then"; *caching* `[]` on an
exception turned one transient failure into a market silently excluded from every future run.
**Never cache a failure.** The cost is one re-fetch; the alternative is undetectable.

**G6. A control must contain the hypothesis it names, in the variables the thing under test can
see.** A banded signal defined on the latent truth, while every protocol observes only the quoted
price, is a signal concentrated in a band nothing can condition on. Such a control fails quietly:
every number it produces looks plausible.

**G7. A passing test is evidence only about the property it asserts.**
The test guarding G6 passed throughout the defect. It checked *how much* of the range was mispriced
and never whether the mispricing was **visible**.

**G8. A correction that is not executable will recur.**
G0.2 was recorded in prose in Pass 4, with its fix described, and re-committed in Pass 9 — because
the fix had been implemented as a property of one class rather than as something a new runner
inherits. [`tests/test_regressions.py`](../tests/test_regressions.py) encodes recorded corrections as
tests, and its own meta-guard fails when a new execution pass is added with nothing guarding it.

**G9. Cached inputs are part of the apparatus.**
If the cache is volatile, results are unreproducible — and where an API paginates by a moving key,
re-fetching returns a *different* sample rather than the original one, so the loss is silent
substitution rather than absence. Runtime state belongs somewhere durable (F1), and a dataset whose
identity matters gets a reconstruction check that voids the run on mismatch.

**G10. A gate must report *why* it refused, not only that it did.**
Gate C's first run reported 0.000 in every null world and PASS while the matcher was declaring two
markets with different strikes to be the same event. The only visible trace was the refusal-reason
column: one world was being refused 386/400 times for the reason it was designed to test and 14/400
for a different reason, because a parser bug had deleted the evidence on one side. An aggregate rate
cannot distinguish a check that works from a check that is accidentally shadowed by another one, so
a refusal for the wrong reason reads as a pass. Count the reasons, not just the refusals — this is
G7 applied to a gate rather than to a test.

**G11. A guard whose precondition is the thing it guards against goes inert exactly when it starts
mattering.**
Written twice in this repo, one pass apart: "while the protocol says the runner has not been built,
assert it does not exist." Building the runner falsifies the precondition, the guard early-returns
forever, and what is left looks exactly like a passing check. State the invariant with no escape
branch instead — *exactly one status marker is present, and the artefact exists if and only if the
status says so* — so that whichever way the world moves, one half of the assertion is live.

**G12. A count fixed by an apparatus limit is not a measurement.**
The cross-venue sweep examined 8.7M candidate pairs and verified zero. That zero was not a fact about
how many events the two venues share: one venue publishes no determination instant at all, so no pair
*could* verify. When a result is guaranteed by construction, say so where the number is reported —
otherwise the next reader takes an instrument's ceiling for the world's floor (A1, G4).

**G13. From inside a blocked measurement, "the instrument is missing" and "the thing is not there"
look identical. Only building the instrument tells them apart.**
Pass 19 diagnosed the cross-venue zero as an apparatus limit and named the missing extractor. That
diagnosis was itself a hypothesis, and Pass 20 tested it the only way available: it built the
extractor, which worked — and then showed the pairs it unblocked were genuinely different events.
The diagnosis was wrong and no amount of further reasoning about the refusal funnel would have said
so. A blocked measurement licenses building the instrument, never asserting what would have been
found with it.

**G15. A label applied to a group asserts a homogeneity nobody checked.**
Adjudicating by group is right - repeating a judgement per member makes it drift - but the group key
names one side of the join, and the other side is not uniform. The first cross-venue alignment table
labelled 234 pairs from event-level exemplars and **40% were false pairs**: BRICS paired with OPEC,
Trump with Gianni Infantino, a Billboard chart with a Spotify one. Every member must earn the group's
label by a mechanical per-pair check, and a group whose outcomes cannot be checked mechanically is
refused whole rather than trusted.

**G14. A gate reports precision and power, and they are not equally trustworthy.**
Null worlds are adversarial by construction: the author is trying to break the instrument, so a low
false-positive rate is earned. The positive control is only as adversarial as the author's
imagination, and when the control is *generated* by the same model of the world the instrument was
*written* against, its power number measures the instrument against itself. Gate C scored 0.000 on
nine adversarial nulls and 1.000 on its own dialect; measured against real venue text, recall was
**0/26**. Precision transfers out of a null world. Power does not — it must be measured against
samples nobody on this side of the gate wrote.

---

## D — Execution and market selection

**D1. An edge you cannot fill at size is not an edge.**

**D2. Observable latency is not exploitable latency.**
A measurable lead-lag can be real and still lose money after costs.

**D3. Capacity and cost are endogenous to deployed size.**
A scalar `edge × capacity × frequency` is a **screening upper bound**. Real economics is a
profit-versus-size curve. Do not annualise a short sample as though opportunity frequency were
stationary, and do not present a screen as a forecast.

**D4. Never trade a market whose resolution a participant could economically move.**
Manipulability of the settlement reference is the disease; a short horizon is one symptom. Absent an
externally grounded manipulation analysis, exclude — per A6.

**D5. No LLM in the order path, ever.**
The LLM proposes relationships, hypotheses, and structure. Deterministic, tested code verifies and
decides. An LLM may never declare a trade executable.

**D6. Reuse the benchmark; do not rebuild the simulator.**
A conservative scalar cost model is a screen for killing candidates cheaply, never a validator.
Execution realism comes from replay against real book, fee, fill and settlement semantics — and any
such benchmark is itself narrow until shown otherwise.

---

## E — Build discipline

**E1. Every proposed module answers: "what surviving experiment requires this?"**
"A paper suggests we may need it later" is not an answer. Build it when an experiment blocks on it.

**E2. Freeze feature work until the existing pipeline has been run.**
Architecture accumulating ahead of evidence is the failure mode this project was created to avoid.

**E3. Prefer the smallest coherent change.**
Do not create a parallel implementation to satisfy a correction, and do not mass-rename blindly —
inspect references first.

**E4. Two competing hypotheses beat one theoretically-chosen hypothesis.**
Where the evidence does not decide between candidate edge classes, run them against the same
evidence machinery and let them compete.

---

## F — Non-negotiable operational constraints

**F1. No secrets, positions, PnL, or account identifiers inside this repo.**
Runtime state resolves to `$ORDO_KAIROS_STATE`, outside `C:/src`. Every repo in that tree is
publish-eligible. Enforced in `kairos/state.py`, not by comment.

**F2. Zero third-party dependencies in the decision core.**
It is scalar math and must port to Rust unchanged in structure.

**F3. No broker integration, live capital, or production executor** until the protocol in
[`PROTOCOL.md`](PROTOCOL.md) has been passed in order.
