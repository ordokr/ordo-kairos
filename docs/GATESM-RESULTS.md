# Gate SM.0 — A different counterparty population (Smarkets)

Run 2026-09-14 · `python gatesm.py --events 200` · registration in [`PROTOCOL.md`](PROTOCOL.md)
Class SM, written before the runner existed and before any Smarkets spread figure was computed.

> **VERDICT: NO VERDICT.** Flow-weighted median half-spread **0.00630** against a comparator of
> **0.00500**; the share of flow quoted wider than the comparator is **62.4%, 95% CI [43.3%, 86.7%]**,
> which straddles 50%. Class SM neither closes nor licenses the expensive gate.
>
> **The registered confound paid for itself.** On Gate K.0's statistic Smarkets reads **100.0%**
> against Kalshi's 26.6% — a spectacular apparent win that is **entirely a tick-size artefact**.

---

## 1. Why this was not another venue test

Gate K.0 varied the venue and found two indistinguishable. The variable never varied is the
**counterparty**. Every class in this repository traded against political and crypto participants,
whom Gate M measured taking **96.1%** of the half-spread. Smarkets' flow is largely recreational
sports bettors.

SX Bet was rejected as the candidate for a stated reason: it is crypto-native, so its population is
the one Classes F and M already measured. Testing it would have varied the venue while holding the
counterparty fixed — which is what Gate K.0 already did.

## 2. The apparatus, measured rather than assumed

The decimal-odds ladder was derived from **283 distinct prices across 2,563 books**, not from
documentation:

| odds | 1.01–2.0 | 2–3 | 3–4 | 4–6 | 6–10 | 10–20 | 20+ |
|---|---|---|---|---|---|---|---|
| increment | 0.01 | 0.02 | 0.05 | 0.10 | 0.20 | 0.50 | 1.00 |

Which gives a **price-dependent** probability tick of roughly **0.005–0.008** — finer than
Polymarket's and Kalshi's flat cent, and the source of the confound in §4.

## 3. What was measured

84 live events, 3,267 markets, 9,340 quoted contracts.

| refusal | contracts |
|---|---:|
| `no_two_sided_quote` | 7,840 |
| `no_flow` | 708 |
| `longshot_out_of_band` | 514 |
| **eligible** | **278** |

**84% of quoted contracts have only one side.** A maker needs a two-sided market to work in; most of
this venue does not offer one.

| statistic | value |
|---|---:|
| Flow-weighted **median half-spread** | **0.00630** |
| Comparator (Kalshi measured; repo standing `CONSERVATIVE.half_spread`) | 0.00500 |
| Share of flow quoted **wider** than the comparator | **62.4%** |
| 95% CI on that share | **[43.3%, 86.7%]** |

The interval straddles 50%, so the median is not established as being above 0.005. The point estimate
is 26% wider than the comparator; the interval is 43 points across and cannot support that.

**On the equivalence of the implemented and registered tests:** the registration specified an
interval on the flow-weighted median against 0.005; the runner intervals the *share of flow above
0.005* against 50%. These are the same test — a weighted median exceeds `x` if and only if the
weighted share above `x` exceeds 50% — and the share formulation bootstraps more stably than a
quantile. Noted so the formulation is not mistaken for drift ([Pass 37.3](CORRECTIONS.md)).

## 4. The confound, registered in advance and then demonstrated

Gate K.0's statistic is *share of flow whose spread exceeds one tick*. Applied to Smarkets it returns:

| venue | tick | Gate K.0 statistic |
|---|---:|---:|
| Kalshi | 0.0100 | 26.6% |
| Polymarket | 0.0100 | 22.6% |
| **Smarkets** | **~0.005–0.008** | **100.0%** |

Every single eligible Smarkets market clears "more than one tick" — because the tick is roughly half
the size, not because the venue is more generous. **Reusing Gate K.0's statistic unchanged would have
produced a four-fold apparent improvement out of nothing**, and it would have been the most exciting
number this repository has produced.

The registration named this confound before the run and moved the primary onto the half-spread in
probability units, which is comparable across all three venues. That is the single most useful thing
this gate did, and it did it before seeing any data.

## 5. Against the pre-committed expectation

| registered before the run | measured | |
|---|---|---|
| Half-spread **at or below** 0.005, therefore **REFUTED** | 0.00630 point estimate | **directionally wrong** |
| | interval straddles → **NO VERDICT** | the gate did not refute, and did not pass |

Expected refutation; got no verdict with a point estimate pointing the other way. Recording the
expectation is what keeps "62.4%" legible as *an interval that straddles* rather than as encouragement.

## 6. What this does not cover

- **Commission on net winnings.** Smarkets charges a percentage of *winnings*, which is structurally
  unlike a per-contract fee and is hostile to a market maker in a way this gate does not model. Not
  in the API, not verified, not claimed.
- **Mechanisms that tax consistent winners.** Betting exchanges are known to operate them. Grade U
  ([`EVIDENCE.md`](EVIDENCE.md)) — recorded so it is not forgotten, never used as a planning input.
- **Adverse selection itself** — the entire point of the class — needs a trade time series and is not
  measured here. Gross spread is a precondition for a maker edge, never evidence of one.
- **Operator eligibility** on a UK-licensed venue, exactly as with Binance in Gate F.
- **One snapshot**, 278 eligible markets, and a 43-point-wide interval.
- **F3 stands.** Nothing traded, quoted, or touched capital.

## 7. What it means

The counterparty-population hypothesis is **not refuted and not supported**. The one suggestive
number — a median half-spread 26% wider than the comparator — sits inside an interval far too wide to
carry it, on a venue where 84% of contracts are quoted one-sided.

Establishing whether recreational flow is less toxic needs the realized-half-spread measurement over
a trade time series, which is a new registration and a materially more expensive gate. Nothing here
licenses it, and the wide interval is a reason to expect that gate would need a lot of data to say
anything either.
