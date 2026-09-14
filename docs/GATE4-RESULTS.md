# Gate 4.0 — Capacity ceiling — Results

**Verdict: the registered floor was cleared, and the floor cannot bear the weight.** Run 2026-09-14
on the reachable Class C opportunity set. Reproduce with `python gate4.py`.

The measurement succeeded. **The registered decision rule did not**, and that is the finding worth
more than the verdict — see §"The floor was scale-free" below and `CORRECTIONS.md` Pass 27.

Nothing here trades, sizes a position, or touches capital (F3).

---

## Result

| | |
|---|---|
| Aligned pairs priced at 25 contracts a side | **82** |
| Priced but not clearing their own round trip | **78** |
| Clearing, but excluded as longshots | 3 |
| **Clearing their own round trip, inside the registered band** | **1** |

The single surviving opportunity in the entire reachable dual-listed universe:

| opportunity | net edge / contract | capital locked |
|---|---|---|
| Will Alexandria Ocasio-Cortez win the 2028 US Presidential Election? | +0.00803 | $24.40 |

### The ceiling

| | |
|---|---|
| Distinct clearing opportunities | **1** |
| **Deployable capital, right now, across the whole universe** | **$24.40** |
| Generous annual ceiling | **$10.47/yr** |
| Registered hurdle (6% of capital locked) | $1.46 |
| Recurrence the hurdle requires | 7 / yr |
| Recurrence physically possible at a 7-day hold | 52 / yr |

Every assumption behind `$10.47` is optimistic by registration: perfect fills (`hit_rate = 1.0`),
zero infrastructure and research cost, **complete** convergence on every trade, and instant
redeployment the moment a position is exited. The real number is lower and cannot be higher.

The recorded Class B row, entered at its **best** observed edge (`-0.00597`, from
`SCANB-RESULTS.md`), returns `-$607/yr` at the same horizon-limited recurrence. No frequency rescues
a negative edge, which is why `required_opportunities_for` returns infinity rather than a large
number.

## The floor was scale-free, and that is a registration defect

The registered objective floor was *"beat the repo's own `settlement_wedge_annual` (6%/yr) on
capital locked."* Against `$24.40` of deployable capital that hurdle is **$1.46**, and `$10.47`
clears it comfortably — a 43% annual return on capital.

**43% on twenty-four dollars is ten dollars.** The floor tests a *rate*; the constraint is a
*magnitude*. Any positive edge passes a rate hurdle when the denominator is small, so the test as
registered cannot distinguish "this is a business" from "this is ten dollars a year," which is the
exact question Gate 4.0 was built to answer.

This was not visible when the floor was chosen. It was picked precisely *because* it was an existing
constant rather than one invented to be clearable — and it turns out that an existing constant can
be the wrong *kind* of quantity. **Throughput is dollars, not percentages.**

**The hurdle is not being changed after seeing the result.** The registered verdict is reported as
it came out, the defect is recorded in `CORRECTIONS.md` Pass 27.1, and the finding is stated in the
units the question was asked in:

> The entire reachable cross-venue opportunity set deploys **$24.40** and yields at most
> **$10.47/yr** under assumptions that cannot be met.

That statement needs no hurdle to interpret. The registration already said passing the objective
floor is **necessary, never sufficient**, and left the operator's own hurdle — *what the same effort
earns elsewhere* — deliberately unset. Any operator hurdle above ten dollars a year fails.

## What this establishes

**Capacity is the binding constraint, and it is external.** Not by the floor test, which passed, but
by magnitude: the ceiling sits three to four orders of magnitude below any goal that would motivate
building a trading bot. It cannot be elevated by finding a better edge, because the edge is not what
caps it — the opportunity set does. One in-band opportunity, $24.40 deep, is what the venue offers.

This is a statement about **retail-accessible prediction markets at reachable depth**, not about
market efficiency, and not a statistical result (AXIOMS A1). It does not say no edge exists. It says
that if one does, there is nowhere here to put meaningful money.

## The correction this run forced

`GATED-RESULTS.md` claimed *"Two pairs of 81 have a gap exceeding their own round trip."* That was
**inferred from the printed top-10 table, not measured.** Counted directly here: **4 clear, of which
3 are longshots and 1 is in band.** The inference was wrong in both directions. Recorded in
`CORRECTIONS.md` Pass 27.2 and corrected at the source.

## Limitations

- **One snapshot.** Books move; this run priced 82 pairs where `gated.py` priced 81 minutes earlier.
- **Recurrence is inverted, not measured.** A required rate that looks plausible is not evidence the
  rate obtains. No price history has been fetched.
- **Level-0 screen** (D3). It may kill a candidate; it may not certify one.
- **Impact is unmodelled.** The ceiling assumes profit does not decline with deployed size, which is
  false (Landier et al.; Chan 2022; Hey et al. 2023) and matters more, not less, at larger size.
- **Class B is recorded, not re-measured.** Its row comes from `SCANB-RESULTS.md`.
- **One venue pair, one size, one moment.** A different size or venue could differ (A1).
- **Venue eligibility remains an operator precondition** this repo neither assumes nor asserts.
