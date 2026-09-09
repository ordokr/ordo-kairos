# Gate 2a — Results

**Verdict: ladder stopped at rung 2. No leakage-free forecaster adds information beyond the market
price.** Run 2026-09-08. Reproduce with `python gate2.py --pages 20 --limit 900`.

Gate 2 splits in two. **2a** (this) runs contamination-proof deterministic forecasters over the
price path. **2b** is the LLM step and is blocked on leakage — see the end.

---

## Dataset

Same as Gate 1: 900 observations, **731 independent events**, 548 development / 183 sealed.
Out-of-sample: 422 rows across 366 events. Benchmark is raw market price (Gate 1 rejected `q_ref`).

## The ladder

| rung | model | log score | vs market | p | verdict |
|---|---|---|---|---|---|
| 1 | **market alone** | 0.33607 | — | — | benchmark |
| 2 | `drift` | 0.32414 | **+0.01193** | 0.1174 | no reproducible gain |
| 2 | `volatility` | 0.34057 | −0.00450 | 0.7056 | no reproducible gain |
| 2 | `maturity` | 0.34299 | −0.00692 | 0.7421 | no reproducible gain |
| 2 | `momentum` | 0.34616 | −0.01009 | 0.7596 | no reproducible gain |
| 3–4 | *not reached* | | | | ladder stopped |

Rungs 3 and 4 were never run, by design: PROTOCOL says stop at the first rung not beaten.
**Sophisticated weighting was not built** (AXIOMS C9, E1).

---

## Finding 1 — error correlation is confounded by anchoring; tilt correlation is not

Correlation was measured **before** any pooling machinery existed (AXIOMS C8). It produced two very
different answers:

| pair | ρ(error) | ρ(tilt) |
|---|---|---|
| momentum / drift | +0.9652 | **+0.4544** |
| volatility / maturity | +0.9771 | **+0.4329** |
| drift / maturity | +0.9707 | **+0.4026** |
| drift / volatility | +0.9740 | **+0.3220** |
| momentum / maturity | +0.9514 | **+0.2399** |
| momentum / volatility | +0.9566 | **+0.1948** |
| **mean** | **+0.9658** | **+0.3411** |
| **effective forecasters (of 4)** | **1.03** | **1.98** |

**Error correlation understated diversity by roughly 2×.** The reason is structural: every model
here is a small tilt on the same price, so every error `p − y` is dominated by the shared `q − y`
term. Correlation near 1.0 is what anchoring produces, not evidence about the models.

Begin et al.'s ρ ≈ 0.70 was measured on LLM agents forecasting independently, where error
correlation *is* the right quantity. Applying it to a market-anchored ensemble is a category error,
and it would have said these four models were worth 1.03 opinions when they are worth about 2.

`tilt_correlations` — correlation of `p − q`, what each model adds beyond the market — is the
diagnostic that survives anchoring. **Both are now reported, with the confound documented at the
point of use.**

## Finding 2 — an apparatus bug that changed the ranking but not the verdict

Run 1 left features unstandardised. `maturity`, whose inputs are O(10) days and counts while every
other model's are O(0.01) price deltas, **diverged to a log score of 4.82** against a 0.336
benchmark. Its result was meaningless, not bad.

Fixed with train-only standardisation (statistics computed on the training split alone, so nothing
leaks). After the fix `maturity` scores 0.343.

**The fix reordered the models completely** — run 1's best was `momentum` (+0.00080, p = 0.4688);
run 2's is `drift` (+0.01193, p = 0.1174) — while leaving the verdict unchanged, since neither beat
the market. Worth recording precisely because the headline survived while everything under it moved.

## Finding 3 — two independent routes converge on the same frontier

| source | best effect | p | interpretation |
|---|---|---|---|
| Gate 1 `C_logit` | +0.01341 | 0.1139 | recalibrating the price |
| Gate 2a `drift` | +0.01193 | 0.1174 | a price-path feature |

Two unrelated methods land within 12% of each other on effect size and within 0.004 on p. Both say
the same thing: **something on the order of 1.2–1.3% of the log score may be available, and ~366
out-of-sample events cannot resolve it from noise.**

From p ≈ 0.117 one-sided, t ≈ 1.19; reaching t ≈ 1.65 needs about **1.9×** the events —
roughly **700 fold-events / 1,400–1,900 total**. That is the same re-test size Gate 1 arrived at
independently. Under AXIOMS A1 this is *"not enough evidence,"* not *"no effect."*

---

## Gate 2b — blocked, and not on machinery

An LLM forecaster cannot be evaluated on this dataset. These markets resolved inside frontier model
training windows, so any LLM score would measure recall rather than foresight — the exact failure
Hindcast, KTD-Fin and PolyBench exist to prevent, and which Paleka et al. identify as the dominant
flaw in the LLM-forecasting literature. The feature layer also deliberately excludes question text:
that is the channel through which training data re-enters.

Three routes exist, and choosing between them is an operator decision:

1. **Hindcast** — replays resolved Polymarket markets against a frozen pre-`t₀` Reddit snapshot,
   closing both leakage channels. Purpose-built for this. Requires verifying artifact availability.
2. **Forward paper evaluation** — forecast markets resolving *after* today. Leakage-free by
   construction, and slow: ~1,400 events at current listing rates is months.
3. **A model with a verifiable cutoff before each market's listing** — cheap, but restricts the
   universe to older markets and only pushes the problem back.

**Gate 2a does not license Gate 2b.** Nothing beat the market here, so there is no demonstrated
information channel for an LLM to be added to.

---

## Limitations

- **Four deterministic forecasters, all price-path.** A richer feature set (order-book depth,
  volume, cross-market structure) is untested and might behave differently.
- **One venue, one period, mid-range prices.** Same admission constraints as Gate 1.
- **Rungs 3–4 unrun.** The ladder stopped correctly, so simple pooling is untested rather than
  refuted.
- **The refactor.** `nullworld` and `forecasters` now share one fitter. Verified bit-for-bit
  identical to the pre-refactor inline loop across 12 configurations (max |Δ| = 0.000e+00), so
  Gate 0's recorded result stands without a re-run.
