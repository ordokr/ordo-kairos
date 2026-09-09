# Look 2 — Results

**Verdict: WITHHELD. 115 fresh events against a registered requirement of 700.** Run 2026-09-08.
Reproduce with `ORDO_KAIROS_STATE=<durable> python replicate.py --pages 60`.

Under AXIOM A1 this is *"not enough evidence"*, never *"no effect"*. The two hypotheses were
measured and are recorded below, but they carry no inferential weight and must not be quoted as
though they did.

---

## The design worked

The whole replication rests on testing events look #1 never saw. That guarantee was enforced, not
assumed:

- Look #1's event set was rebuilt from its own arguments and checked against the recorded count.
  **731 events reproduced exactly.** Had it come back 730 or 733 the run would have voided itself
  rather than proceed on a partially-overlapping sample.
- Uncapped, the reachable universe gave **1,122 observations in 846 events**. Removing look #1's 731
  leaves **115 fresh events**.

The sealed holdout was **not** queried. Neither hypothesis cleared development, and spending the one
permitted query on a hypothesis that had already failed would burn it for nothing (C6). It remains
sealed.

## What was measured — non-inferential

| hypothesis | log score | vs market | p | look #1 |
|---|---|---|---|---|
| market | 0.39983 | — | — | benchmark |
| `C_logit` | 0.37515 | +0.02468 | 0.3928 | +0.01341 |
| `drift` | 0.34644 | +0.05338 | 0.0915 | +0.01193 |

Both point estimates are **larger** than look #1's and neither is significant at the registered
`alpha = 0.025`. That combination is exactly what 115 events buys: an estimate too noisy to be worth
anything, and the larger of two, so it carries the same selection inflation already registered
against look #1's `+0.012`. **These numbers are not encouraging and must not be described as such.**
They are excluded from Look 3 precisely because they have now been read.

Note also the benchmark moved: 0.39983 here against 0.336 in look #1. The fresh events are older
markets with a different price composition, so the two log scores are not directly comparable.

---

## Why it could not answer — a measured apparatus ceiling

`--pages 60` and `--pages 21` return **identical data**. Probed directly against the live API, with a
second method, after the run:

| probe | result |
|---|---|
| `offset` = 1900, 2000 | 100 markets each |
| `offset` ≥ 2100 — every ordering, with and without `order` | **HTTP 422** |
| `limit` = 500, `limit` = 1000 | silently capped at 100 |
| same query inside an `end_date_min`/`end_date_max` window | **its own 2100 budget** |
| two adjacent quarterly windows | **overlap = 0 markets** |
| quarterly sweep 2021–2026 | **26,143 resolved markets** |

So Gamma's ceiling is on **pagination**, not on the universe: offset paging can see 2,100 markets and
date-windowed paging reaches at least 26,143 — twelve times as many, with several quarters still
saturated at their own 2,100 cap.

**Look 2's registered sample size was never reachable by the method Look 2 registered.** That is an
apparatus defect, diagnosed and fixed before the target was touched. The target was not changed:
Look 3 runs the same two hypotheses at the same `alpha` with the same materiality floor.

### This is not optional stopping

The stopping rule exists to forbid collecting until a p-value cooperates. What happened is
different in kind: the retrieval mechanism could not deliver the pre-registered *n*. The distinction
is load-bearing and is preserved by two things —

1. Look 2's 115 events are **excluded** from Look 3. Their outcomes have been seen, so they are
   spent; reusing them would make Look 3 a second look on part of its own sample.
2. Look 3's stopping count (1,500 fresh events) is a **sample-size** target fixed in the
   registration before that data existed, taken from Gates 1 and 2a independently sizing the re-test
   at 1,400–1,900 events. It is not derived from anything Look 2 measured.

---

## Operational finding — the cache is volatile and that is a correctness problem

Mid-session the data cache went from **1,683 history files to 199**, with `markets/` deleted
outright. `%TEMP%` is swept on this machine — almost certainly the same thing that freed 216 GB
between sessions.

This is not merely a re-fetch cost. Because Gamma paginates by descending end date, **re-fetching
page *n* later returns a different set of markets** as new ones resolve. A swept cache does not
restore the old sample; it silently substitutes a new one, and every gate run against those pages
becomes unreproducible.

Mitigations, both landed:

- `ORDO_KAIROS_STATE` set to `C:/Users/Administrator/.cache/ordo-kairos` — outside `%TEMP%` and
  outside the publish-eligible repo tree.
- `cache_dir()` now warns once per process, on stderr, when it falls back to temp, and says why the
  fallback is dangerous rather than merely non-durable.

The look-#1 reconstruction check is what would have caught a silent substitution. It passed, so the
disjointness claim above holds — but it passed on a cache that had already been rebuilt once, which
is why the check exists rather than an assumption.
