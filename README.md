# Ordo Kairos

**A falsification-first instrument for deciding whether a prediction-market trading bot is worth
building — and the measured answer, which is no.**

Not a trading bot. Not a framework. It never placed an order, and that was the point.

### The hypothesis

> **A retail participant, with no latency advantage and no private information, can extract a
> risk-adjusted return from event-contract markets that clears the cost of the capital it locks.**

Stated so it can fail, and tested as **eleven separate hypothesis classes** — forecasting skill,
structural arbitrage, cross-venue convergence, market making, subsidy capture, funding carry,
counterparty selection, and new-listing timing — because "can you make money here" is not one
question and fails for a different reason each time.

### Why it exists

The usual way to answer that question is to build the bot and read the brokerage statement. That
answer is accurate, expensive, and arrives late. This is the cheap version: **measure the ceiling
before spending anything**, and refuse to report a number the instrument cannot support.

Seventeen gates, three event-contract venues plus crypto perpetuals, **zero dollars risked**.

### What it is worth to you

- **If you are about to build in this space** — the measured ceilings below are the months of work
  and the capital you do not have to spend to find them out.
- **If you are evaluating someone else's trading bot** — the exhibits here show what the same
  strategy looks like before and after its costs are charged honestly. One estimator reported
  `+4.71%` where the truth was `−0.67%`.
- **If you write quantitative code of any kind** — the reusable part is the machinery, not the
  finance: null-world gating, three-state verdicts, and a corrections log that fails the build.

---

## The answer

| class | hypothesis | measured result |
|---|---|---|
| **A** | A forecaster can beat market consensus | **REJECTED** — 1,966 fresh events, 983 out of sample; effect `+0.00371` failed both the registered α and a 1% materiality floor |
| **B** | Structural (negRisk) arbitrage | **0 of 78** positive |
| **C** | Cross-venue convergence (Polymarket↔Kalshi) | **$10.47/yr** |
| **M** | Maker spread capture | keeps **3.9%** of the half-spread; **96.1%** lost to adverse selection |
| **M2** | Maker rebates + holding rewards | **$139,450/yr** — but **77% is subsidy**, needs ~$100k, and holding rewards are a **net loss** against the capital they're paid on |
| **R** | Liquidity-reward capture | sign flips on an accounting choice |
| **F** | Delta-neutral funding carry | **REFUTED** — best **+2.85%**/yr against a 6% capital hurdle; every higher leverage was liquidated |
| **S** | Does the subsidy persist? | **NO VERDICT** — one revision is not a cadence; annual withdrawal hazard bounded only at **≤94.5%** |
| **K.0** | Is a maker better paid on Kalshi? | **NO VERDICT** — 26.6% of flow with room vs Polymarket's 22.6%, interval straddles |
| **SM.0** | Is a *recreational* counterparty less toxic? (Smarkets) | **NO VERDICT** — half-spread 0.0063 vs 0.005, interval straddles |
| **N.0** | Be the first maker in an empty book | **REFUTED ON CAPACITY** — new listings are 16× wider, 93.7% unquoted, 84× thinner queues, and carry **0.11%** of flow |

**The two constraints that killed everything:** 73–77% of traded flow sits in markets quoted at a
single tick, where an entrant cannot improve the quote; and behind those quotes is a queue up to
6,284 deep. Both were measured on two venues independently.

**The one thing that paid was a subsidy, not an edge** — money the venue chooses to hand out, which
it can stop handing out on a Tuesday.

## Numbers worth stealing

If you are about to build something in this space, these are the figures that would have saved us
the time:

- A maker retains **3.9%** of the quoted half-spread. Adverse selection takes the rest.
- **77.4%** (Polymarket) / **73.4%** (Kalshi) of dollar flow is pinned at one tick.
- New listings carry **0.11%** of flow. The wide window is real and closes before anyone arrives.
- Taker fee is `C × feeRate × p(1−p)`, `takerOnly: true` on **11 of 11** live schedules — makers pay
  nothing, and the published rate table was **stale** the day we checked it.
- Polymarket maker rebate ≈ **3.6×** the retained spread, and unlike liquidity rewards it does
  **not** dilute with competition: pool and share scale together.
- Holding rewards pay **3.25%**/yr on capital. Charge that capital anything reasonable and it is a
  net loss.
- Funding carry: the naive backtest reports **+4.71%** where the truth is **−0.67%**, because it
  never looks at the price path.

## Why believe any of it

