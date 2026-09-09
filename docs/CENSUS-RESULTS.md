# Feasibility Census — Results and Decision 001

**Run 2026-09-08.** Reproduce with `python census.py --pages 10 --probe 20`.
Method: `principles-20-solutions`, proportionality 4/4.

---

## Decision

**Run Gate 1 (the `q_ref` ablation) on Polymarket resolved markets — Class A first — and hold
Class B behind its own null gate.**

Both classes have raw material. Class A's is confirmed abundant and its statistical machinery
already passed Gate 0. Class B's material exists but its **false-positive mode is unmeasured and
severe**, and building a scanner before its gate would repeat exactly the error Gate 0 was built to
prevent (AXIOMS A7).

**Constraint introduced:** no Class B scanner is written until a Class-B null gate exists, on the
same terms as Gate 0.

**Falsifier:** if a Gate-1 adapter cannot assemble ≥300 independent events each carrying ≥5 usable
decision-time price points, Class A is not measurable on this venue and the decision was wrong.

**Close second (now moot):** the Hindcast adapter (PROTOCOL step 2). Class A was rejected by Look 3 before this was needed, and Zhang et al. 2026 measured frontier models losing 16-31% of real capital on these venues — leakage-free evidence at a fraction of the cost. Originally deferred because its artifact
availability is unverified while the local data path is confirmed, and because it answers a
narrower question than the ablation does.

---

## What the census measured

### Class A — forecasting supply: **sufficient**

| Measure | Value |
|---|---|
| Markets sampled (most recently resolved) | 1,000 |
| Cleanly resolved binary | **1,000 (100%)** |
| With CLOB token ids | 1,000 |
| Independent events, negRisk groups collapsed | **877** |
| Gate-0 requirement | 300 |
| Price history retrievable | **20/20 (100%)** |
| Markets with ≥5 usable price points | **20/20 (100%)** |

877 independent events from a single 1,000-market page, against a requirement of 300. Supply is not
the constraint.

**The binding constraint is history density, not event count.** Point counts are strongly
parameter-sensitive — `fidelity=60` returned **1 point** where `fidelity=1440` returned **8** on the
same market — and many markets resolve within days of listing. One sampled market ran **7 days**
against a nominal 2029 end date. A Gate-1 adapter must measure per-market history and admit markets
on that basis, not on the nominal horizon.

### Class B — structural supply: **exists, but the naive reading is an artifact**

28 negRisk groups with ≥4 legs in a 1,000-market open sample. The decisive column is the last one:

| legs | sum(YES) | raw deviation | **carry-adjusted** | group |
|---|---|---|---|---|
| 52 | 0.9300 | −0.0700 | **+0.0450** | JD Vance, 2028 US Presidential |
| 51 | 0.9045 | −0.0955 | **+0.0195** | Newsom, 2028 Democratic primary |
| 42 | 0.8965 | −0.1035 | **+0.0115** | Trump, 2028 Republican primary |
| 41 | 0.9925 | −0.0075 | **+0.0294** | Le Pen, 2027 French presidential |
| 31 | 1.0355 | +0.0355 | **+0.0440** | Mbappé, 2026 Ballon d'Or |
| 20 | 0.3685 | −0.6315 | **−0.6264** | Trump Nobel Peace Prize |

**Adjusting for capital lock-up reverses the sign on every long-dated group.** The apparent 7–10%
"discount" on the 2028 groups is more than fully explained by the settlement wedge — after
adjustment they trade slightly *rich*, not cheap. This is the Gebele & Matthes (2026) result
reproduced on live data with our own `SettlementTerms` model.

The −0.63 residual on the Nobel group is **leg truncation**, not arbitrage: the page did not
contain the full candidate set.

**The number that matters:** residual carry-adjusted deviations sit at **1–4.5%**, consistent with
Gebele's published 2–4% cross-venue figure — and **at or below the ~5-point round-trip cost band**
that `kairos.costs` already computes for a 0.50 contract at 30 days. Class B is not obviously dead,
but it is not obviously alive either, and nothing about it can be settled without execution-aware
measurement.

---

## Three false-positive sources found in Class B, in one afternoon

1. **Pagination truncation.** The first hand-probe reported apparent **53% arbitrage** on a 2028
   election group. Entirely an artifact of seeing part of the leg set.
2. **Settlement carry.** The next probe reported a consistent 6–10% "edge" across long-dated
   groups. Entirely explained by capital lock-up, and over-explained — the sign flips.
3. **Exhaustiveness.** A negRisk group that is not mutually exclusive *and exhaustive* is supposed
   to sum below 1. Nothing in the API states which groups are exhaustive.

Three independent ways to manufacture a large fake edge, all found before writing a scanner. This
is the evidence for the constraint above: **Class B needs a null gate at least as much as Class A
did.**

---

## Bugs found in this census's own apparatus

Recorded because a measurement whose apparatus was not inspected is not a measurement
(AXIOMS A5, and the method's "a number in the brief is a measurement whose apparatus you have not
inspected").

| # | Bug | Effect | Fix |
|---|---|---|---|
| 1 | `resolution_of` demanded exact `0.0`/`1.0` | Reported **0% resolved** — resolved markets report `["0.00000101…", "0.99999898…"]` | Tolerance-based test; `["0","0"]` voids still correctly excluded |
| 2 | Carry horizon computed with `start=None` | Adjustment **silently never ran**; every row printed the raw deviation | Compute days from *now* to resolution |
| 3 | "Market lifetime" used nominal `endDate` | Reported median **367 days** for markets whose real traded span is **7 days** | Relabelled NOMINAL; actual span measured from the history probe |
| 4 | CLOB history probed with default urllib agent | **403 Forbidden** — nearly recorded as "history unavailable", which would have killed Class A on a false blocker | User-Agent header; verified against `curl`, which had reached the host |

Bug 4 is the instructive one: a single probe method produced a decisive-looking negative result that
was wrong. The rule it confirms is AXIOMS A6 — *"we did not measure it" is not evidence*, and its
converse: one failed measurement is not evidence either.

---

## What this does **not** establish

No edge, in either class. The census measures whether the raw material exists to *run* PROTOCOL
Gates 1–2. It does not run them. Class A's supply is confirmed; its edge is entirely unknown.
Class B's material is confirmed and its measurement problem is now partly characterised — which is
strictly worse news than it looked before the carry adjustment was applied.

**Next (done 2026-09-08):** PROTOCOL Gate 1 — the four-way `q_ref` ablation (raw / settlement-only / recalibration-only
/ both) on rolling temporal splits, with a sealed final holdout, using markets admitted on measured
history density rather than nominal horizon.
