# Ordo Kairos — Specification

**Status:** superseded as a status document. This file records the original design intent and the
end that governs it, both still current. For what was actually measured, and the verdict, see
[`README.md`](README.md) and [`docs/PROTOCOL.md`](docs/PROTOCOL.md). The repository now sweeps live
public APIs across three venues; it still holds no capital and places no orders.

---

## 0. The end (governs everything below)

> **Rapidly falsify competing sources of market edge.** Establish whether any forecaster carries
> information beyond a friction-adjusted market baseline `q*`; whether that information survives
> realistic execution; whether it is executable at meaningful **capacity**; and fund nothing until it
> survives adversarial validation.

Not "build a trading bot," and not "find an event-contract strategy" either — prejudging where the
profit must come from is how you end up automating an edge that was never there. If the gate says kill,
the project ends and that is a success of the method.

**On the deadline.** 30 days is a project-management constraint, not a statistical one. Elapsed time is
not evidence. The statistical unit is **independent informational trials** (§4), because twenty contracts
on one election are one observation, and a hundred parameter mutations against one holdout are not a
hundred confirmations.

---

## 1. What the literature forced us to change

The brief was "maximize speed of execution and profitability." The evidence inverts the first half.

### 1.1 Naive agent trading is a measured, named failure

| Study | Setup | Result |
|---|---|---|
| KellyBench (Grady et al. 2026, arXiv 2604.27865) | Frontier LLMs, sequential EPL season, told to maximise bankroll, given odds + advanced stats | **All models lose money.** Best −8%. **Several hit ruin.** Claude Opus 4.6 strategy rubric **26.5%** vs human baseline |
| Prediction Arena (Zhang et al. 2026, arXiv 2604.07355) | 6 frontier models, **real capital**, $10k each, 57 days, live Kalshi + Polymarket | Kalshi **−16.0% to −30.8%**. Polymarket −1.1% avg. **"Research volume shows no correlation with outcomes"** |
| StockBench (Chen et al. 2025, arXiv 2510.02209) | LLM agents, multi-month equity trading | Most **fail to beat buy-and-hold** |
| FINSABER (Li et al. 2025, KDD) | LLM timing strategies, 2 decades, 100+ symbols | Reported advantages "deteriorate significantly"; conservative in bulls, aggressive in bears |
| KTD-Fin (Zhu et al. 2026, arXiv 2605.28359) | Leakage-controlled, Barra attribution | Returns "largely explained by passive market and style exposure, **limited evidence of persistent stock-selection alpha**" |

**But "LLMs cannot forecast" is too strong**, and the earlier draft overreached. PolyBench (Cheng et al.
2026, arXiv 2604.14199) ran seven models on 38,666 timestamp-locked Polymarket markets with order-book
execution simulation: **two of seven were profitable** — MiMo-V2-Flash at **17.6%** confidence-weighted
return, Gemini-3-Flash at **6.2%** — while five lost "despite uniformly high stated confidence."

The correct conclusion is therefore narrower and more useful:

> **A model's forecasting competence is an empirical hypothesis to be tested per model. A model's
> discretion in execution is not — it is eliminated.**

AlphaForgeBench (Zhang et al. 2026, KDD, arXiv 2602.18481) reaches the same architecture independently
and explains why: LLMs as direct traders show "extreme run-to-run variance… inconsistent action sequences
even under strictly deterministic decoding, and irrational action flipping," which it attributes to
stateless autoregressive architectures. Its fix is to recast the LLM as a **quantitative researcher
emitting an executable strategy**, evaluated deterministically. That is this repo.

One meta-finding sets the bar for reading any positive result in this literature. The Agentic Trading
survey (Xia et al. 2026, arXiv 2605.19337) coded 77 studies: of the 19 with closed-loop evaluation,
**1/19 reports an explicit transaction-cost model**, 1/19 documents survivorship handling, and **no study
reaches R3 reproducibility**. Most reported LLM trading alpha has never been costed.

### 1.2 The causal order — and what sizing is *not*

An earlier version of this spec called `(p, q) → stake` "the principal cause of PnL." **That was an
inversion.** Sizing governs the *wealth path* conditional on an edge — growth, drawdown, ruin. It cannot
manufacture expected value from a forecast carrying no information the market lacked. The order is:

```
incremental information over q*  →  economic edge after friction  →  capacity  →  sizing  →  wealth path
```

never `sizing → edge`. Gu et al.'s guarantee is explicitly conditional: positive expected profit *whenever
`p` beats `q` under a strictly proper scoring rule **and liquidity suffices***. The antecedent is the whole
problem. Establishing it is the job of `baseline.py` + `score.py`, which rank **above** `sizing.py`.

