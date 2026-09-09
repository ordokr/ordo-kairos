# Ordo Kairos

A decision core for event-contract markets. **Not a trading bot.** A pre-registered instrument for
deciding, on measured evidence and without risking capital, whether a trading bot is worth building.

Read [`SPEC.md`](SPEC.md) first — it carries the evidence and the kill rule.

## The one-paragraph version

Frontier LLM agents told to trade lose money: **all of them** on KellyBench (best −8%, several ruined),
**−16% to −31%** on live Kalshi capital in Prediction Arena. But two of seven models *were* profitable on
PolyBench, so forecasting competence is an empirical hypothesis to be tested per model — while execution
discretion is simply removed. The scarce unknown is not how to size a bet; fractional Kelly is well
understood. It is **whether there is a repeatable edge worth sizing at all**. So this repo builds, in
causal order: a friction-adjusted market baseline `q*` that the forecaster must actually beat, a proper
score differential against it, a capacity model that asks whether the edge is a business, and only then
sizing — which governs the wealth path but **cannot create edge**. It abstains by default and its null
decision is *kill*.

## Status

`v0.2` — decision core only. No venue binding, no network, no capital, no LLM wired in.
101 tests, zero third-party dependencies.

## Layout — in causal order, information first

| Module | Role |
|---|---|
| `kairos/baseline.py` | **`q_raw → q*`.** Settlement un-discounting + logistic recalibration. The price is not the probability |
| `kairos/score.py` | **`ΔS = S(p,y) − S(q*,y)`** — the go/no-go metric. Trial ledger, deflated Sharpe |
| `kairos/economics.py` | edge × capacity × frequency − costs. Effective sample size (clusters, not rows) |
| `kairos/costs.py` | Fees, half-spread, settlement wedge — a conservative *screen*, not a validator |
| `kairos/calibration.py` | Isotonic (PAVA) recalibration, market-anchored blending, reliability stats |
| `kairos/gate.py` | Abstention gate. Default `ABSTAIN`; fails closed on unmeasured manipulability |
| `kairos/sizing.py` | `(p, q*) → stake`. Proper betting → shrunk fractional Kelly → caps |

Sizing is last on purpose. Pure stdlib, so it ports to Opifex Rust unchanged in structure.

## Governing documents

| Doc | Role |
|---|---|
| [`docs/AXIOMS.md`](docs/AXIOMS.md) | Standing rules that outrank convenience. Cite by number |
| [`docs/EVIDENCE.md`](docs/EVIDENCE.md) | Every empirical claim, graded, with what it does **not** license |
| [`docs/PROTOCOL.md`](docs/PROTOCOL.md) | Pre-registered Stage 0. Gate 0 is null-world falsification of Kairos itself |
| [`docs/CORRECTIONS.md`](docs/CORRECTIONS.md) | Claims withdrawn, and why. Anti-drift record |
| [`SPEC.md`](SPEC.md) | Design and market-selection rationale |

## Status: nothing is validated yet

This repo has **not demonstrated a single out-of-sample edge.** `demo.py` shows the machinery runs;
its numbers are fitted and scored on the same synthetic data and are **not evidence** of anything
(AXIOMS A5).

## Gate 0 — null-world falsification

```bash
python gate0.py            # full run (~30 min)
python gate0.py --quick    # indicative only, not a gate result
```

Before asking whether this pipeline can find an edge, it asks whether it reliably **fails** to find
one that does not exist — and whether it can still see one that does. Three protocols are compared
on the same synthetic worlds so the harness shows which discipline buys what:

| Protocol | Selection | Inference | Role |
|---|---|---|---|
| `naive` | fit + select on all data | IID, clustering ignored | exhibit — expected to fail |
| `cluster` | fit + select on all data | cluster-robust | isolates selection bias |
| `kairos` | fit / select / **sealed holdout** | cluster-robust | the gate condition |

Every positive control is also run through an **oracle** built from the world's own generating
parameters. Nothing can beat it, so its detection rate is the power ceiling — which is what
separates *"the pipeline is inert"* from *"the sample is too small."*

### The finding that constrains the whole programme

Oracle power against a heavily compressed market, one-sided α = 0.05:

| independent events | 20 | 40 | 80 | 160 | 320 | 640 |
|---|---|---|---|---|---|---|
| oracle power | 0.183 | 0.333 | 0.500 | 0.667 | **0.933** | 1.000 |

**A market-relative forecasting edge needs hundreds of independent events to detect — not dozens**,
and this is an *upper* bound, since the oracle is unbeatable and the control's edge is larger than
anything realistic. Any evaluation set below ~300 independent events cannot support a fund/kill
decision, however many contract rows it holds.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

## Rules that outrank convenience

1. No secrets, positions, PnL, or account IDs in this repo. Runtime state goes to `$ORDO_KAIROS_STATE`,
   which must resolve outside `C:/src`.
2. No LLM in the order path.
3. Log every configuration to the trial ledger *before* reading its result.
4. ROI is reported, never selected on.
