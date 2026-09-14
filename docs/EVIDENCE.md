# Ordo Kairos — Evidence Ledger

Every empirical claim this project relies on, what it licenses, and — critically — **what it does
not license**. Cited by DOI, which is durable; tracking URLs are not.

Strength grades:

| Grade | Meaning |
|---|---|
| **S** | Large sample, peer-reviewed or heavily replicated, direction and magnitude both usable |
| **A** | Solid single study or well-cited preprint; direction usable, magnitude indicative |
| **B** | Recent preprint, low/zero citations, narrow deployment. **Hypothesis source only** (A3) |
| **R** | Refuted, corrected, or downgraded. Recorded so it is not re-asserted |
| **U** | **Unverified public claim** — social media, promotional writeup, press coverage. Weaker than B: no method, no data, usually a commercial interest. **Hypothesis source only (A3), and never a planning input.** Recorded here *with its test* so the same claim cannot return as folklore |

Last revised 2026-09-08.

---

## 1. Direct LLM trading

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| All frontier models lose money over a season; best −8%; several ruined; Claude Opus 4.6 strategy rubric 26.5% | KellyBench, Grady et al. 2026, `10.48550/arxiv.2604.27865` | A | Refusing LLM-as-trader | Any claim about LLM *forecasting* |
| Six frontier models, real capital, 57 days: Kalshi −16.0% to −30.8%; **research volume uncorrelated with outcomes** | Prediction Arena, Zhang et al. 2026, `10.48550/arxiv.2604.07355` | A | B3 (research is a cost); D5 | Generalising to all venues — Polymarket averaged −1.1% |
| **Two of seven models profitable** on 38,666 timestamp-locked markets (MiMo-V2-Flash 17.6% CWR, Gemini-3-Flash 6.2%); five lost "despite uniformly high stated confidence" | PolyBench, Cheng et al. 2026, `10.48550/arxiv.2604.14199` | A | Treating per-model forecasting competence as an empirical hypothesis | The blanket claim "LLMs cannot forecast" — **this refuted our earlier overreach** |
| LLMs as direct traders show extreme run-to-run variance and irrational action flipping *under deterministic decoding*; cure is LLM-as-researcher emitting an executable strategy | AlphaForgeBench, Zhang et al. 2026, `10.48550/arxiv.2602.18481` | A | D5, and the whole architecture | — |
| LLM relative performance changes over a market lifecycle: more competitive **early and in uncertain markets**, substantially less near resolution | TimeSeek, Mostafa et al. 2026, `10.48550/arxiv.2604.04220` | B | Conditioning any ensemble weight on **market state**, not model identity | Fixed per-model weights |
| Of 77 coded studies, 19 with closed-loop evaluation: **1/19 reports an explicit transaction-cost model**, 1/19 documents survivorship, **none reach R3 reproducibility** | Agentic Trading survey, Xia et al. 2026, `10.48550/arxiv.2605.19337` | A | Default scepticism toward any uncosted LLM alpha claim | — |

## 2. Ensembles are not independent

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| Pairwise forecast-error correlation ≈ **0.70** for aligned agents; **ten agents ≈ 1.4 effective independent forecasters**; cross-model diversity helps but does not eliminate it | Begin et al. 2026, `10.48550/arxiv.2606.26583` | A | **C8.** Measuring ρ before claiming diversity | Assuming vendor diversity = information diversity |
| Combination helps, but dependence and weighting structure materially determine how much | Wang & Hyndman 2022, `10.1016/j.ijforecast.2022.11.005` | S | Starting with simple pools | Sophisticated weighting before simple pools are beaten |
| Deliberative multi-agent consensus **degrades** accuracy to ~76%, below every single-model baseline ("confidently wrong models flip correct ones"); unanimous high-confidence subset reaches 97.87% on 47% of items | Kota 2026, `10.48550/arxiv.2605.30802` | A | No debate; abstention on disagreement | Calling independent aggregation "independent" (see above) |