| Study | Finding |
|---|---|
| Walsh & Joshi 2023 (Mach. Learn. Appl.) | Selecting on **calibration** rather than accuracy raises betting ROI. **Direction only — the magnitude is not usable.** arXiv 2303.06021 reports +110.42% vs +2.98%; the journal version reports +34.69% vs −35.17%; a **2025 corrigendum** (DOI 10.1016/j.mlwa.2025.100627) records errors "discovered in the original implementation" during modularisation and unit testing. Three versions, three magnitudes, one correction. The direction is independently supported by Hubáček et al. 2019 and Wunderlich et al. 2026 |
| Gu et al. 2026 (arXiv 2607.06166) | On CLOB venues "informed forecasters routinely lose money while uninformed strategies profit on heuristics." Proves a **"proper betting"** rule on (p, q) is *essentially the only* strategy with a robust profit guarantee. Live Kalshi month: **+80.33% ROI, Sharpe 3.35** |
| Galekwa et al. 2026 (IEEE Access) | Betting funds with **accurate models** failed for lack of sizing discipline. Uncertainty-adjusted Kelly: ruin **78% → <2%**, retaining **85%** of growth |
| Baker & McHale 2013 (Decis. Anal.) | Under parameter uncertainty, bet size must be **shrunk**; shrunken Kelly beats raw Kelly out-of-sample |
| MacLean et al. 2011 | Full Kelly: "a sequence of bad scenarios can lead to very poor final wealth" regardless of edge |
| Wunderlich et al. 2020 (Int. J. Forecasting) | **Betting ROI is not a valid measure of accuracy** — positive returns arise randomly and systematically without a superior model |

**Conclusion:** the map `(p, q) → stake` is the principal cause of PnL. The forecast is instrumental.
We build the sizing function first, to a higher standard than anything else.

### 1.3 Speed is a means-end inversion at our scale

Cheng et al. 2026 (arXiv 2605.00864) reconstructed **75M order-book snapshots over 173 Polymarket NBA
games**:

- Single-market arbitrage: **7 executable episodes**, median duration **3.6 seconds**
- Combinatorial: 290 episodes, median return **101 bps**
- **76.9% of opportunities capped at ~14.8 shares** of executable size
- Verdict: "confining risk-free extraction strictly to the **retail scale**"

A Rust executor that wins a 3.6-second race to place a **$15** trade is precisely `wisdom-causes-order.md`
**E1 Means-End Inversion**. Speed is not the binding constraint. **Selectivity is.**

### 1.4 The only defensible use of an LLM here

AIA Forecaster (Alur et al. 2025, arXiv 2511.07678) is the state of the art:

- Matches **human superforecasters** on ForecastBench
- **Underperforms market consensus** on liquid prediction markets
- **But an ensemble of forecaster + market consensus beats consensus alone** — "provides additive information"

So the LLM is never the forecast. It is a **bounded adjustment to the market price**, and it must earn
its blend weight empirically or the weight goes to zero.

Two more architecture constraints, both measured:

- **No debate.** Kota 2026 (arXiv 2605.30802), 1,189 Kalshi questions: independent aggregation with
  confidence-weighted voting = **83.43%**; **deliberative consensus collapses to ~76%, below every single
  model** — "confidently wrong models flip correct ones."
- **Abstain by default.** Same study: auto-resolving **only unanimous, high-confidence** items yields
  **97.87% accuracy on 47%** of the set. Selectivity is where the accuracy lives.
- **Research is a cost, not an edge.** Page et al. 2017 (Games Econ. Behav.): traders **over-acquire**
  information and "informed traders on average obtain **negative profits net of information costs**."
  Confirmed independently by Prediction Arena's null result on research volume.
- **Never trust self-reported confidence.** Cash et al. 2025 (Mem. Cogn.): LLMs are overconfident and,
  unlike humans, **fail to adjust confidence based on past performance**. Calibration must be external and
  statistical.

---

## 2. Excluded by construction

Each exclusion is a paper, not a preference.

