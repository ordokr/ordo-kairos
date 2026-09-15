# Ordo Kairos

**A falsification-first instrument for deciding whether a prediction-market trading bot is worth
building — and the measured answer, which is no.**

Not a trading bot. Not a framework. It never placed an order, and that was the point.

> **Research artifact — not investment advice, not a solicitation, no warranty.** Every figure is a
> dated observation of a named public venue, and this project is unaffiliated with all of them. See
> [`DISCLAIMER.md`](DISCLAIMER.md).

---

## In plain English

**What these markets are.** On sites like Polymarket and Kalshi you can buy a contract that pays
$1 if some real-world event happens — an election result, an interest-rate decision, a basketball
game — and nothing if it doesn't. The price sits between 0¢ and 100¢ and works like the crowd's
estimate of the odds. Because the payouts are simple and the prices are public, a lot of people
look at these markets and think: *a program could make money here.*

**The question.** Could it? Precisely: can an ordinary person — no special speed, no inside
information, an ordinary-sized account — make enough to be worth the money tied up doing it?

**Why I built a measuring instrument instead of a bot.** The usual way to find out is to build the
trading bot, run it for six months, and read the brokerage statement. That answer is accurate,
expensive, and arrives far too late to act on. So I built the thing that measures the *ceiling*
first — the most anyone could make, before the costs are even charged — and never placed a single
trade. If the ceiling is too low, you have your answer for the price of some electricity.

**What it does.** Seventeen experiments, called *gates*, across three betting venues plus crypto
futures. Each one tests a single specific way you might make money: predicting events better than
the crowd, spotting two prices that contradict each other, quoting prices to other traders,
collecting the bonuses the venues pay out, and so on. Each reads live public data, charges every
realistic cost honestly, and returns one of three answers: **it pays**, **it doesn't**, or
**no verdict** — meaning the measurement was too weak to say either way. That third answer is the
unusual one, and four gates returned it. **Zero dollars were risked.**

**What I found: no.** Not one of the eleven strategies cleared the bar. Two facts killed most of
them:

1. **There is no room to compete.** Roughly three quarters of all the money traded sits in markets
   where the price is already as tight as the venue permits. A newcomer literally cannot offer a
   better one.
2. **Where there is room, there is a queue.** Up to 6,284 orders are already waiting ahead of you.

The one thing that *did* pay was not skill. It was a subsidy — money the venue chooses to hand out
to attract traders, and can stop handing out on a Tuesday.

**Why this might be useful to you.**

- **If you were about to build something like this** — the numbers below are months of work and a
  pile of capital you no longer have to spend to find out.
- **If someone is selling you a trading bot** — this shows what one strategy looks like before and
  after its costs are charged honestly. One estimator here reported a **`+4.71%` profit** where the
  truth was a **`−0.67%` loss**. The gap was a single thing it forgot to look at.
- **If you write code that produces numbers** — in any field, not just finance — the reusable part
  is the machinery for not fooling yourself: null-world gating, three-state verdicts, and a
  corrections log that fails the build.

**The finding that travels furthest.** This project logged every mistake it made — 41 rounds of
them. Every single one was in the *words around* the number: what was being counted, over what
period, measured against what — and once, whether evidence had been "destroyed" when it was merely
unreachable. **Not one was in the arithmetic.** The maths was always right. What it meant was what
broke. That is probably true of your numbers too.

---

### The hypothesis

Stated formally, so that it could fail:

> **A retail participant, with no latency advantage and no private information, can extract a
> risk-adjusted return from event-contract markets that clears the cost of the capital it locks.**

Tested as **eleven separate hypothesis classes** — forecasting skill, structural arbitrage,
cross-venue convergence, market making, subsidy capture, funding carry, counterparty selection, and
new-listing timing — because "can you make money here" is not one question, and it fails for a
different reason each time.

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
| **S** | Does the subsidy persist? | **NO VERDICT** — one revision is not a cadence; the sample bounds the annual withdrawal hazard no tighter than **≤94.5%**, which is to say it is uninformative |
| **K.0** | Is a maker better paid on Kalshi? | **NO VERDICT** — 26.6% of flow with room vs Polymarket's 22.6%, interval straddles |
| **SM.0** | Is *recreational* order flow less adversely selected? (Smarkets) | **NO VERDICT** — half-spread 0.0063 vs 0.005, interval straddles |
| **N.0** | Be the first maker in an empty book | **REFUTED ON CAPACITY** — new listings are 16× wider, 93.7% unquoted, 84× thinner queues, and carry **0.11%** of flow |

