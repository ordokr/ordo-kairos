# Gate M — What a maker keeps — Results

**Verdict: NOT REFUTED, and the number that matters is not the verdict. A maker retains 3.9% of the
quoted half-spread; informed flow takes the other 96.1%.** Run 2026-09-14. Reproduce with
`python gatem.py --nulls` then `python scanm.py --markets 250`.

Nothing here trades or quotes (F3).

---

## The null gate — PASSED

`python gatem.py --nulls`, 20 replications × 276,000 samples, decision horizon 60 minutes. Verdicts
are block-bootstrap intervals with three states; a point estimate failed this gate on its first run.

| world | true `R` | measured | profit | loss | none | verdict |
|---|---|---|---|---|---|---|
| informed_strong (impact 2× spread) | −0.010 | −0.00280 | 0% | 100% | 0% | PASS |
| informed_breakeven (impact = spread) | 0.000 | −0.00003 | 0% | 0% | **100%** | PASS |
| toxic_minority (10% at 15×) | −0.005 | −0.00403 | 0% | 100% | 0% | PASS |
| pure_bounce | +0.010 | +0.01000 | 100% | 0% | 0% | PASS |
| walk_plus_bounce | +0.005 | +0.00500 | 100% | 0% | 0% | PASS |
| **STALE informed (95.7% no-trade)** | −0.010 | −0.00281 | 0% | 100% | 0% | PASS |
| **STALE bounce (95.7% no-trade)** | +0.010 | **+0.00928** | 100% | 0% | 0% | PASS |

The boundary world abstaining 100% of the time is the gate working: a world whose truth *is* the
decision threshold should return no verdict, not a coin flip.

## The measurement

| | |
|---|---|
| Eligible markets (in band, tick room > 1) | 898 |
| **Markets with usable history** | **237** |
| **Pooled observations** | **276,421** |
| Median quoted half-spread | **+0.01000** |

### Term structure

| horizon | `R(k)` | interval | observations |
|---|---|---|---|
| 1 min | +0.00016 | [+0.00014, +0.00019] | 290,404 |
| 5 min | +0.00025 | [+0.00021, +0.00028] | 289,456 |
| 15 min | +0.00029 | [+0.00023, +0.00036] | 287,086 |
| **60 min** | **+0.00039** | **[+0.00023, +0.00056]** | 276,421 |

`R` **rises** with the horizon rather than decaying, which is not the classic informed-flow
signature. The price tends to come back toward the maker over the hour. That is favourable and it is
reported because it was measured, not because it was expected.

## The finding: 96% of the spread does not survive the flow

The verdict is NOT REFUTED because the interval sits strictly above zero. **The economics are in the
magnitude, not the sign.**

| | per contract | share of the half-spread |
|---|---|---|
| Quoted half-spread | +0.01000 | 100% |
| **What a maker keeps, `R(60)`** | **+0.00039** | **3.9%** |
| Implied adverse selection | +0.00960 | 96.1% |

**The calibration is what makes this interpretable.** The same estimator, on a synthetic world with
the same 95.7% staleness and the same 0.010 half-spread but *uninformed* flow, returns **+0.00928** —
93% retention. So the instrument can see the spread when it survives. On real Polymarket flow it sees
3.9% of it.

### What that does to Gate M.0's ceiling

Gate M.0 reported a gross ceiling of **$29,280,877/yr** on the $532M of annual flow in markets with
tick room, computed at the full quoted spread. Retaining 3.9% of it:

| | |
|---|---|
| Gross ceiling at 100% of with-room flow | $29,280,877/yr |
| **Net of measured adverse selection** | **~$1,142,000/yr** |
| At a 1% share of that flow | ~$11,400/yr |
| At a 0.1% share | ~$1,140/yr |

100% capture is impossible; an entrant competes for queue position against incumbents who already
hold **77.4%** of the flow at one tick. **These figures are before queue position, inventory risk,
infrastructure and the operator's own time**, none of which is measured and all of which cut against.

This is a cross-measurement combination — M.0's flow across all in-band markets, M's retention on the
tick-room subset — and is an indication of scale rather than a measured quantity.

## Two defects this run found, both in what surrounds the measurement

**The null worlds traded every step; the real data is 95.7% stale.** Measured before the verdict was
trusted: 95.7% of minute-to-minute prices are unchanged and 59.6% of contributions are exactly zero.
The estimator had been validated on a process the data does not resemble — the **G14 failure Gate C
already committed**, where a matcher scored power 1.000 on its own parser's dialect and 0/26 on real
text. Fixed by adding the two STALE worlds above; the estimator survived, so the verdict stands. It
did not have to.

**The power precondition compared incommensurable counts.** The registered threshold — 100,000
observations — was calibrated on synthetic *trade sequences*. It was applied to *minute samples*, of
which ~96% carry no trade. Re-calibrated in the real regime (276,000 stale samples, 10/10 detection
both ways), which is what licenses the verdict.

Recorded in `CORRECTIONS.md` Pass 29.

## Limitations

- **The tick test attenuates toward zero**, and zero is the direction that flatters the maker:
  measured, a true `R` of −0.010 reads as −0.0028. A NOT REFUTED verdict is therefore the *less*
  trustworthy outcome here, and the true retention may be below 3.9%.
- **Queue position is not measured at all.** This measures the cost of fills a maker gets, never the
  probability of getting them. It is the whole of Gate 3 for this class.
- **Maker rewards are excluded**, and cut for. 1,318 of 1,436 in-band markets advertise them, and
  rewards farming is a different hypothesis with a different revenue source.
- **One day of history per market**, one snapshot of quoted spreads.
- **Traded prices stand in for midquotes**, which Polymarket does not publish historically.
- **Direction is inferred, not read.** On-chain `OrderFilled` is ground truth and is not used.
- **The exhibit did not fire.** With interval inference, a gate decided at `R(1)` would have called
  0 of 4 losing worlds profitable, so the registered case for the 60-minute horizon is weaker than
  the registration claimed.
