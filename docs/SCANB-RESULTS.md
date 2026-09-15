# Class B candidate scan — Results

**Verdict: no candidate. Class B's binding constraint is structural, not pricing.** Run 2026-09-09
on the **full reachable open universe**, swept from both ends of the volume distribution.
Reproduce with `python scanb.py --pages 21 --groups 120`.

This is a **candidate generator**; nothing here trades, sizes a position, or touches capital
(A5, D1, F3).

---

## Result

| | |
|---|---|
| Open negRisk markets pulled | **2,246**, in **769 events** (186 with >= 3 legs) |
| **Groups with at least one untradeable leg** | **99 (53%)** |
| Groups partially settled | 6 |
| **Verified, completable, and priced** | **78** |
| ...with a positive post-cost edge at 25 contracts/leg | **0** |
| Genuinely too thin to fill | 2 |
| Unexplained failures | **0** |

Closest to profitable: **-0.00597/contract** (event 606384, 5 legs, 1.2 days). No group crossed
zero.

| event | legs | days | edge/contract |
|---|---|---|---|
| 606384 | 5 | 1.2 | **-0.00597** |
| 606452 | 5 | 9.4 | -0.01221 |
| 624242 | 19 | 21.9 | -0.03446 |
| 48292 | 7 | 114.0 | -0.03894 |
| 51456 | 13 | 112.7 | -0.04647 |
| 106981 | 3 | 114.0 | -0.05031 |

Every completable group costs **0.6%-16% more than the $1 it pays**, after real ask-book VWAP at
size, taker fees and carry. The market is not giving anything away.

## The finding: you cannot assemble the set

**53% of live groups (99/186) contain at least one leg that cannot be bought.** The buy-every-leg identity
requires *all* legs; if one is untradeable the set cannot be completed, and no price on the
remaining legs recovers the guarantee. This is a structural refusal (D1), not a pricing one, and it
is the dominant reason Class B has so little raw material.

It also means the tradeable universe is far smaller than the market count suggests: 2,246 open
negRisk markets → 769 events → 186 groups of usable size → **78 completable**.

## Apparatus: `active` is the only flag that predicts a tradeable leg

Legs that cannot be bought return **HTTP 404** from the CLOB `/book` endpoint. Measured across 10
groups, every 404 leg had:

| field | value on a 404 leg |
|---|---|
| `enableOrderBook` | **True** |
| `acceptingOrders` | **True** |
| `active` | **False** |

**The two obvious flags are both wrong here.** A scanner filtering on `enableOrderBook` or
`acceptingOrders` — the names that sound like they mean "you can trade this" — would have kept every
one of these legs and then failed at fetch time, or worse, priced the set from whichever legs
happened to respond.

## Two apparatus facts that would each have produced a false result

**The order book is sorted worst-first.** Asks arrive descending (`0.999, 0.998, 0.95, …`), so
`asks[0]` is the price you would never get. Verified against Gamma's own `bestAsk` on 12 markets:
best ask equals `asks[-1]` in **12/12** and `asks[0]` in **0/12**, where `asks[0]` was 0.999 every
time. `kairos.book` normalises both sides to best-first once, so no consumer rediscovers this.

**A crossed price must not be charged spread twice.** `effective_yes_cost` takes a *mid* and adds
`half_spread` to model crossing. A VWAP walked off the asks has already crossed. Added
`effective_yes_cost_at`, which applies taker fee and carry to an already-traded price — and is not
the same as `maker=True`, which would suppress the spread but also swap in the maker fee, when
taking the ask is a taker trade.

---

## A false claim this run nearly published

The first version reported **"thin/unavailable 29"** — a single bucket merging "the book was too
thin to fill 25 contracts" with "the book never loaded". Read naturally, that says *most negRisk
groups lack the depth to trade*, which is a claim about the venue's liquidity.

Separating the two (AXIOMS G5) gave: **too thin 0, unfetchable 29.** Not one group was genuinely
thin. Every failure was HTTP 404 — which then turned out not to be a failure at all, but the
untradeable-leg finding above.

Three readings of the same 29 groups, in order: *"the venue is illiquid"* → *"our fetching is
broken"* → *"the sets cannot be assembled"*. Only the third is true, and only the last is a fact
about Class B. The whole distance was travelled by refusing to let an error and a measurement share
a counter.

## Limitations

- **One sample, one moment.** Books change by the second; this is a snapshot, deliberately uncached.
- **Discovery now covers the whole reachable open universe** - 21 pages swept in *both* volume
  orderings, deduped, because Sethi & Kline and Abinzano et al. locate surviving mispricing in
  low-attention contracts and a head-only null would be weakest exactly there. `offset` caps at
  2100 on open markets as it does on closed ones, so this is the universe offset pagination can
  reach, not a sample of it. A venue-wide sweep would need date-windowed discovery, as Look 3
  needed for closed markets.
- **`days_to_settlement` is nominal.** Open markets have no realised resolution date. Markets
  usually resolve early, so the nominal date is late, which *overstates* carry and makes edges look
  worse — the safe direction, but an estimate.
- **Quote persistence is unmodelled.** Nothing here accounts for a counterparty withdrawing when
  hit, which is the usual reason a screen-visible arbitrage is not executable. Gate 3.
- **No candidate ≠ no edge.** This measures one venue, one size (25 contracts a leg) and one
  moment. A different size, a different venue, or a different instant could differ (A1).
