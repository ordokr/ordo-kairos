# Gate F — Funding-rate carry — Results

**Verdict: REFUTED. At no leverage does net return on deployed capital clear the 6% this repo
already charges for locked collateral.** Run 2026-09-14. Reproduce with `python gatef.py --nulls`
then `python gatef.py`.

Nothing here trades (F3). Venue eligibility is an operator precondition this repo does not assert.

---

## The null gate — PASSED, on the second attempt

| world | median RoC | pays | liquidated | truth | verdict |
|---|---|---|---|---|---|
| liquidation_cascade | −0.61% | 0% | 100% | loses | PASS |
| bear_regime | −5.14% | 0% | 2% | loses | PASS |
| costs_exceed_carry | −0.04% | 0% | 0% | loses | PASS |
| steady_carry | +4.85% | 100% | 2% | pays | PASS |
| high_funding | +9.83% | 100% | 10% | pays | PASS |

**Exhibit:** on the liquidation world the naive carry sum reports **+4.71%** where the truth is
**−0.67%** — it never looks at the price, so it reports the premium and ignores the risk that
premium is paid for. A 5.4-point error that flips the sign.

## The measurement

Gross funding, OKX, 98 days to 2026-09-14: **BTC +4.55%/yr, ETH +3.26%, SOL +2.26%** — before any
cost. Net of four crossings, liquidation and the capital both legs lock:

| instrument | 1x | 2x | 3x | 5x | 10x |
|---|---|---|---|---|---|
| **BTC** | +1.90% | +2.53% | **+2.85%** | −2.72% ⚠ | −5.66% ⚠ |
| **ETH** | +1.25% | +1.67% | −3.56% ⚠ | −3.96% ⚠ | −5.83% ⚠ |
| **SOL** | +0.74% | −2.59% ⚠ | −3.45% ⚠ | −5.22% ⚠ | −5.77% ⚠ |

⚠ = liquidated on the real price path. Best case **+2.85%** against a **6%** hurdle.

**The trade-off is measured, not argued.** Leverage is the only lever that raises return on
capital, and it is the same lever that lowers the breach threshold: BTC pays most at 3x and is
liquidated at 5x. Even this calm-looking window breached 5x on BTC and 2x on SOL.

## The defect the null gate caught

The first estimator credited the spot leg at the **overshot** price when a period jumped past the
liquidation trigger — paying the whole jump while losing only the fixed margin, and so
**manufacturing a profit out of a liquidation**. It reported a profit in 35% of replications of a
world that liquidated 100% of the time.

Exchanges liquidate continuously; nobody keeps the overshoot. Crediting at the threshold makes the
residue exactly maintenance + penalty + one crossing, and the larger loss is the carry never earned
afterwards. Fixed in the estimator, not the worlds (A8). See `CORRECTIONS.md` Pass 32.

## Measured apparatus limits

- **`fapi.binance.com` returns HTTP 451 — Unavailable For Legal Reasons** from this jurisdiction.
  The deepest-liquidity venue is legally unreachable.
- **OKX caps funding history at 98 days** (296 records; page 3 genuinely empty, verified against a
  retrying fetcher so the limit is not a swallowed error — Pass 9). dYdX publishes hourly funding
  but reaches only ~41 days.
- **The sample therefore cannot be guaranteed to contain an unwind**, which is why the null gate
  carries the crash discipline and why the refutation rests on it rather than on the window.

## Limitations

- **Exchange default is unmodelled** and cuts against — Pindza measures counterparty episodes as
  *more damaging than price crashes*; FTX is the realized case.
- **Crowding is unmodelled.** Arbitrage capital growth measurably lowers carry returns.
- **Breach detection uses daily closes**, which misses intraday squeezes and therefore *understates*
  liquidation frequency.
- **One venue, three instruments, 98 days, one regime.** Carry has exceeded 40%/yr in boom periods;
  that the reachable window shows 4.55% gross is itself the finding — **this is a regime exposure,
  not a harvest.**