**The two constraints that killed everything:** 73–77% of traded flow sits in markets quoted at a
single tick, where an entrant cannot improve the quote; and behind those quotes is a queue up to
6,284 deep. Both were measured on two venues independently.

**The one thing that paid was a subsidy, not an edge** — money the venue chooses to hand out, which
it can stop handing out on a Tuesday.

## Numbers worth taking

If you are about to build something in this space, these are the figures that would have saved us
the time:

- A maker retains **3.9%** of the quoted half-spread. Adverse selection takes the rest.
- **77.4%** (Polymarket) / **73.4%** (Kalshi) of dollar flow is pinned at one tick.
- New listings carry **0.11%** of flow. The wide window is real and closes before anyone arrives.
- Taker fee is `C × feeRate × p(1−p)`, `takerOnly: true` on **11 of 11** live schedules — makers pay
  nothing, and the published rate table **differed from the live schedule** on the day we checked.
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

**Only 2 of 8 gates can prove it from the artifact — and `main` is not where you check.** Class C
and Class S have a registration commit that lands *before* the commit adding their runner. The other
six — M2, F, R, K, SM, N — committed registration and implementation **together**, so a reader
cannot distinguish "registered first" from "back-filled to match the result."

`main` is a single squashed commit and cannot carry that proof. The 21-commit development history is
preserved on the tag [`provenance/pre-squash`](https://github.com/ordokr/ordo-kairos/tree/provenance/pre-squash),
which a default `git clone` fetches. Check it yourself:

```bash
git log provenance/pre-squash --diff-filter=A --format=%H -- gates.py       # runner
git log provenance/pre-squash --format=%H -S 'Class S' -- docs/PROTOCOL.md  # registration
```

The registration hash is the older of the two. Same for `gated.py` / `Class C`.

The claim is true as a fact about how the work was done, and **not independently verifiable for six
of eight gates**. A repository whose entire value rests on pre-registration should say so in its own
README rather than let the reader assume. A falsifier in `tests/test_readme_claims.py` reads the tag
— not `HEAD` — and fails if the ratio moves in either direction, or if the tag goes missing.

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
- **An executable corrections log** (`docs/CORRECTIONS.md`, 41 passes) — every defect this project
  made, recorded, plus a meta-test that **fails the build** if a correction is written in prose
  without a runnable guard. Pass 41 records this log correcting its own diagnosis in Pass 40.

The corrections log is not an apology section. It is the most useful file here, and the finding it
carries is the one that generalises furthest:

> Across 41 recorded defects, **every single one was in the sentences surrounding the measurement** —
> units, weighting, preconditions, sampling frame, validation regime, and once the word "destroyed".
> **Never in the arithmetic.** The maths was always right. What it meant was what broke.

Examples, all caught before they reached a conclusion: a **53% arbitrage** that was pagination
truncation; a **$3,257,641/yr** reward figure computed at the exact point where the published formula
pays zero; holding rewards booked as **+$12,675** when they were **−$10,725**; a tick-room statistic
that read **100%** on a venue purely because its tick was half the size.

## What this does not claim

- It is **not** a claim that no edge exists — only that none of eleven classes cleared a floor at
  retail capital with no latency advantage, on the venues and dates measured.
- Venue mechanics change. A published fee table and the live schedule differed inside a day during
  this work — a fact about how fast these markets move, not an allegation against anyone.
- No LLM was in any order path, and no order path exists.
- **Nothing here ever traded.** No broker integration, no live capital, no executor.
- It is **not** investment advice, a solicitation, or a suggestion that you open an account
  anywhere. See [`DISCLAIMER.md`](DISCLAIMER.md).

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
python -m unittest discover -s tests   # 686 tests
```

Gates hit live public APIs and are unauthenticated. Figures move between runs as the universe
drifts; the results documents record what was measured on the day.

## Layout

| path | what |
|---|---|
| `docs/PROTOCOL.md` | every registration, in order, with amendments |
| `docs/CORRECTIONS.md` | 41 passes of recorded defects |
| `docs/AXIOMS.md` | the rules the gates are judged against |
| `docs/*-RESULTS.md` | one per gate, 22 of them |
| `kairos/` | the estimators and the null worlds |
| `gate*.py`, `scan*.py` | runners, one per gate |
| `tests/` | 686 tests, including the corrections meta-guard |

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