| Excluded | Evidence |
|---|---|
| **Any market whose resolution a participant at our scale could economically move** — the general rule; sub-15-minute price-settled crypto (the starred `5min-btc-polymarket` strategy) is one instance | Dai et al. 2026 (arXiv 2606.31675): after Polymarket's 5-min BTC launch, settlement-time spot flow spikes and reverses; **"manipulators capture a large amount of profit, mostly from retail."** Absent in 15-min contracts. The horizon is a symptom; **manipulability of the settlement reference is the disease.** `gate.py` fails closed when the cost to move settlement is unmeasured |
| **Short-horizon crypto lead-lag generally**, not just 5-minute | OpenMarket (Young 2026, arXiv 2607.26245) built a synchronized Polymarket–Binance dataset and measured Polymarket responding to large Binance moves at a **~347 ms median** — yet a 43-feature walk-forward model still produced **negative simulated results after costs.** Observable latency ≠ exploitable latency |
| **Pure arbitrage as the strategy** | Cheng et al. 2026: 14.8-share depth, 3.6s windows, retail-scale ceiling |
| **Crypto cross-exchange / triangular arb** | Crépellière et al. 2023 (J. Financial Markets): "hardly possible to exploit" post-2018. Muck et al. 2024: 4,879 Binance triangular opportunities, **all eliminated by costs and depth**. Öz et al. 2025: 5 addresses do >half of cross-chain volume, one does 40% |
| **Market making on liquid venues** | Baron et al. 2018 (JFQA): relative latency rank drives performance. Gao et al. 2018: latency strictly degrades MM performance. We have no colocation |
| **Public factor zoos** (Vibe-Trading's 462 alphas) | Chen & Velikov 2020 (JFQA): net of spreads, post-publication decay, and modern trading era, the average anomaly nets **4 bps/month**; the best net **10 bps**; combinations ~**20 bps**. McLean & Pontiff 2016: −26% OOS, −58% post-publication |
| **Longshot contracts** | Whelan 2023 (Quant. Finance): prediction-market fees create a favorite-longshot bias — **post-fee loss rates rise as probability falls** |
| **"Free money" in near-certain contracts** | Gebele et al. 2026 (arXiv 2605.31431): collateral lock-up puts a maturity-dependent **settlement discount** in the price; adjusting for it removes **48–88%** of the apparent near-certainty gradient |
| **Selecting on backtest Sharpe** | Wiecki et al. 2016 (J. Investing), 888 live Quantopian algos: backtest Sharpe predicts OOS with **R² < 0.025**. Bailey & López de Prado: after **7** configurations you expect a 2-year backtest with SR > 1 when true SR = 0 |

---

## 3. The design

```
   market price q ──► ┌─────────────────────────────────────────┐
                      │ q*  BASELINE                            │  the price is not the probability
                      │  · un-discount settlement lock-up       │  Gebele 2026: explains 48-88%
                      │  · logistic recalibration by domain/TTE │  Le 2026: 353M trades
                      │  · fee-induced longshot bias absorbed   │  Whelan 2023
                      └────────────────┬────────────────────────┘
                                       │  q*  (everything downstream compares to THIS)
                       ┌───────────────▼─────────────────────────┐
                       │ ANCHOR      p₀ = q*  (market is prior)   │
                       └────────────────┬────────────────────────┘
                                        │
   LLM ensemble ───► independent, ─────►│ BLEND  p₁ = (1−w)·q + w·p_llm
   (no debate)       confidence-        │        w earned empirically, w=0 default
                     weighted           │
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │ RECALIBRATE  p₂ = isotonic(p₁)          │  fitted on resolved markets
                       └────────────────┬────────────────────────┘  never self-reported
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │ GATE  default = ABSTAIN                 │  every check must pass
                       │  · edge CI lower bound > total cost     │
                       │  · ensemble unanimous                   │
                       │  · depth ≥ intended size                │
                       │  · contract class not excluded          │
                       └────────────────┬────────────────────────┘
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │ SIZE  proper bet → shrunk frac. Kelly   │  THE PRINCIPAL CAUSE
                       │  · lower-confidence-bound edge          │
                       │  · fractional multiplier (default 0.25) │
                       │  · per-position + gross caps            │
                       │  · drawdown kill switch                 │
                       └────────────────┬────────────────────────┘
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │ SCORE  ΔS = S(p,y) − S(q*,y)            │  the go/no-go metric
                       │  ROI reported, never selected on        │
                       │  trials logged → deflated Sharpe        │
                       │  n counted as INDEPENDENT clusters      │
                       └────────────────┬────────────────────────┘
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │ ECONOMICS                               │  is the edge a business?
                       │  edge × capacity × frequency − costs    │
                       │  a 2% edge on $100k beats 15% on $20    │
                       └─────────────────────────────────────────┘
```

**No LLM is ever in the execution path.** It contributes one bounded number, `p_llm`, upstream of a
deterministic, tested, auditable pipeline.

---

## 4. The gate (pre-registered — changing it later is a new trial)

**Stage 0 — free, no capital, no venue account.** Run the pipeline against two public benchmarks:

1. **KellyBench** (openreward.ai) — must beat the documented frontier-model field: **> −8%** and **zero
   ruin across all seeds.**
2. **PredictionMarketBench** (arXiv 2602.00133) — deterministic Kalshi LOB replay with maker/taker and fee
   modelling.
3. **Hindcast** (Ye et al. 2026, arXiv 2607.14051) — replays resolved Polymarket markets against a frozen
   pre-`t₀` Reddit snapshot, closing both leakage channels (post-hoc retrieval and training-set overlap),
   and scores each forecast against the outcome **and the market's own price at `t₀`**.
   **Correction:** an earlier draft called this "the `q*` comparison as an evaluation protocol." It is
   not — Hindcast's baseline is the **raw** market price, not our learned adjustment. That is a feature:
   it gives an independent third-party benchmark against raw `q`, which is exactly what is needed to test
   whether our `q_ref` transformation adds anything at all. Run both comparisons; do **not** modify
   Hindcast to bake `q_ref` in.
4. **PolyBench** (arXiv 2604.14199) — 38,666 timestamp-locked markets with order-book execution
   simulation, and a published per-model leaderboard to beat.

**Pass condition (all five, or kill):**

1. **Information.** `skill_score(p, y; baseline=q*) > 0` on held-out resolved markets — the model beats
   the **friction-adjusted** market on a proper score, not on ROI. Beating raw `q` is not enough and can
   be actively misleading: in the shipped demo a forecaster scoring **+0.0000** against quoted `q` scores
   **−0.0430** against `q*`.
2. **Independent evidence.** `sufficient_evidence(clusters, required_effective_n=…)` passes. Contracts
   are clustered by underlying event; `ρ = 1.0` by default, so a cluster counts once.
3. **Selection.** Deflated Sharpe > 0 after counting **every** configuration tried, against the
   *effective* n, not the row count.
4. **Execution realism.** Results replicated under PredictionMarketBench's event-driven replay with
   maker/taker semantics, real depth and settlement — not the scalar cost model.
5. **Capacity.** `StrategyEconomics.worth_building(hurdle)` passes against an explicit hurdle equal to
   what the same effort earns elsewhere. Not zero. The published Polymarket NBA arbitrage grosses
   **$154/yr** at a 50% hit rate; that is a measurement, not a business.

**Stage 1 — paper, only if Stage 0 passes.** ≥ 60 sessions, live prices, zero capital.

**Stage 2 — capital, only if Stage 1 passes.** Smallest fundable size. Kill switch armed before first order.

At every stage the **null action is abstain** and the **null decision is kill**.

---

## 5. Non-negotiable constraints

1. **No secrets, positions, PnL, or account identifiers inside this repo.** Runtime state lives at
   `$ORDO_KAIROS_STATE`, which must resolve outside `C:/src`. Every repo under `C:/src` is
   publish-eligible (`C:/src/CLAUDE.md` rule 1).
2. **No LLM in the order path.** Ever.
3. **Every configuration tried is appended to the trial ledger** before its result is read. Untracked
   trials invalidate the deflated Sharpe and therefore the gate.
4. **Zero third-party dependencies in the decision core.** It is scalar math; it must port to Opifex Rust
   (`crates/opifex-core/src/portfolio.rs` already holds `RiskLimits` / `apply_limits` / `ClampEvent`) if
   and only if Stage 2 is reached.
5. **ROI is never a selection metric.** Wunderlich et al. 2020.
6. **We do not build an execution simulator.** `costs.py` is a deliberately conservative scalar screen for
   killing candidates cheaply — it is *not* adequate for validating one. Dubach 2026 (arXiv 2604.24366,
   30B order-book events) shows depth is not concentrated at top-of-book, effective spreads vary by
   category, and public-feed trade direction agrees with on-chain truth only **~59%** of the time. Real
   validation consumes PredictionMarketBench's replay and on-chain `OrderFilled` ground truth. Rebuilding
   an LOB simulator is exactly the premature infrastructure this project exists to avoid.
7. **Research is a cost centre, budgeted in `annual_fixed_cost`.** Prediction Arena found research volume
   uncorrelated with returns; Page & Siemroth 2017 found traders over-acquire information to the point of
   negative net profit. An LLM that can generate hypotheses for pennies makes this worse, not better.

---

## 6. Open forks (operator decision, not blocking the core)

- **Venue.** Kalshi (CFTC-regulated, PredictionMarketBench replay available, but Prediction Arena models
  did *worse* there) vs Polymarket (better model returns, deeper free data — Qin et al. 2026 released
  **1.20B trades / 1.30M markets with 100% ground-truth aggressor direction**, arXiv 2606.04217 — but
  UMA resolution risk: **$972M** of disputed volume, Wen et al. 2026). Verify current US regulatory
  status before binding.
- **Capital.** Sizing is fraction-of-bankroll; the absolute number only matters at Stage 2.
