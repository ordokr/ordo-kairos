# Gate M.0 — Maker dead-on-arrival check — Results

**Verdict: NOT REFUTED. The first hypothesis in this repository to survive its dead-on-arrival check
with room to spare — and the registered condition was the wrong weighting for its own hypothesis.**
Run 2026-09-14 on the reachable open universe. Reproduce with `python gatem.py`.

No order book was fetched: Gamma publishes `spread`, `orderPriceMinTickSize` and `volumeNum` on the
market listing. Nothing here trades or quotes (F3).

---

## Result

| | |
|---|---|
| Open markets swept (both volume orderings, to the offset ceiling) | **4,200** |
| Excluded as longshots outside the registered band | 1,543 |
| Missing quote fields | 1,167 |
| Order book not enabled | 54 |
| **In band, quotable, measured** | **1,436** |

### Tick room

| | |
|---|---|
| Spread in ticks — p25 / **median** / p75 / max | 1.0 / **2.0** / 9.0 / 1000.0 |
| Markets quoted at one tick (no room to improve) | 534 / 1,436 (**37.2%**) |
| **Share of *flow* sitting in one-tick markets** | **77.4%** |
| Markets advertising maker rewards | 1,318 / 1,436 |

### Gross capture

| | |
|---|---|
| Volume-weighted gross capture per $ of flow | **3.2564%** |
| Published annual flow across measured markets | $2,354,022,358 *(`volumeNum` assumed dollars, unverified)* |
| Ceiling at 100% of measured flow | **$76,657,509/yr** |
| **Ceiling restricted to markets with tick room** | **$29,280,877/yr** on $532,016,630 of flow, 902 markets |
| Registered floor (10× the taker ceiling) | $104.70/yr |
| Flow required to clear the floor | $3,215/yr — 0.000137% of measured flow |

## The constraint moved, and that is the finding

| | taker (Gate 4.0) | maker (Gate M.0) |
|---|---|---|
| opportunity set | visible mispricings | flow crossing the quote |
| measured size | **$24.40** deployable | **$532M/yr** of flow where there is room to quote |
| ceiling | **$10.47/yr** | **$29,280,877/yr** gross |

**Six orders of magnitude.** Capturing 0.0004% of the with-room flow would beat the entire taker
programme this repository spent four hypothesis classes testing. That is what it means for a
constraint to be structural rather than incremental: the taker constraint was *capacity* and could
not be elevated by any amount of edge search, and changing role removes it — replacing it with a
different constraint entirely.

**The new constraint is adverse selection and queue position, and it is not measured here.**

## The registered condition was the wrong weighting

The registered primary falsifier was *"the median in-band market must quote more than one tick."*
Measured: **2.0 ticks. It passes.**

But the hypothesis is about **flow**, and weighting every market equally does not ask about flow.
Asked of the money instead: **77.4% of measured flow sits in markets quoted at one tick**, where an
entrant cannot improve the quote and can only join the back of an existing queue. The unweighted
median and the flow-weighted picture disagree, and the disagreement was visible during the run — a
two-page sample of the volume head returned a median of **1.0 tick and a REFUTED verdict**, which
flipped to 2.0 and NOT REFUTED once the low-volume tail was included.

**Tick room and flow are anti-correlated**: the room is in markets nobody trades, and the flow is in
markets already quoted as tight as the grid allows.

**The condition is not being rewritten after the fact.** The registered verdict stands as it came
out; the defect is recorded in `CORRECTIONS.md` Pass 28.1; and the flow-weighted number is reported
beside it so no reader has to take the unweighted one on its own. It does not overturn the verdict —
$532M/yr of flow *does* sit in markets with room, and that is three orders of magnitude more than
the floor requires — but it materially changes what NOT REFUTED means here.

## What this does and does not license

**Licenses exactly one thing:** Gate M — a measurement of adverse selection and queue position on
real trade data. No executor, no quoting, no capital (F3).

**Does not license any claim that market making here is profitable.** Everything that determines
maker P&L is excluded from this gate:

| excluded | direction |
|---|---|
| **Adverse selection** — filled preferentially when the price is about to move against you | Against. This is the whole of maker P&L |
| **Queue position** — incumbents hold 77.4% of the flow at one tick | Against, and now quantified |
| **Inventory risk** — an unbalanced book is a directional position | Against |
| **Competition response** — incumbents requote when you arrive | Against |
| **Polymarket maker rewards** — 1,318 of 1,436 markets advertise them | **For**, and unmodelled |

The excluded terms do not merely trim the ceiling; they decide the sign. A gross spread of 3.26% per
dollar of flow is what you collect *if the flow is uninformed*, and the entire business of market
making is that it is not.

## Limitations

- **One snapshot**, and `spread` is a point-in-time quote.
- **`volumeNum` is cumulative, not a rate.** Daily flow is `volumeNum / days_since_start` — an
  average over each market's life, not a current rate, and it is stated as such.
- **`volumeNum` units are unverified.** Assumed dollars. If it is shares, every dollar figure here
  scales by the price level and the comparison to the floor changes.
- **1,167 markets were dropped for missing quote fields** — 28% of the sweep. Whether those are
  systematically different from the measured set is not known, and they are counted rather than
  merged into any other bucket (AXIOMS G5).
- **The offset ceiling applies.** 4,200 markets is what both orderings reach, not the venue.
- **Nothing here measures whether *we* could win.** It measures that there is a market to compete
  in, which is a different and much weaker claim.
