# Gate B — Results

**Verdict: PASS.** Run 2026-09-08. Reproduce with `python gateb.py --groups 200`.

1,000 groups per world (200 × 5 horizons from 7 days to 2 years), 3–8 legs. The Class B pipeline
finds nothing in six arbitrage-free worlds and detects an unambiguous edge every time.
`docs/CENSUS-RESULTS.md` **Decision 001** is now satisfied: a scanner against real negRisk groups is
licensed, as a **candidate generator only** (A5, D1).

---

## Result

| world | signal | 7d | 30d | 90d | 365d | 730d |
|---|---|---|---|---|---|---|
| fair | — | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / **1.000** | 0.000 / **1.000** |
| fair+noise | — | 0.000 / 0.030 | 0.000 / 0.045 | 0.000 / 0.250 | 0.000 / **1.000** | 0.000 / **1.000** |
| truncated | — | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** |
| non_exhaustive | — | 0.000 / 0.995 | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** |
| thin_book | — | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** | 0.000 / **1.000** |
| **marginal** | — | **0.000** | **0.000** | **0.000** | **0.000** | **0.000** |
| *truncated_believed* | *exhibit* | *1.000* | *1.000* | *1.000* | *1.000* | *1.000* |
| **ARB independent** | ✔ | **1.000** | **1.000** | **1.000** | **1.000** | **1.000** |

*(disciplined scanner / naive exhibit)*

**The naive scanner fires at up to 1.000 in worlds containing no arbitrage at all.** Every refusal
in `scan` is paid for by that number — it is the empirical case for the discipline, measured against
our own code rather than asserted from the census anecdote.

## The two results that carry the gate

**`marginal` — the only null that tests arithmetic.** Every other arbitrage-free world is rejected
by a *structural refusal*: a boolean the world hands the scanner saying the leg set is incomplete or
exhaustiveness is unverified. Those test flag-honouring, not detection. `marginal` has impeccable
structure and is unprofitable by exactly 0.005 after costs, so **only the fee, spread and carry
arithmetic stands between the scanner and a false fire.** It holds at every horizon.

**`ARB independent` — a control that is not circular.** The first version of this gate used
`inject_arbitrage`, which bisects on `effective_yes_cost` to hit a target post-cost edge — i.e. it
is defined by the very formula `scan` applies, so detecting it was guaranteed by construction rather
than measured. That is the same defect as the retracted Gate-2a demo. `obvious_arbitrage` scales
quotes to a fixed **nominal** sum of 0.70, which is riskless profit under any cost model anyone
would defend. The circular control is retained as a labelled exhibit.

---

## The gate's most valuable output is a number it does not gate on

`truncated_believed` fires **1.000 at every horizon**. It models a group that really is truncated
while the leg set is asserted complete — which is what happens when upstream pagination silently
drops a leg, because real pagination does not announce itself.

**The scanner cannot defend against this and no arithmetic inside it ever will.** A leg never seen
cannot be reasoned about. So the entire Class B false-positive defence rests on **leg-set
verification upstream**, and this number says how much that verification is carrying: all of it.

Carried as an exhibit rather than a gate condition, because failing it is information about where
the risk lives rather than a defect in the thing being gated. Any real scanner must treat
completeness as a *measured property with its own verification*, never as a field read off a
response.

## A latent inconsistency, found before the scanner existed

The repo holds **two carry models**, and they disagree:

| horizon | `SettlementTerms` implied cost | `CostModel.carry` | gap |
|---|---|---|---|
| 7 d | 0.00115 | 0.00115 | 0.00000 |
| 90 d | 0.01458 | 0.01479 | 0.00022 |
| 365 d | 0.05660 | 0.06000 | 0.00340 |
| **730 d** | **0.10714** | **0.12000** | **0.01286** |

`SettlementTerms` discounts (`1/(1+wt)`); `CostModel.carry` is linear (`base·wt`). They agree to
first order and diverge with horizon. **1.29 points at two years is larger than a plausible
arbitrage**, and negRisk groups are most numerous at exactly those horizons — the census's own
worked example was a *JD Vance 2028* group.

It does **not** currently produce false positives, and the gate says why: at five legs, `N ×
half_spread` alone is 0.025, which swamps the 0.0129 disagreement. **The inconsistency is latent,
not active** — it is masked by costs rather than absent, and a lower-spread venue or a
maker-execution assumption would unmask it.

Deliberately **not** unified now (E3): the two models are consumed by different recorded results,
and changing `SettlementTerms` would move Gate 1's settlement numbers. Instead the gap is pinned by
a regression test so it cannot silently widen, and the scanner is built to charge carry **once**,
through `effective_yes_cost`, against a nominal $1 payoff (C7).

---

## Limitations

- **Synthetic worlds only.** These groups are constructed, not observed. The gate falsifies the
  *scanner logic*; it says nothing about whether real negRisk groups behave like this.
- **Depth is modelled, not measured.** `MIN_FILL = 25` contracts is enforced against a synthetic
  depth field. Real book depth is a Gate 3 question and no order-book data has been touched.
- **Completeness is handed to the scanner as a boolean.** See above — this is the residual risk, and
  it is the single thing most likely to make a real scanner wrong.
- **One venue's fee structure.** `CONSERVATIVE` is a Polymarket-shaped cost model.
- **No adversary.** Nothing here models a counterparty who withdraws quotes when hit, which is the
  usual reason a screen-visible arbitrage is not executable.
