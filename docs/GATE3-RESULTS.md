# Gate 3.0 (Class M) — Does the fill arrive? — Results

**Verdict: both variants clear the floor at every size measured. Class M survives.** Run 2026-09-14.
Reproduce with `python gate3.py --markets 250`.

**The verdict is size-dependent and the registration froze no size**, which is the C11 violation
recorded in `CORRECTIONS.md` Pass 30.2. The curve is the result; no point on it is the answer.

Nothing here trades or quotes (F3).

---

## Result

| | |
|---|---|
| Eligible markets (in band, tick room > 1) | 898 |
| **Books measured** | **248** |
| Median touch depth | **148 contracts** |
| Median one-sided daily flow | **5,420 contracts** |
| **Markets where the queue never clears in a day** | **6 / 248 (2.4%)** |

The queue turns over roughly **36 times a day**. The pre-committed expectation — that markets wide
enough to quote in are wide *because they are quiet*, so joining the queue would approach zero fills
— **was wrong.** These markets are wide and active.

## The size curve (C11)

| posted size | (a) join the back | (b) improve one tick | clears |
|---|---|---|---|
| 5 | $245.59 | $155.98 | both |
| **25** | **$1,227.95** | **$779.90** | both |
| 100 | $4,901.92 | $3,119.60 | both |
| 500 | $23,495.04 | $15,061.31 | both |
| 2,000 | $76,078.25 | $46,446.20 | both |

**(a) beats (b) at every size**, which also contradicts the registration's expectation. Paying two
ticks for priority is wasted when the queue turns over 36 times a day — you get filled either way,
so the cheaper quote wins. Improving the quote is what you do when the queue is *slow*, and it is
not.

## What the numbers rest on, and where they stop being trustworthy

Every figure above is `fills × RETENTION × half_spread`, where **RETENTION = 3.9%** comes from Gate M
— measured across 237 markets and 276,421 observations **on aggregate flow**.

**That assumption does not survive scale.** At a posted size of 500 against a median touch depth of
148, an entrant is three times the resting queue; at 2,000 they are thirteen times it. At that point
they are not taking a share of the flow, they **are** the book, and the flow that reaches them is not
the aggregate flow the retention was measured on — it is disproportionately the informed part.
**The large-size rows are the least trustworthy in the table and they are the only ones that produce
interesting money.**

As a rate the result is strong — roughly $3,100 of capital at size 25 returning ~$1,228/yr, about
40% — but Pass 27.1 is exactly why that framing is not the question. The magnitude at a size whose
retention assumption still holds is **about twelve hundred dollars a year**.

## Two defects this run found

**The registration wrote (a) with no size cap.** It specified expected fills as
`max(0, side_flow − touch_depth)`, which lets a single entrant absorb every contract of excess flow
at unlimited size. It made (a) beat (b) by $123,586 to $6,480 in the first run — structurally
impossible, since (a) is strictly behind (b) in the queue. Both variants are now capped at the size
actually posted, once a day, which is conservative and stated rather than tuned.

**The registration froze no posted size at all**, while C11 exists precisely to stop a design
variable being held at one value. With no registered size there is no registered verdict — only a
curve — and picking a point on it now would be choosing the answer after seeing it (A8).

## Limitations

- **Competitive requoting is unmodelled**, and cuts against both variants.
- **Adverse selection at the touch** is not measured; `RETENTION` is an aggregate-flow number.
- **Flow is a lifetime average** — `volumeNum / days_since_start` — not a current rate, and
  `volumeNum` units are assumed dollars and unverified.
- **One posting a day** is a conservative fill model, stated; real quoting requotes continuously.
- **Partial fills and cancellation** are unmodelled.
- **Maker rewards are excluded**, and cut for.
- **The pre-committed expectation was wrong in both directions** — the markets are active, not
  quiet, and (a) beats (b). Recorded because a registration whose predictions fail is more
  informative than one whose predictions are never checked.
