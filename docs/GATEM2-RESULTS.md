# Gate M2 — The subsidised maker: spread, rebates and holding rewards together

Run 2026-09-14 · `python gatem2.py --pages 12 --markets 200` · registration in
[`PROTOCOL.md`](PROTOCOL.md) Class M2, written before the runner existed and before any rebate
figure was computed.

> **VERDICT: NOT REFUTED — and subsidy-dependent, which is how it must be reported.**
> Net **$139,450/yr** at 2,000 posted contracts across 195 markets, against a **$104.70/yr** floor.
> The margin comes from the **maker rebate**, not from the spread and not from holding rewards.

---

## 1. What was measured

195 in-band, tick-room, fee-charging markets priced against live books.

| quantity | value |
|---|---|
| Spread kept per filled contract (median) | **+0.000390** — Gate M's 3.9% retention of the quoted half-spread |
| **Rebate per filled contract (median)** | **+0.001406** — **3.6x the spread** |
| Total per filled contract | **+0.001796** — **4.6x spread alone** |
| Holding rewards | 3.25%/yr on position value, **vs a 6% capital hurdle → fails on its own** |

## 2. Per-category, as the registration required

The fee rate and the rebate rate both vary by category, so a single median hides the structure:

| category | n | feeRate | rebateRate | spread/fill | rebate/fill | ratio |
|---|---:|---:|---:|---:|---:|---:|
| `sports_fees_v3` | 68 | 0.05 | 15% | +0.000780 | +0.001683 | 2.2x |
| `crypto_fees_v2` | 48 | 0.07 | 20% | +0.000390 | +0.001686 | 4.3x |
| `finance_prices_fees` | 24 | 0.04 | 25% | +0.000380 | +0.001600 | 4.2x |
| `politics_fees` | 20 | 0.04 | 25% | +0.000127 | +0.000934 | **7.4x** |
| `sports_fees_v2` | 16 | 0.03 | 25% | +0.000283 | +0.000716 | 2.5x |
| `economics_fees` | 9 | 0.05 | 25% | +0.000390 | +0.001414 | 3.6x |
| `weather_fees` | 5 | 0.05 | 25% | +0.000390 | +0.002344 | 6.0x |
| `tech_fees` | 4 | 0.04 | 25% | +0.000409 | +0.000819 | 2.0x |
| `culture_fees` | 1 | 0.05 | 25% | +0.000312 | +0.000594 | 1.9x |

**Politics has the highest ratio and the worst absolute spread.** Its markets are one-tick — the
half-spread a maker can retain there is `+0.000127`, a third of the universe median — so the rebate
carries 7.4x what the spread does. The ratio is high because the denominator is nearly gone, which
is the opposite of good news, and is exactly the reading Pass 28.1 exists to force.

## 3. The annual figures, with capital charged

Capital is **$1 per posted contract per market** — the cost of the hedged YES+NO pair that makes
holding rewards riskless — and is charged at this repository's **6%** hurdle.

| size | capital | spread/yr | rebate/yr | holding/yr | capital cost | **NET/yr** |
|---:|---:|---:|---:|---:|---:|---:|
| 25 | $4,875 | $537 | $1,621 | $158 | −$292 | **$2,024** |
| 100 | $19,500 | $2,149 | $6,482 | $634 | −$1,170 | **$8,096** |
| 500 | $97,500 | $10,697 | $32,241 | $3,169 | −$5,850 | **$40,257** |
| 2,000 | $390,000 | $34,627 | $115,548 | $12,675 | −$23,400 | **$139,450** |

**Holding rewards are a net loss.** At 2,000 contracts they pay $12,675 on capital that costs
$23,400 — a **−$10,725** contribution. They are in the table as a *negative* term, and the only
reason the strategy clears is that the rebate ($115,548) is 3.3x the spread capture and 4.9x the
entire cost of capital.

Reporting them as a positive, which the first run of this gate did, is the Pass 27.1 dimensional
error in a new costume: a 3.25% *rate* added to a dollar total without charging what the dollars
cost. Recorded as [Pass 33.3](CORRECTIONS.md).

## 4. Against the pre-committed expectation

| registered before the run | measured | |
|---|---|---|
| Rebate ≈ **6.4x** the spread | **3.6x** median | **wrong, and by a factor of ~2** |
| Total ≈ **7x** Gate 3.0's figures | **4.6x** per contract | **wrong in the same direction** |
| Holding rewards **fail** the 6% hurdle alone | 3.25% vs 6% | **confirmed** |
| Binding constraint reverts to **queue/fills** | both terms scale with fills | **confirmed** |

The expectation was computed at `p = 0.5` in politics, on the assumption that politics dominates the
tradeable universe. It does not — politics is **20 of 195** markets after the gate's own band and
tick-room preconditions — and the published rate table I transcribed into the registration is stale
in one row. Both errors are recorded in [Pass 33.2](CORRECTIONS.md); the arithmetic was never
affected, because the runner reads each market's live `feeSchedule` rather than a hardcoded table.

## 5. What holds this number up, and what does not

**The rebate is not a congestion game, and that is the structural finding.** The pool is
`rebateRate x total taker fees` and a maker's share is `own_fee_equivalent / total_fee_equivalent`,
so pool and share scale together: **rebate per filled contract is `rebateRate x feeRate x p(1-p)`
whatever other makers do.** Gate R measured the opposite regime — liquidity rewards, where every
entrant dilutes the share — and those two programmes must never again be reasoned about together.

**The fill model is the dominant uncertainty in the level, and not in the ratio.** Fills are
Gate 3.0's `max(0, side_flow - queue_ahead)` capped at posted size, and both the spread term and the
rebate term are linear in exactly that quantity. An error in the fill model moves every dollar
figure in this document proportionally and moves the **3.6x ratio not at all**.

**The level is not a forecast.** Two consecutive runs of this gate priced 194 and 195 markets and
produced $138,212 and $139,450, because the open universe drifts between sweeps and the cache sits
in a swept temp directory. Read the figures as a measured ceiling on a particular afternoon's book,
in the sense of AXIOMS G12 — an instrument's ceiling, not the world's floor.

## 6. Why this is not an edge

Both terms that make it work are set by the counterparty:

- **Maker rebates** are funded by fees Polymarket chose to introduce and can withdraw.
- **Holding rewards** are explicitly "variable and subject to change at Polymarket's discretion",
  funded from the treasury — a customer-acquisition subsidy, not a market inefficiency.

A subsidy the counterparty can switch off with one decision is a promotion. Class M survives as a
**subsidy-dependent strategy** and the registered consequence is that the next question — whether
the subsidy persists — is a **new registration**, not licensed here.

## 7. Unmodelled

- **Subsidy persistence.** The dominant risk, and no amount of measurement hedges a single decision.
- **Competitive response.** The rebate does not dilute, but the *spread* does: makers arriving for
  the subsidy compete the quoted spread down, and the spread term is already only 23% of the total.
- **Queue position** beyond Gate 3.0's model.
- **Inventory risk** on any position not held as a hedged pair. Holding rewards require *holding*,
  which a flat market maker by definition does not do — the two programmes pull in opposite
  directions and the table above pays the capital cost of resolving that tension toward holding.
- **F3 stands.** Nothing here traded, quoted, or touched capital.
