# Gate K.0 — Is there room to quote on Kalshi?

Run 2026-09-14 · `python gatek.py --pages 12` · registration in [`PROTOCOL.md`](PROTOCOL.md) Class K,
written before the runner existed and before any Kalshi spread figure was computed.

> **VERDICT: NO VERDICT.** Kalshi's flow with room to quote is **26.6%, 95% CI [18.4%, 39.1%]**,
> against Polymarket's measured **22.6%**. The interval straddles the comparator. A 4-point gap on
> one snapshot, inside a 20.7-point-wide interval, does not distinguish the two venues.
>
> Class K neither closes nor licenses the expensive gate.

---

## 1. The apparatus fact that shrank the gate before it ran

**Kalshi's market API exposes no fee, maker, taker, rebate or reward field of any kind.** Polymarket
publishes a per-market `feeSchedule` carrying `rate`, `rebateRate`, `takerOnly` and `exponent`, which
is what made Gate M2 possible. Kalshi publishes none of it, and `kairos/kalshi.py` has recorded the
published schedule as **unverified** since 2026-09-09 (HTTP 429 from the site, 404 on the
documentation paths).

**So there is no Class M2 equivalent here, and there cannot be one from this apparatus.** The
$139,450/yr rebate finding has no counterpart to compare against. This gate is about the spread and
nothing else, and that was registered before it ran rather than discovered afterwards.

## 2. What was measured

19,818 markets across 2,400 events. The preconditions removed most of them:

| refusal | markets |
|---|---:|
| `no_flow` (zero 24h volume) | 12,909 |
| `no_two_sided_quote` | 3,945 |
| `longshot_out_of_band` | 1,742 |
| `not_active` | 98 |
| **eligible** | **1,124** |

**65% of Kalshi's listed markets traded nothing at all in 24 hours.** Total eligible flow across the
venue was **$319,300/day** — which is the more arresting number in this document and is discussed in
§5.

## 3. Spread in ticks, by tick structure

| tick | markets | 24h flow | median ticks | flow with room |
|---:|---:|---:|---:|---:|
| 0.0010 (`deci_cent`) | 56 | $14,627 | 21.00 | 20.3% |
| 0.0100 (`linear_cent`) | 1,068 | $304,672 | 4.00 | 26.9% |

Spread is expressed in **ticks**, never cents, because the venue runs three tick structures and cents
are not comparable across them.

## 4. The weighting is the whole finding

| statistic | value |
|---|---:|
| Median spread **by market** | **5.00 ticks** |
| Median spread **by flow** | **1.00 tick** |
| Flow **with** room to quote | 26.6% |
| Flow **pinned at one tick** | **73.4%** |

By market count Kalshi looks spacious — five ticks of room. Weighted by the dollars that would
actually have to fill you, the median market is quoted **at one tick**, where an entrant cannot
improve the quote and can only join the back of a queue.

**This is Gate M.0's defect reproducing exactly on a different venue.** There, the registered
condition passed on a median of 2.0 ticks by market while 77.4% of flow sat at one tick
([Pass 28.1](CORRECTIONS.md)). Here it is 5.00 by market and 1.00 by flow, 73.4% pinned. The
correction was applied in advance this time, which is the only reason the gate reports the right
number.

## 5. Why the two venues are hard to tell apart

Kalshi 73.4% pinned, Polymarket 77.4% pinned. The bootstrap interval on the Kalshi figure is
[18.4%, 39.1%] and contains Polymarket's 22.6% comfortably.

That interval is wide because flow is **concentrated**: a handful of markets carry most of the
$319,300, so resampling markets moves the weighted share a long way. The width is not a defect in the
estimator — it is the honest statement that a venue-level share resting on a few heavy markets is
barely estimated at all from one snapshot.

## 6. Against the pre-committed expectation

| registered before the run | measured | |
|---|---|---|
| Kalshi looks **worse** than Polymarket (coarse 1c tick forces quotes together) | 26.6% vs 22.6% point estimate | **directionally wrong** |
| …and the gate **refutes** | interval straddles; **no verdict** | **wrong, but not in the hypothesis's favour** |

I expected refutation and registered that expectation explicitly. The point estimate went the other
way and the interval swallowed the difference. Recording both matters: had I registered no
expectation, a 4-point gap could have been narrated as encouraging.

## 7. What this does not cover

- **Fees and rebates.** Not exposed by the API, schedule still unverified. The term that carried all
  of Gate M2's economics is **unmeasurable here**.
- **Adverse selection** — the term that killed Class M on Polymarket, taking 96.1% of the spread.
  Tick room is a *precondition* for a maker edge, never evidence of one.
- **Queue position**, inventory, and the whole of Gate 3.0's machinery.
- **One snapshot.** Flow, spreads and listings all change continuously.
- **F3 stands.** Nothing traded, quoted, or touched capital.

## 8. What it means

Kalshi is not obviously better and not obviously worse than a venue already measured to hand a maker
**3.9%** of the half-spread. It is also roughly **$319,000/day of total eligible flow** — for
context, Gate M2's Polymarket figure of $139,450/yr assumed posting 2,000 contracts across 195
markets, and the whole of Kalshi's daily qualifying turnover would not support many operators of
that size.

The honest read: this was the cheapest remaining trading question in the repository, it cost one
afternoon, and it returned **no verdict**. That is not a reason to run the expensive gate.
