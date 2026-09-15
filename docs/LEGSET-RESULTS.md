# Leg-set verification — Results

**Built and validated 2026-09-08; exhaustiveness sample extended 2026-09-09.** Gate B measured that the entire Class B false-positive defence
rests on leg-set verification rather than on the scanner. This is that layer, and the threat it
defends against turned out to be much larger than the census anecdote suggested.

---

## The threat, measured

Groups were assembled exactly the way a paginated `/markets` scan assembles them — take whatever the
pages returned, group by `negRiskMarketID` — and then checked against the authoritative event
listing:

| | |
|---|---|
| Groups checked | 80 |
| **Truncated** | **39 (49%)** |
| Legs missing across truncated groups | **519 of 865 (60%)** |
| Worst case | held **49 of 117** legs |

**Half the groups were incomplete, and those were missing three fifths of their legs.** A group
missing 60% of its legs sums to roughly 60% less than it should, which presents as a spectacular
arbitrage. The census's "53% arbitrage" was not an unlucky one-off; it is the *typical* output of
scanning grouped markets through offset pagination.

The rate depends on how a scan paginates — it is a property of the retrieval method, not a constant
of the venue — but any offset-paginated assembly has this shape, because page boundaries do not
respect group boundaries and nothing in the response says a group was split.

## The authority, cross-checked rather than trusted

`/events/<id>` returns the full market list for a group. Verified against the live API on a 70-event
sample:

- markets per event **3–51**, no round-number cap — it does not silently truncate the way offset
  pagination does (the largest group found in the truncation study had **117** legs);
- **0/70** events spanned more than one `negRiskMarketID`, so event id is a safe group key;
- `negRiskRequestID` is **not** a group key — it is per-market (2,896 ids across 2,896 markets) and
  grouping on it yields singletons. Checking this cost one query and would otherwise have produced a
  scanner that saw every group as a single leg.

`verify_leg_set` does **not** assume the event is authoritative. If the held set contains a market
the event does not list, the event is refused as non-authoritative for that group. Trusting an
endpoint to be complete is the assumption that created the problem in the first place.

---

## Exhaustiveness: the measurement contradicted the obvious rule

If the listed outcomes do not cover the space, an unlisted outcome resolves every leg NO, the set
pays **$0** instead of $1, and the "riskless" trade loses the whole stake. That is a different sign
of error, not a smaller one.

The obvious rule — require an explicit `negRiskOther` catch-all leg — discards most of the universe:
only **36%** of negRisk events carry one. So the base rate was measured directly instead.

**Across 512 fully-resolved negRisk groups, every single one had exactly one winning leg.**
Zero-winner groups: **0/512**. Multi-winner groups (which would falsify mutual exclusivity in the
other direction): **0/512**. Reproduce with `python exhaustiveness.py`.

That does not make the risk zero, and the module refuses to treat it as such. Zero failures in 512
trials bounds the rate at about **0.59%** (rule of three). The bound is a function of how much has
been checked, so it shrinks by measuring more groups and by nothing else.

| measured | trials | failures | bound | smallest tradeable edge |
|---|---|---|---|---|
| 2026-09-08 | 75 | 0 | 0.0400 | ~5% |
| **2026-09-09** | **512** | **0** | **0.0059** | **~1%** |

**Survivorship checked, not assumed.** A group where nothing won might be *voided* rather than
resolved, and voided markets report `["0","0"]` — which a clean-resolution filter silently drops,
making the sample structurally unable to contain the failures it is looking for. Measured across
**4,968 closed negRisk legs: zero voided, zero unparseable, zero settled between the extremes.**
The channel does not exist here, and `exhaustiveness.py` re-checks it on every run rather than
trusting this paragraph.

### Why a small bound is still not free

If the group fails, the entire stake is lost, not the edge. So

> `EV = (1 − q)·edge − q·stake` ⟹ break-even at **`q* = edge / (edge + stake)`**

| edge | break-even failure rate | vs 0.59% bound |
|---|---|---|
| 0.5% | 0.0050 | **not tolerable** |
| 1% | 0.0100 | tolerable |
| 2% | 0.0200 | tolerable |
| 5% | 0.0500 | tolerable |

At the original 75-trial sample the floor was ~5%; at 512 it is **~1%**. A "riskless" trade whose
failure mode costs a hundred times its profit needs its failure rate measured, not assumed — and
measuring it is what moved the floor.

This is why `LegSetVerification.exhaustive()` takes the edge as an argument. Exhaustiveness safety is
a statement about the *trade*, not about the group.

**The lever was sample size, and it has been pulled.** Going from 75 to 512 groups cost 153 seconds
of fetching and moved the tradeable floor from ~5% to ~1% — a far larger widening of the Class B
universe than any change to the scanner could produce. It remains the cheapest lever: the bound is
`3/n`, so the next halving needs ~1,000 groups.

---

## What changed in the scanner

`scan()` reads `legs_are_complete` and `outcomes_are_exhaustive` off the group. That is honest inside
a null world, where the harness knows the truth, and is exactly the hole Gate B measured:
`truncated_believed` fires **1.000 at every horizon** because a caller can assert completeness that
nothing checked.

`scan_verified()` takes a `LegSetVerification` instead and refuses anything not carrying one — the
old boolean raises `TypeError` rather than being silently accepted. Order of operations:

1. refuse unless the leg set verified;
2. cost arithmetic against a nominal $1 (carry charged once — C7);
3. **exhaustiveness tested at the resulting edge**, since tolerance scales with edge;
4. fillability last (D1).

Driven in `tests/test_legset.py`: a truncated group summing to 0.40 — a spectacular fake arbitrage —
cannot fire, and an edge too thin to absorb the current bound is refused on exhaustiveness risk.
Those tests derive their edges **from the measured bound** rather than pinning a number: the first
version hard-coded 2% as "too thin", which was true at 75 trials and false at 512. It failed for the
right reason when the evidence improved, and editing the constant would have silenced the mechanism
it was there to check.

---

## Limitations

- **The exhaustiveness sample is 512 groups.** Everything above turns on that number. The 0.59%
  bound is stated as a bound rather than a rate, and it is not zero: `3/n` never reaches zero
  however many groups pass (A6).
- **Resolved groups only.** The exactly-one-winner measurement necessarily used settled groups; it
  assumes the mechanism behaves the same for open ones.
- **The event endpoint is the authority, cross-checked but not proven.** The cross-check catches an
  event that omits a leg we hold. It cannot catch an event that omits a leg *nobody* fetched.
- **Depth is still synthetic.** `MIN_FILL` is enforced against a modelled field; no order-book data
  has been touched. That remains a Gate 3 question, along with a counterparty who withdraws on being
  hit.
- **One venue.** All of this is Polymarket's negRisk structure.
