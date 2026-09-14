# Gate D.0 — Class C dead-on-arrival check — Results

**Verdict: split. Class C is NOT refuted as measured, and IS refuted inside the registered
tradeable band.** Run 2026-09-14 on the 140-pair adjudicated alignment table. Reproduce with
`python gated.py`.

This is a **falsifier**, not a measurement of edge. Surviving it means only *not dead on arrival*;
it licenses Gate D (the convergence null gate) and nothing else. Nothing here trades, sizes a
position, or touches capital (F3), and **no price history was fetched, so no pair is spent**.

---

## What was registered before the number existed

`docs/PROTOCOL.md` Class C registered the adverse prior in the same breath as the hypothesis: a
convergence round trip crosses **four** books where Class B's crossed two and let settlement pay the
rest, so from the Class B run's `0.0834` zero-fee cost — roughly `0.019` of it carry at 114 days —
four crossings should cost around `0.13` against carry savings of at most `0.019`.

**The measured four-crossing round trip is `0.02824`, not `0.13`.** The registration's estimate was
off by a factor of about four, and in the direction that favours the hypothesis. The cause is
identifiable: the `0.065`-per-two-legs figure it extrapolated from was a *hold to settlement* cost on
a ~114-day median horizon, and the crossing component of it is much smaller than the carry-laden
total implied. An estimate built by subtracting one modelled quantity from another was not a
substitute for walking four books, which is the whole reason Gate D.0 was registered as a
measurement rather than left as the arithmetic in the registration.

## Result

| | |
|---|---|
| Aligned pairs in the table | **140** |
| Closed since adjudication (2026-09-09) | 7 |
| Unpriced at every size (a leg could not be filled) | 51 |
| **Priced at 25 contracts a side** | **81** |
| ...of which longshots outside the registered band | **52 (64%)** |
| ...**inside** the band | **29** |

### The size curve (C11 — a design variable is not held at one value)

| size | n | median gap | largest gap | median round trip | zero-fee round trip |
|---|---|---|---|---|---|
| 5 | 82 | +0.00000 | +0.10200 | 0.02754 | 0.01515 |
| 10 | 81 | +0.00000 | +0.10200 | 0.02824 | 0.01515 |
| **25** | **81** | **+0.00000** | **+0.09775** | **0.02824** | **0.01612** |
| 50 | 81 | +0.00000 | +0.09488 | 0.03097 | 0.01713 |

**The median gap is zero at every size.** The typical aligned pair shows no executable deviation at
all; the distribution is a spike at zero with a short right tail. Whatever Class C would be trading,
it is not a broad property of dual-listed events.

### The two verdicts

| reading | n | largest gap | median round trip | verdict |
|---|---|---|---|---|
| as measured | 81 | +0.09775 | 0.02824 | **NOT REFUTED** |
| inside the registered band | 29 | +0.05000 | **0.08638** | **REFUTED** |

## The finding: the verdict turns on a precondition no scanner here enforces

`docs/PROTOCOL.md` **Market-selection preconditions (apply at every gate)** exclude *"longshots,
where fee structure mechanically worsens post-fee returns"*, and `CostModel.price_in_band` exists to
do it. **It is called in `kairos/gate.py` and `kairos/sizing.py` and nowhere else.** No scanner
applies it — not `gated.py` as first written, and not `scanb.py` or `scanc.py`, whose measurements
are already recorded as results.

It is load-bearing here. The single widest gap in the table is:

| pair | Polymarket YES | Kalshi YES | gap | its own round trip |
|---|---|---|---|---|
| Will the US confirm that aliens exist before 2027? | **0.0380** | 0.1554 | +0.09775 | 0.04418 |

An 11.7pp cross-venue disagreement on a market quoted at under four cents. It is out of band on the
Polymarket leg, and **it alone is what keeps the unbanded reading alive**: remove it and the largest
in-band gap is `+0.05000` against a median round trip of `0.08638`.

**Why the banded median round trip is three times the unbanded one**, which reads backwards until
the mechanism is named: a longshot pair quoted 0.02/0.98 has a tiny round trip *in absolute price
units* because the fee is quadratic in price and the absolute spread is small. It looks cheap and is
ruinous in relative terms — Whelan 2023's fee-induced favourite–longshot effect, which is the
published reason the band exists. Longshots drag the unbanded median down and inflate the unbanded
largest gap at the same time, pulling both sides of the comparison in the hypothesis's favour.

**Neither reading is chosen here.** The banded row is what the protocol says; the unbanded row is
what every prior Class B measurement in this repo actually did. Substituting one silently would have
made this run non-comparable with the Class B result it exists to be compared against, and choosing
after seeing both is the move `AXIOMS` A8 forbids.

## The first run did not have the band, and its verdict is recorded

The band check was **absent from the first execution** of `gated.py`, which reported a bare
`NOT REFUTED` on largest gap `+0.09775` against median round trip `0.02824`. The omission was found
by inspecting the pairs behind the headline, not by a test. It is recorded in `CORRECTIONS.md`
Pass 26 rather than quietly patched, because the fix moved the verdict **toward the outcome the
registration predicted**, which is the shape of a change that deserves more suspicion than a
surprising one, not less.

## The unverified Kalshi fee is not the cause of anything here

`KALSHI_FEES.verified` is `False` — the published schedule returned HTTP 429 on 2026-09-09 — so the
registered fallback (the conservative quadratic form, coefficient 0.07) applies. Following
`scanc.py`'s pattern, the zero-fee verdict is reported alongside: at **zero fees** the median round
trip is `0.01612` and the unbanded reading is still `NOT REFUTED`. The fee assumption does not
decide the unbanded verdict, and the banded verdict is decided by a `0.08638` round trip that zero
fees would not close either.

## Limitations

- **One snapshot, one moment.** Books change by the second and nothing is cached. A gap visible now
  is not a gap that persists to an order.
- **Entry and exit are priced off the same instant.** Gate D.0 asks what crossing in and straight
  back out costs *now*; it cannot model the gap having moved by the time the exit is taken. That is
  the whole content of Gate D and it is untested.
- **Quote persistence is unmodelled.** Nothing accounts for a counterparty withdrawing when hit —
  the usual reason a screen-visible deviation is not executable. Gate 3.
- **Basis risk is not priced.** Every pair in the table is `FUNGIBLE-WITH-BASIS`; none is
  `IDENTICAL`. The Somaliland pair's legs settle 10h01m apart. A "hedge" across a divergence window
  is two positions, and both can lose.
- **Both venues are charged the same cost model**, as `scanc.py` does. Kalshi's schedule is
  unverified; see above.
- **`days_held` is the registered 7 days**, not a measured holding period. No history has been
  fetched, so no realised convergence time exists to use.
- **NOT REFUTED is not an edge.** ~~Two pairs of 81 have a gap exceeding their own round trip.~~
  **CORRECTED 2026-09-14 — that count was inferred from the top-10 table above, never measured.**
  Counted directly by `gate4.py` on a later snapshot: **4 clear their own round trip, of which 3 are
  longshots outside the registered band, leaving 1.** The inference was wrong in both directions.
  See `CORRECTIONS.md` Pass 27.2 and [`GATE4-RESULTS.md`](GATE4-RESULTS.md). This
  gate compares the largest gap to the *median* cost by registration, a comparison deliberately
  stacked in the hypothesis's favour so that a refutation cannot be blamed on a harsh test. It is
  not evidence that a convergence trade is profitable, and it may not be reported as such.