## 3. The market benchmark

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| Equilibrium prediction-market prices converge to **different weighted means of participants' beliefs** depending on utility functions and trading order | Yu et al. 2022, `10.1145/3490486.3538347` | A | **A2.** Naming the benchmark an estimator | Any claim to have recovered "the market's belief" |
| Calibration varies with domain, time-to-resolution and trade size; political markets compress toward 50%; **~half of raw slope variation may be estimation noise** | Le 2026, `10.48550/arxiv.2602.19520` | A | Conditional logistic recalibration, cross-fitted | Hard-coding a correction; treating fitted slopes as stable |
| Logistic and beta recalibration on **logit-transformed** estimates consistently best; must be validated externally | Ojeda et al. 2023, `10.1002/sim.9921` | S | Logit-space recalibration as the default family; external validation | Isotonic as an unexamined default on sparse data |
| Settlement discount is maturity-dependent, **time-varying**, and altered by market architecture (NegRisk conversion, yield-bearing collateral); adjusting for it explains 48–88% of the near-certainty gradient | Gebele & Matthes 2026, `10.48550/arxiv.2605.31431` | A | An *estimated* settlement adjustment that must earn its place OOS | **"Undiscounting is arithmetic, not estimation" — refuted, see §7** |
| Commercial prediction-market fee structures mechanically produce favourite-longshot effects in prices and returns | Whelan 2023, `10.1080/14697688.2023.2257756` | A | Longshot exclusion; fee-aware edge tests | — |

## 3b. Where the market's error lives — the case for stratifying

Every gate so far tested **one average over the whole sample**. This row set is why that is a design
choice rather than a neutral default, and it is what `PRICE_STRATA` and Gate 0b were built from.
None of it licenses a stratified result; it licenses *testing* the stratified hypothesis under A7.

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| Calibration is **not a static property**: on 23M Kalshi trades, parameters sit at perfect-calibration values mid-life and depart sharply near expiry, becoming step-like in the final ten minutes. "Practical use of prediction-market prices as probabilities requires conditioning on time to expiry and product type, not on price alone" | Moshrefi 2026, `10.48550/arxiv.2607.14430` | B | Treating time-to-expiry as a **designed variable**, not a constant. Directly motivates Correction 8.3 | Any claim about *which* horizon is exploitable on Polymarket; this is Kalshi sports |
| Time to expiration negatively affects price accuracy; markets are reasonably calibrated when expiry is near and significantly biased for events further out — exploitable only by a trader with a low discount rate | Page & Clemen 2013, `10.1111/j.1468-0297.2012.02561.x` | S | Horizon as an axis; the cost model's settlement wedge | Assuming the bias is large enough to clear costs at any particular horizon |
| Models "failed to beat the market in the headline contract but some did so convincingly in contracts referencing **less visible** races" | Sethi & Kline 2025, `10.1145/3715928.3737483` | A | Attention/visibility as a market-selection axis worth registering | Selecting the visibility cut after seeing which side wins |
| Model and market make **different kinds of errors in different states**; a simple average beat both overall, though no average can beat both components on any single state-date pair | Sethi & Kline 2021, `10.2139/ssrn.3767544` | A | Keeping the market-anchored pool on the Gate 2 ladder | Building weighting machinery before a simple pool is beaten (C9) |
| Machine-weighted hybrid beat the market **particularly where the two disagreed by ≥5%**, replicated out of sample | Gruen et al. 2023, `10.1016/j.ebiom.2023.104783` | A | Disagreement magnitude as a pre-registered stratum candidate | Conditioning on disagreement *after* seeing the marginal test fail |
| Relative advantage of prediction markets over polls/models is "surprisingly small", with **steep diminishing returns to information — nearly all predictive power in two or three parameters** | Goel et al. 2010, `10.1145/1807342.1807400` | S | **Stopping the ladder.** Four price-path forecasters already exhaust the plausible parameter budget; adding models is refuted a priori | Concluding no edge exists — this is about *model complexity*, not market efficiency |
| Overpricing in on-chain prediction markets is self-fulfilling and **survives only for longshots**; capital-weighted clearing underprices favourites | Gill 2026, `10.2139/ssrn.6886600` | B | The direction of the longshot/favourite split in `PRICE_STRATA` | A trading rule. Hypothesis source only (A3) |
| Mispricing is positively associated with trading volume and **negatively with institutional presence**; information enters faster in the market receiving more attention | Abínzano et al. 2019, `10.1177/1527002517731875` | A | Attention as a mechanism behind the visibility finding above | Depth/volume as an admission filter without measuring it first (D1) |

