# Ordo Kairos — Corrections Log

Append-only record of claims this project made and then had to withdraw, plus the status of every
outstanding corrective instruction. Its purpose is anti-drift: a refuted claim recorded here must
not be silently re-asserted by a later session or agent.

Newest pass at the top.

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
  Mitigation: `ORDO_KAIROS_STATE` set to `C:/Users/Administrator/.cache/ordo-kairos`, outside both
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