Every gate was **registered in `docs/PROTOCOL.md` before it was built** — hypothesis, units,
weighting, preconditions, decision rule, and a pre-committed expectation, all written while the
answer was still unknown. Amendments are recorded, never applied silently.

### The limit of that claim, stated rather than glossed

**Only 2 of 8 gates can prove it from the artifact.** Class C and Class S have a registration commit
that lands *before* the commit adding their runner. The other six — M2, F, R, K, SM, N — committed
registration and implementation **together**, so a reader cannot distinguish "registered first" from
"back-filled to match the result."

The claim is true as a fact about how the work was done. It is **not independently verifiable for
most gates**, and a repository whose entire value rests on pre-registration should say so in its own
README rather than let the reader assume. A falsifier in `tests/test_readme_claims.py` measures the
ratio and will fail if it gets worse; future gates land their registration in its own commit.

What *is* independently checkable: the pre-committed expectations, which are written next to results
that frequently contradict them. Gates K.0 and SM.0 both recorded an expectation that turned out
**directionally wrong**, and Gate S's registration contains four defects the run exposed. Back-filled
registrations do not predict their own failures.

Three pieces of machinery do the actual work, and they are the reusable part:

- **Null-world gating** (`kairos/nullworld.py`) — a pipeline must find **nothing** in worlds built to
  contain nothing before it may touch real data, judged on an exact binomial tail *and* a power
  floor. It caught an estimator reporting profit in **35%** of replications of a world that
  liquidated in **100%** of them.
- **Three-state verdicts** (`kairos/validity.py`) — profit / loss / **no verdict**. Four gates
  returned no verdict and were right to. An instrument's ceiling is not the world's floor.
- **An executable corrections log** (`docs/CORRECTIONS.md`, 39 passes) — every defect this project
  made, recorded, plus a meta-test that **fails the build** if a correction is written in prose
  without a runnable guard.

The corrections log is not an apology section. It is the most useful file here, and the finding it
carries is the one that generalises furthest:

> Across 39 recorded defects, **every single one was in the sentences surrounding the measurement** —
> units, weighting, preconditions, sampling frame, validation regime. **Never in the arithmetic.**
> The maths was always right. What it meant was what broke.

Examples, all caught before they reached a conclusion: a **53% arbitrage** that was pagination
truncation; a **$3,257,641/yr** reward figure computed at the exact point where the published formula
pays zero; holding rewards booked as **+$12,675** when they were **−$10,725**; a tick-room statistic
that read **100%** on a venue purely because its tick was half the size.

## What this does not claim

- It is **not** a claim that no edge exists — only that none of eleven classes cleared a floor at
  retail capital with no latency advantage, on the venues and dates measured.
- Venue mechanics change. A published fee table went stale inside a day during this work.
- No LLM was in any order path, and no order path exists.
- **Nothing here ever traded.** No broker integration, no live capital, no executor.

## Reproduce

Python 3.11+. **Zero third-party dependencies** — standard library only.

```bash
python gatem.py      # maker spread capture and adverse selection
python gatem2.py     # rebates and holding rewards
python gatef.py --nulls && python gatef.py   # funding carry, null gate first
python gates.py      # subsidy persistence
python gatek.py      # Kalshi
python gatesm.py     # Smarkets
python gaten.py      # new listings
python -m unittest discover -s tests   # 681 tests
```

Gates hit live public APIs and are unauthenticated. Figures move between runs as the universe
drifts; the results documents record what was measured on the day.

## Layout

| path | what |
|---|---|
| `docs/PROTOCOL.md` | every registration, in order, with amendments |
| `docs/CORRECTIONS.md` | 39 passes of recorded defects |
| `docs/AXIOMS.md` | the rules the gates are judged against |
| `docs/*-RESULTS.md` | one per gate, 22 of them |
| `kairos/` | the estimators and the null worlds |
| `gate*.py`, `scan*.py` | runners, one per gate |
| `tests/` | 681 tests, including the corrections meta-guard |

## Licence

**Apache-2.0** — see [`LICENSE`](LICENSE). Take the numbers, take the machinery, attribute where it
helps you. The stock copyright placeholder in the appendix is left unfilled, matching the other
Apache-licensed repositories in this org.

## Reading this repository critically

The front page makes claims about itself, and the front page was never gated. So it has falsifiers
too: [`tests/test_readme_claims.py`](tests/test_readme_claims.py) checks every count against the
tree, every headline figure against a results document, the "never traded" promise against every
source file, and the pre-registration claim against git history — where it **fails partially, by
design**, and the README says so above.