## 3c. What happens when models actually trade these venues

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| Six frontier models trading **real capital** for 57 days returned **−16.0% to −30.8% on Kalshi** and averaged **−1.1% on Polymarket**; research volume showed **no correlation** with outcomes; platform design dominated which models succeeded | Zhang et al. 2026, `10.48550/arxiv.2604.07355` | B | **A large downgrade of Gate 2b's expected value.** This is leakage-free by construction — live, forward, real money — and it is the closest existing evidence to the question Gate 2b would answer, at a fraction of the cost | Concluding an LLM cannot forecast; the study measures *trading agents*, including sizing and execution, not forecast skill in isolation (B1) |
| Profitability-optimised model selection beats accuracy-optimised out of sample by implicitly detecting and countering market bias | Wunderlich & Memmert 2026, `10.1016/j.ijforecast.2025.11.006` | A | Keeping economic value as a **Level-2** question, after informational superiority | Selecting on ROI (C2) |

## 4. Validation and overfitting

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| Adaptive reuse of a holdout destroys its validity; the reusable-holdout construction is needed to restore it | Dwork et al. 2015, `10.1126/science.aaa9375` | S | **C5, C6.** Sealed single-query final holdout | Believing a trial ledger solves adaptivity |
| Whole financial-ML workflows must be run against **martingale/null environments and microstructure placebos**; workflows that still "discover" predictability are rejected | Nikolopoulos 2026, `10.48550/arxiv.2604.15531` | B | **A7.** The null-world meta-gate as a *first* step | — |
| After ~7 configurations you expect a 2-year backtest with Sharpe > 1 when true Sharpe = 0 | Bailey et al. 2016, `10.2139/ssrn.2326253` | S | Trial counting; minimum backtest length | Treating DSR as the primary inference for clustered binary events |
| Deflated Sharpe corrects selection bias and non-normality | Bailey 2014, `10.3905/jpm.2014.40.5.094` | S | DSR as a **secondary** diagnostic | DSR as an independent universal pass condition (§7) |
| Backtest Sharpe predicts out-of-sample performance with **R² < 0.025** across 888 live algorithms | Wiecki et al. 2016, `10.3905/joi.2016.25.3.069` | S | Never selecting on backtest Sharpe | — |
| Clustered-data inference requires attention to correlation structure, unequal cluster size and small-cluster corrections; cluster wild bootstrap for few clusters | Joshi, Pustejovsky & Beretvas 2021, `10.1002/jrsm.1554` | S | **C4.** Block/cluster bootstrap for the primary test | A scalar `n_eff` fed to a Sharpe formula |
| Forecast superiority testing must handle serially dependent errors (HAC / bootstrap) | Corradi, Jin & Swanson 2023, `10.2139/ssrn.3538905` | S | Paired score-difference test as the primary inference | — |
| At power < 30%, statistically significant estimates carry relative bias > 1.78 and "almost no estimates are roughly accurate"; low-power significant results may consist **entirely** of magnitude, sign and Type-I errors | Jaksic et al. 2026, `10.1016/j.gloepi.2026.100250` | A | Treating the selected-best-of-K effect as an **upper** bound when planning sample size, never as the effect | Reporting a power calculation that assumes the observed effect is the true one |
| Design analysis: report the exaggeration ratio (Type M) and sign error rather than power alone; the hard part is a defensible plausible effect size | Gelman & Carlin 2014, `10.1177/1745691614551642` | S | Naming the selection filter explicitly wherever a best-of-K is reported | — |
| Type S/M statistics do **not** support good design or interpretation; **testing against a minimum effect while controlling Type I error is the coherent alternative** | Lakens et al. 2026, `10.1177/25152459261432530` | A | **Post-hoc endorsement of `MIN_RELATIVE_GAIN`** — the materiality floor added after Gate 1's p=0.0005 win worth 0.02% of the benchmark is exactly minimum-effect testing | Dropping the materiality floor in favour of an exaggeration-ratio adjustment |
| Repeatedly testing accumulating data inflates Type I error; alpha-spending controls it **even when the number and timing of looks is not fixed in advance** | DeMets & Lan 1994, `10.1002/sim.4780131308`; Lakens et al. 2021, `10.31234/osf.io/x4azm` | S | **A hard precondition on re-testing.** Gates 1 and 2a are look #1 on this hypothesis; any re-test on a superset of the same markets is look #2 and needs its spending schedule registered *before* the run | Re-running the same test at nominal `alpha` on more data and reporting the result as if it were a first look |
| Positive betting returns arise systematically **or randomly** without superior accuracy | Wunderlich et al. 2020, `10.1016/j.ijforecast.2019.08.009` | S | **C2** | — |

