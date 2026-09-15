# Gate R — Subsidy capture — Results

**Verdict: NOT REFUTED on the registered rule, by $6,324/yr at one size — and the sign flips at
every larger size and under the other honest accounting of fills.** Run 2026-09-14. Reproduce with
`python gater.py --markets 120`.

**The verdict is not robust, and the registration is why.** See "Two defects" below and
`CORRECTIONS.md` Pass 31. Nothing here trades or quotes (F3).

---

## The universe

| | |
|---|---|
| Markets swept | 1,902 |
| Excluded as longshots | 1,126 |
| No tick room | 267 |
| Missing quote fields | 196 |
| **No reward pool** | **139** |
| **Incentivized and priced** | **120** |
| Pool published with a **zero max spread** (nothing can qualify) | present, counted separately |

| | |
|---|---|
| **Median daily pool** | **$5** |
| Largest observed pools | $302, $242, $109, $100/day |
| **Median competitor score** | **2,336** |

The pools are a long tail: a handful at $100–302/day and a median of five dollars. The books inside
`max_spread` are already densely quoted, so an entrant's share of any pool is small by construction.

## Net annual by quote distance, 100 contracts a side

| s / max_spread | reward/yr | fills/yr | **NET (registered)** | NET (consistent) |
|---|---|---|---|---|
| 0.1 | $38,517 | 7,180,435 | **−$30,415** | +$39,820 |
| 0.3 | $28,868 | 6,388,940 | **−$32,465** | +$32,339 |
| 0.5 | $20,087 | 5,887,567 | **−$36,434** | +$25,348 |
| 0.7 | $12,813 | 5,449,567 | **−$39,503** | +$19,571 |
| 0.9 | $8,054 | 4,891,702 | **−$38,906** | +$15,794 |
| 1.0 | **$0** | 4,782,202 | **−$45,909** | +$8,364 |

Reward falls monotonically in `s` exactly as `((v−s)/v)²` requires, and is **zero at the edge**.

## Size curve (C11)

| size | best s/v | NET (registered) |
|---|---|---|
| **20** | 0.0 | **+$6,324** |
| 100 | 0.0 | −$27,975 |
| 500 | 0.9 | −$244,209 |
| 2,000 | 1.0 | −$900,046 |

**Only the smallest size is positive.** Fills are capped at the posted size per side per day, so the
cost term scales linearly in size while the reward share scales sub-linearly —
`own / (own + competitors)` saturates. Subsidy capture is therefore a *small-size* strategy or none,
which is the opposite of how capacity constraints usually resolve.

## Two defects, and the verdict turns on the second

**The code diverged from the registration.** The frozen rule is
`pool × share(s) − fills(s) × 0.0096`. The first implementation added `+ fills × distance` — an
unregistered capture term — and reported a best net of **$3,257,641/yr at `s/v = 1.0`**, the one
distance where rewards are **zero by construction**. The absurdity is what exposed it: an optimum
sitting exactly where the thing being measured pays nothing means the number came from somewhere
else. It came from applying Gate M's constant at 4–6× the distance it was measured at.

**The registration itself double-counts adverse selection.** Gate M's `R(60)` is *already* net of
adverse selection — it is what a maker **keeps**. Charging `0.0096` per fill against a capture of
zero charges the same cost twice. The honest per-fill P&L is `RETENTION × s`, small and **positive**,
exactly as `gate3.py` uses it.

So there are two defensible accountings and **they disagree in sign at every size above 20**:

| reading | at 100 contracts, s = 0.1 |
|---|---|
| registered (fills as pure cost) | **−$30,415/yr** |
| consistent with Gate M and Gate 3.0 | **+$39,820/yr** |

The registered rule was run as the verdict because it is what was frozen, and the frozen rule is not
rewritten after seeing the result (A8). The consistent reading is reported beside it. **A verdict
whose sign depends on an accounting choice is not a finding**, and saying so is the result.

## What this establishes

At the honest end of the range — the Gate-M-consistent accounting, at a size where the assumption
holds — subsidy capture across **the entire incentivized universe** is worth **tens of thousands of
dollars a year**, before competitor response, on a snapshot of today's competition.

That is two to three orders of magnitude above every prior class (Class C: $10.47/yr; Class M
Gate 3.0: ~$1,200/yr) and it is still not a business that would justify the build. And the term that
would decide it — what happens to `own / (own + competitors)` when an entrant arrives — is precisely
the term this gate cannot measure.

## Limitations

- **Competitor response is unmodelled**, and is the binding uncertainty. Share normalises against
  every entrant; the measurement is a snapshot, not an equilibrium.
- **The fills model caps at posted size per side per day**, so the cost term is close to
  deterministic and the verdict is sensitive to that cap.
- **Adverse selection was measured at a ~1c half-spread** and these markets quote 4.5–6.5c max
  spreads. Applying it there is extrapolation and flatters wide quotes.
- **Maker rebates and holding rewards are excluded**, and both cut for. `holdingRewardsEnabled` is a
  third programme this repository has still never examined.
- **Epoch mechanics, the $1 minimum daily payout, and cancellation** are unmodelled.
- **One snapshot** of books and pools, both of which change continuously.