## 5. Scoring rules

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| Different strictly proper rules can rank two imperfect forecasters differently; locality matters | Du 2020, `10.1175/waf-d-19-0205.1` | A | **C1.** Pre-registering log score as primary | Post-hoc score selection |
| Calibration for an unknown downstream agent is a distinct objective from any single proper score | Kleinberg et al. 2023, `10.48550/arxiv.2307.00168` | A | Reporting calibration diagnostics separately | Assuming score optimality ⇒ decision optimality |
| Better statistical forecast scores do not automatically yield better downstream decisions | Stratigakos et al. 2024, `10.1016/j.ijforecast.2024.11.006` | A | Keeping forecast skill and economic value as **separate** gates | Collapsing them into one metric |
| Selecting on calibration rather than accuracy raises betting ROI | Walsh & Joshi 2023, `10.1016/j.mlwa.2024.100539` | **R → direction only** | The *direction* | **The magnitude — see §7** |
| Models optimised against market prices beat accuracy-optimised ones out of sample | Hubáček et al. 2019, `10.1016/j.ijforecast.2019.01.001`; Wunderlich et al. 2026, `10.1016/j.ijforecast.2025.11.006` | S | The direction above, independently | — |

## 6. Market structure, capacity, and strategy classes

| Finding | Source | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| 173 NBA games: 7 executable single-market episodes (median 3.6 s); 290 combinatorial episodes at 101 bps median; **76.9% capped near 14.8 shares** | Cheng et al. 2026, `10.48550/arxiv.2605.00864` | A | Rejecting *ultra-low-latency, single-market, retail-scale* arbitrage | **Rejecting arbitrage as a class — that generalisation was invalid (§7)** |
| Rebalancing and combinatorial arbitrage on Polymarket, ≈ **$40M realized extraction** historically | Saguillo et al. 2025, `10.48550/arxiv.2508.03474` | A | Investigating combinatorial payoff arbitrage | Assuming that pool is accessible at our scale |
| Distinguishes theoretical payoff arbitrage from **protocol-executable** arbitrage; reconstructs ≈ **$1.12M** realized profit through distinct mechanisms | Gebele, Mutzel & Matthes 2026, `10.48550/arxiv.2608.00666` | B | Protocol/NegRisk arbitrage as a Stage-0 hypothesis class | Assuming it survives our costs |
| Cross-platform semantic matching over >100,000 events finds persistent **2–4% execution-aware price deviations** between semantically equivalent contracts | Gebele & Matthes 2026, `10.48550/arxiv.2601.01706` | A | **Cross-venue semantic arbitrage as hypothesis class B** — the best fit for LLM comparative advantage | An LLM declaring any pair equivalent without deterministic payoff verification |
| Polymarket responds to large Binance moves at ~**347 ms median**, yet a 43-feature walk-forward model is **negative after costs** | OpenMarket, Young 2026, `10.48550/arxiv.2607.26245` | B | **D2** | — |
| Five-minute BTC contracts: settlement-time spot flow spikes and reverses; manipulators capture profit "mostly from retail"; **absent at 15 minutes** | Dai et al. 2026, `10.48550/arxiv.2606.31675` | A | **D4** | A 15-minute horizon being *safe* — the mechanism, not the clock, decides |
| Depth is not concentrated at top-of-book; effective spreads vary by category; public-feed trade direction matches on-chain truth only ~**59%** of the time | Dubach 2026, `10.48550/arxiv.2604.24366` | A | **D6.** On-chain `OrderFilled` ground truth for microstructure work | Trusting a scalar half-spread as a validator |
| Strategy performance declines with scale; impact is nonlinear; slow impact decay reduces apparent capacity; misspecified impact can turn expected profit into loss | Landier et al. 2015; Chan 2022 `10.2139/ssrn.3911635`; Hey et al. 2023 `10.2139/ssrn.4465282` | S | **D3.** Profit-versus-size curves when a candidate survives | Building that machinery before a candidate requires it (E1) |
| Net of spreads, post-publication decay and modern trading, the average anomaly nets **4 bps/month**; best 10; combinations ~20 | Chen & Velikov 2020, `10.1017/s0022109022000874` | S | Excluding public factor zoos | — |

## 7. Benchmarks and harnesses

| Resource | Source | What it is | What it is **not** |
|---|---|---|---|
| **Hindcast** | Ye et al. 2026, `10.48550/arxiv.2607.14051` | Replays resolved Polymarket markets against a frozen pre-`t₀` Reddit snapshot, closing retrieval and training-overlap leakage. Scores against the outcome **and the market price at `t₀`** | **Not** an implementation of our `q_ref`. Its baseline is **raw** market price. That is a feature: it is an independent third-party check on raw `q`, and must not be contaminated with our transformation |
| **PredictionMarketBench** | Arora & Malpani 2026, `10.48550/arxiv.2602.00133` | Event-driven Kalshi replay with maker/taker, fee and settlement semantics. The reference implementation for fill semantics | **Only four Kalshi episodes.** An integration and smoke test, **not** a universal certifier of execution realism across venues or categories |
| **PolyBench** | Cheng et al. 2026, `10.48550/arxiv.2604.14199` | 38,666 timestamp-locked markets, order-book execution simulation, per-model leaderboard | — |
| **KellyBench** | Grady et al. 2026, `10.48550/arxiv.2604.27865` | Season-long sequential betting; published frontier-model field to beat | — |
| **Polymarket-v1 DB** | Qin et al. 2026, `10.48550/arxiv.2606.04217` | 1.20B trades, 1.30M markets, **100% ground-truth aggressor direction** | — |

## 7b. Measured in this repository (Gate 0)

Findings produced by our own harness rather than read from a paper. Reproduce with
`python gate0.py`. Full narrative in [`CORRECTIONS.md`](CORRECTIONS.md) Pass 4.

| Finding | Measurement | Grade | Licenses | Does **not** license |
|---|---|---|---|---|
| **Detecting a market-relative edge needs hundreds of independent events.** Oracle power vs test-set size: 0.183 @ 20, 0.333 @ 40, 0.500 @ 80, 0.667 @ 160, **0.933 @ 320**, 1.000 @ 640 | Unbeatable oracle forecaster against a heavily compressed market, one-sided α=0.05, 60 replications | A | Sizing Gate 2's evaluation set at **≥300 independent events**; rejecting any fund/kill claim built on fewer | Reading these as *sufficient*. The control's edge is far larger than realistic and the oracle is unbeatable, so a real forecaster needs **more** |
| Fit-and-select-and-test on the same data, with IID inference, produces near-total false positives on provably null worlds | `naive` protocol, 26/30 on `fair_market+noise` | A | AXIOMS C3/C5/C6, measured on our own code | — |
| Cluster-robust inference alone does **not** fix selection bias | `cluster` protocol sits above nominal α on null worlds | A | Requiring the sealed holdout in addition to correct inference | — |
| Selecting a candidate by its *fit-set* score reliably picks the worst generaliser | Zero power until a three-way fit/select/holdout split was introduced | A | The three-way split as mandatory | — |
| A zero power reading is uninterpretable without an oracle ceiling | Oracle undetectable at the original sample size, so the pipeline's zero carried no information | A | Reporting the ceiling on every positive control | Concluding "inert pipeline" whenever power is low |

## 8. Corrected and downgraded claims

Recorded so they are not silently re-asserted. Full history in [`CORRECTIONS.md`](CORRECTIONS.md).

| Claim | Status | Why |
|---|---|---|
| Walsh & Joshi's "+34.69% vs −35.17%" | **Magnitude retracted** | Three published versions give three magnitudes (arXiv `10.48550/arxiv.2303.06021`: +110.42% vs +2.98%; journal: +34.69% vs −35.17%), then a **2025 corrigendum** `10.1016/j.mlwa.2025.100627` records errors "discovered in the original implementation" during modularisation and unit testing. Direction survives on independent sources |
| "Sizing is the principal cause of PnL" | **Retracted** | Inverts B1/B2. Sizing governs the wealth path given an edge |
| "`q*` is the market's actual belief / fair probability" | **Retracted** | Violates A2 (Yu et al. 2022) |
| "Settlement undiscounting is arithmetic, not estimation" | **Retracted** | Applying a known wedge is arithmetic; *obtaining* it is estimation, and it is time-varying and architecture-dependent |
| "Applying settlement before recalibration prevents double-counting" | **Retracted** | Violates C7 — code order is not statistical orthogonality |
| "Hindcast is the `q*` comparison as an evaluation protocol" | **Retracted** | Hindcast compares against **raw** `q` at `t₀` |
| "Pure arbitrage" excluded as a class | **Retracted** | Invalid generalisation from one retail-scale NBA study. Structural/protocol/semantic arbitrage is a separate class with independent evidence |
| The `q*` demo number (+0.0000 vs −0.0430) as "the number that justifies the repo" | **Retracted as evidence** | Fitted and scored on the same synthetic observations. Violates A5. Retained only as a unit demonstration that the transformation runs |
| DSR > 0 as an independent universal pass condition | **Downgraded to secondary** | Assumptions are not justified for sparse, clustered binary-contract experiments |
| `n_eff` (ρ=1) as an inference input | **Downgraded to planning heuristic** | C4 |
| 100× manipulation-cost multiple | **Rejected as a production rule** | An arbitrary safety factor standing in for an unmeasured quantity (A6). A manipulator's incentive is not bounded by our position size |
| "Independent LLM ensemble" | **Retracted** | C8; ρ ≈ 0.70, ten agents ≈ 1.4 effective |

## 9. Unverified public claims, and what testing them cost

Grade **U**. Social-media and press claims about AI agents making money, tested 2026-09-14 with
machinery already in this repository. They are recorded **with their tests** because an untested
claim returns as folklore, and because the cost of testing one turned out to be minutes.

The pattern across all three: **each claim carries the number that refutes it.** None needed new
data.

| Claim | Source | Test | Result |
|---|---|---|---|
| AI agent finds linked prediction markets; **~20% average return** on week-long trades; **60–70% of high-confidence links resolve correctly** | IBM + Columbia, circulated on X | `legset.break_even_failure_rate(0.20, 1.0)` | **Internally inconsistent.** A 20% edge on a $1 stake tolerates a **16.7%** link-failure rate. The claim's own reported accuracy is a **30–40%** failure rate — two to two-and-a-half times break-even. At 10% edge the tolerance falls to 9.1% |
| ETH SMA-crossover agent, backtest **289.71% → 419.29% after refinement**, refinement being "Monte Carlo over hundreds of strategy variations" | X, "no code written" writeup | `score.expected_max_sharpe(n)` | **The refinement is the defect.** 300 trials of **pure noise** yield an expected max Sharpe of **2.90**; 1,000 yield 3.26. Justifying a *true* Sharpe of 1 after 300 trials needs **11.4 years** of honest backtest. Selecting the best of hundreds is not refinement, it is manufacture |
| Wallet "0x8dxd": **$313 → ~$437,600 in a month, 98% win rate**, latency arbitrage on 15-minute BTC/ETH/SOL contracts against Binance/Coinbase spot | Press coverage | endpoint probe + our own §6 | **Verifiable in principle, unverifiable as published.** `data-api.polymarket.com/value?user=<address>` resolves and returns portfolio value, so on-chain PnL *is* checkable — but the published identifier is **truncated**, and the leaderboard endpoints 404/400. A truncated handle is what makes a concrete-looking claim unfalsifiable |

### What the third claim runs into, from evidence already in this ledger

- **The mechanism was measured and is negative.** OpenMarket (Young 2026, §6) found Polymarket
  responds to large Binance moves at ~347 ms median and that a 43-feature walk-forward model is
  **negative after costs** — the same lag, the same venue, done properly.
- **The horizon choice is not innocent.** Dai et al. 2026 (§6) measured settlement-time manipulation
  on 5-minute BTC contracts capturing profit "mostly from retail", and **absent at 15 minutes**. The
  claim names 15-minute contracts, which is the horizon where that particular predation is not.
- **PROTOCOL excludes the class anyway** (D4): the manipulability of the settlement reference is the
  disease and the horizon is a symptom, so these markets fail closed here regardless of the claim.

### Apparatus note

Swept 1,600 open markets across both volume orderings: **82** short-horizon "Up or Down" crypto
markets exist as listings, every one reachable quoting **spread 1.0, last 0, volume 0** — dead
shells, dated months out. The live five-minute windows are not reachable through offset pagination,
so **this repository cannot presently observe the market class the claim is about.** That is a
statement about our apparatus, not about the claim (G12).

### What this licenses

**Nothing about strategy.** It licenses one operating rule: a public claim whose identifier is
truncated, whose selection procedure is "best of many", or whose own reported accuracy sits below
its own break-even, is refutable **in minutes** with instruments already built — so it should be,
before it is allowed to reorder a roadmap.
