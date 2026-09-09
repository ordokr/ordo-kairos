"""Gate C measurement: the executable cross-venue deviation, Polymarket vs Kalshi.

    python scanc.py [--pages N] [--kalshi-pages N] [--sizes 5,10,25,50]

Registered in ``docs/PROTOCOL.md`` Gate C **before any paired data was fetched**, and licensed by
``gatec.py``, which established that the matcher refuses all seven registered near-misses while
still pairing the same event across two venues' phrasings.

**This produces a measurement, never a trade** (AXIOMS A5, D1, F3). What it reports is:

1. a **refusal funnel** — of all same-date candidate pairs, which piece of identity evidence blocked
   them, and how often that piece was *unavailable* rather than *contradictory*. Gate C could not
   distinguish those two, and said so; this is where the distinction is measured;
2. for verified pairs only, the **executable deviation** at size off both real books, net of both
   venues' round-trip costs, over the registered size curve;
3. the verdict under the registered decision rule, including its **terminal** branch.

**The kill rule is real and is why the fee schedule matters.** "Does not clear costs" ends the
programme. An overstated fee would therefore kill a real edge. Kalshi's schedule is **unverified**
(`kairos.kalshi.KALSHI_FEES`), so this runner reports the fee coefficient at which the verdict would
flip rather than announcing a terminal verdict on an unaudited number (G3).
"""

from __future__ import annotations

import argparse
import collections
import statistics
import time
import urllib.error
from dataclasses import replace
from pathlib import Path

from kairos.book import fetch_book_result
from kairos.costs import CONSERVATIVE
from kairos.crossvenue import (
    best_direction,
    date_blocks,
    days_until,
    edge_from_vwaps,
    kalshi_descriptor,
    polymarket_descriptor,
)
from kairos.identity import compare_identities
from kairos.kalshi import KALSHI_FEES, fetch_books, fetch_events
from kairos.legset import break_even_failure_rate, residual_failure_bound
from kairos.polymarket import _get_retry

GAMMA = "https://gamma-api.polymarket.com/markets"
PAGE = 100

#: Registered stopping rule: below this many verified pairs the verdict is WITHHELD as underpowered.
MIN_VERIFIED_PAIRS = 200

#: Registered size curve. 25 is the primary; the others exist because holding a design variable at
#: one value is an assumption, not a test (AXIOMS C11).
SIZES = (5.0, 10.0, 25.0, 50.0)



def ascii_safe(text: str) -> str:
    """Venue titles carry characters the Windows console codec cannot encode.

    A run that crashes *while printing* loses the verdict it already computed, which is what the
    first near-miss report did on a combining diaeresis. Reporting is not the place to fail.
    """
    return (text or "").encode("ascii", "replace").decode("ascii")


def polymarket_universe(pages: int) -> list[dict]:
    """Sweep the open universe from **both ends of the volume distribution**, deduped.

    Same shape as ``scanb.py`` and for the same measured reason: a null taken only from the
    high-volume head is weakest exactly where surviving mispricing is most expected.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for ascending in ("false", "true"):
        for i in range(pages):
            try:
                batch = _get_retry(f"{GAMMA}?closed=false&limit={PAGE}&offset={i * PAGE}"
                                   f"&order=volumeNum&ascending={ascending}")
            except urllib.error.HTTPError as e:
                if e.code != 422:  # 422 is the offset ceiling: the expected stop, not a fault
                    print(f"      page {i} ({ascending}): HTTP {e.code} - partial universe")
                break
            except (urllib.error.URLError, TimeoutError, OSError):
                print(f"      page {i} ({ascending}): network - partial universe")
                break
            if not isinstance(batch, list) or not batch:
                break
            for m in batch:
                mid = str(m.get("id") or "")
                if mid and mid not in seen:
                    seen.add(mid)
                    out.append(m)
            time.sleep(0.12)
    return out



def run_alignment(polys, kalshis) -> int:
    """Measure on the adjudicated table rather than the mechanical matcher.

    **The recall floor is checked first and it is not decorative.** Gate C3 registers
    ``RECALL_FLOOR = POWER_FLOOR = 0.50`` and disqualifies the mechanical matcher as a pair source
    below it. That check is reported here even though the pairs no longer come from the matcher,
    because the reason the table exists is that the matcher failed it.
    """
    import json
    from kairos.nullworld import POWER_FLOOR

    table = json.loads((Path(__file__).resolve().parent / "docs" / "ALIGNMENT.json")
                       .read_text(encoding="utf-8"))
    pairs = [t for t in table["pairs"] if t["label"] != "DISTINCT"]
    recall = (sum(1 for t in pairs if t["matcher_paired"]) / len(pairs)) if pairs else 0.0

    print(f"\n{'=' * 92}")
    print("RECALL FLOOR - registered in Gate C3 before the table was built")
    print("=" * 92)
    print(f"  adjudicated: {len(table['pairs'])} candidates -> {len(pairs)} aligned, "
          f"{len(table['pairs']) - len(pairs)} DISTINCT, {table['identical_count']} IDENTICAL")
    print(f"  mechanical matcher recall {recall:.3f} against floor {POWER_FLOOR}  "
          f"{'PASS' if recall >= POWER_FLOOR else 'FAIL'}")
    if recall < POWER_FLOOR:
        print("  -> the mechanical matcher is DISQUALIFIED as a pair source. Its verified count")
        print("     measures the matcher, not the venues (G12). Pairs are taken from the table.")
    print(f"\n{table['identical_note']}")

    by_pm = {d.market_id: d for d in polys}
    by_kx = {d.market_id: d for d in kalshis}
    by_size: dict[float, list[float]] = {s: [] for s in SIZES}
    zero_fee: dict[float, list[float]] = {s: [] for s in SIZES}
    basis: collections.Counter[str] = collections.Counter()
    census: collections.Counter[str] = collections.Counter()
    rows: list[tuple[str, float, float]] = []
    free = replace(CONSERVATIVE, taker_fee_coeff=0.0)

    print(f"\n[pricing] {len(pairs)} aligned pairs off both real books...", flush=True)
    for t in pairs:
        for kind in t["mechanical_refusals"]:
            basis[kind] += 1
        p, k = by_pm.get(t["pm_id"]), by_kx.get(t["kx_ticker"])
        if p is None or k is None:
            census["gone_since_adjudication"] += 1
            continue
        p_yes, why = fetch_book_result(p.yes_handle)
        p_no, why2 = fetch_book_result(p.no_handle)
        k_yes, k_no, why3 = fetch_books(k.market_id)
        if p_yes is None or p_no is None or k_yes is None or k_no is None:
            census[f"unfetchable:{why or why2 or why3}"] += 1
            continue
        days = max(days_until(p.settle_iso) or 0.0, days_until(k.settle_iso) or 0.0)
        priced = False
        for size in SIZES:
            dev, reason = best_direction(p_yes, p_no, k_yes, k_no,
                                         size=size, days=days, costs=CONSERVATIVE)
            if dev is None:
                census[f"size{size:.0f}:{reason.split(':')[-1]}"] += 1
                continue
            by_size[size].append(dev.edge)
            zero_fee[size].append(edge_from_vwaps(dev.yes_vwap, dev.no_vwap, days, free))
            if size == 25.0:
                rows.append((ascii_safe(t["pm_title"])[:52], dev.edge, days))
            priced = True
        census["priced" if priced else "unpriced"] += 1

    for key, count in census.most_common():
        print(f"      {key:<38} {count}")

    print(f"\nBASIS-RISK INVENTORY across aligned pairs (ways the two legs can come apart)")
    for kind, count in basis.most_common():
        print(f"      {kind:<34} {count}/{len(pairs)}")
    print("      NOTHING here is riskless. Every aligned pair carries at least one of these.")

    print(f"\n{'=' * 92}\nRESULT\n{'=' * 92}")
    if by_size[25.0]:
        print(f"  {'size':>6} {'pairs':>7} {'median edge':>14} {'best':>12} {'clearing costs':>16}")
        for size in SIZES:
            edges = by_size[size]
            if edges:
                print(f"  {size:>6.0f} {len(edges):>7} {statistics.median(edges):>+14.5f} "
                      f"{max(edges):>+12.5f} {sum(e > 0 for e in edges):>16}")
        for label, edge, days in sorted(rows, key=lambda r: -r[1])[:8]:
            print(f"    {edge:+.5f}  {days:6.1f}d  {label}")

    if zero_fee[25.0]:
        zf = statistics.median(zero_fee[25.0])
        med = statistics.median(by_size[25.0])
        print()
        print(f"  FEE SENSITIVITY: median {med:+.5f} charged, {zf:+.5f} at ZERO fees.")
        print(f"  The fee assumption moves the median by {zf - med:+.5f} - and NEITHER venue's")
        print("  schedule has been verified against published terms (Kalshi 429'd; Polymarket's")
        print("  CLOB fee is assumed at the same conservative quadratic and is very likely lower).")
        if zf > 0.0 >= med:
            print("  *** The sign TURNS ON an unverified input. No terminal verdict may rest on")
            print("      this until both schedules are checked (G3). ***")
        else:
            print("  The sign does not turn on it: the deviation fails to clear costs even with")
            print("  fees set to zero, so fee verification cannot rescue it.")

    n = len(pairs)
    med = statistics.median(by_size[25.0]) if by_size[25.0] else None
    print()
    if n < MIN_VERIFIED_PAIRS:
        print(f"  VERDICT: WITHHELD - {n} aligned pairs against a registered floor of "
              f"{MIN_VERIFIED_PAIRS}.")
        print("  The numbers above are DESCRIPTIVE and underpowered (A1).")
    elif med is not None and med > 0.0:
        print(f"  Median executable deviation {med:+.5f} at 25 contracts CLEARS both venues'")
        print("  combined round-trip costs on a powered sample. A candidate class exists.")
        print("  NOT YET a candidate: the divergence bound below still gates candidacy.")
    else:
        print(f"  VERDICT: median {med:+.5f} does NOT clear combined round-trip costs on "
              f"{n} pairs.")
        print("  The registered TERMINAL branch applies: Class B is concluded and the programme")
        print("  ends - subject to the fee sensitivity printed above.")
    print(f"{chr(10)}  The mechanical matcher found 0 of these {n}; adjudication found them in the")
    print("  same mechanically-surfaced pool. Two guards then demoted pairs the group labels got")
    print("  wrong - subject containment and outcome match - because a group label asserts only")
    print("  that a Kalshi event matches SOME Polymarket series.")
    print(f"{chr(10)}  Divergence bound: {residual_failure_bound(trials=0):.3f} (UNMEASURED). Gate C3")
    print("  requires it below `break_even_failure_rate` at the measured edge before any aligned")
    print("  pair may be called a candidate, so none is.")
    print("=" * 92)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=22, help="Polymarket pages per sort direction")
    ap.add_argument("--kalshi-pages", type=int, default=25)
    ap.add_argument("--max-priced", type=int, default=250, help="verified pairs to price")
    ap.add_argument("--alignment", action="store_true",
                    help="take pairs from the adjudicated table (PROTOCOL Gate C3) instead of the "
                         "mechanical matcher, whose recall was measured at 0.000")
    args = ap.parse_args()

    print("=" * 92)
    print("GATE C MEASUREMENT - EXECUTABLE CROSS-VENUE DEVIATION (POLYMARKET vs KALSHI)")
    print("=" * 92)
    print(f"  sizes {'/'.join(f'{s:.0f}' for s in SIZES)} contracts a side | verified-pair floor "
          f"{MIN_VERIFIED_PAIRS} | MEASUREMENT ONLY, nothing is traded")
    print(f"  Kalshi fee schedule: {'VERIFIED' if KALSHI_FEES.verified else 'UNVERIFIED'} "
          f"(coeff {KALSHI_FEES.taker_coeff}) - {KALSHI_FEES.note}")

    print("\n[1/4] Pulling both venues...", flush=True)
    polys = [d for d in (polymarket_descriptor(m) for m in polymarket_universe(args.pages)) if d]
    events = fetch_events(args.kalshi_pages)
    kalshis = [d for d in (kalshi_descriptor(e, m) for e in events for m in (e.get("markets") or []))
               if d]
    print(f"      polymarket: {len(polys)} descriptors | kalshi: {len(events)} events, "
          f"{len(kalshis)} descriptors")

    # ---- what each venue actually publishes ----
    print("\n[2/4] Evidence availability (what a venue publishes, not what the matcher decided)")
    for name, items in (("polymarket", polys), ("kalshi", kalshis)):
        prov: collections.Counter[str] = collections.Counter()
        for d in items:
            for field, how in d.provenance:
                prov[f"{field}:{how}"] += 1
        total = max(len(items), 1)
        line = "  ".join(f"{k}={v * 100 // total}%" for k, v in sorted(prov.items())
                         if k.endswith("missing"))
        print(f"      {name:<11} unavailable: {line or 'none'}")

    if args.alignment:
        return run_alignment(polys, kalshis)

    # ---- the funnel ----
    print("\n[3/4] Pairing on the six registered pieces of evidence...", flush=True)
    blocks = date_blocks(polys, kalshis)
    no_instant = sum(1 for d in polys + kalshis if not d.identity.instant)
    shared_days = [d for d, (p, k) in blocks.items() if p and k]
    refusal: collections.Counter[str] = collections.Counter()
    sole_blocker: collections.Counter[str] = collections.Counter()
    #: Blockers among pairs that agreed on SCOPE. Those are the genuinely dual-listed events, and
    #: what stops *them* is the only question the funnel is really asking.
    scope_agreed: collections.Counter[str] = collections.Counter()
    scope_agreed_pairs = 0
    candidates = 0
    verified: list[tuple] = []
    #: Pairs whose **only** blockers are evidence a venue does not publish. They are not verified
    #: and are deliberately NOT priced: pricing them would put a number on the table before the
    #: instrument that produces it has passed a gate, which is how Look 1 spent its alpha. Counting
    #: them is what says whether building that instrument is worth doing.
    provisional: list[tuple] = []
    #: The pairs that came closest. When nothing verifies, this is the only part of the run that
    #: says whether the venues lack dual-listed events or the matcher lacks recall on real phrasing
    #: — and Gate C named that exact ambiguity as the thing it could not resolve.
    near: list[tuple[int, str, str, tuple[str, ...]]] = []
    for day in shared_days:
        left, right = blocks[day]
        for p in left:
            for k in right:
                candidates += 1
                verdict = compare_identities(p.identity, k.identity,
                                             left_id=p.market_id, right_id=k.market_id)
                if verdict.paired:
                    verified.append((p, k))
                    continue
                kinds = {r.split(":")[-1] if r.startswith("unrecoverable") else r
                         for r in verdict.refusals}
                for kind in kinds:
                    refusal[kind] += 1
                if len(kinds) == 1:
                    sole_blocker[next(iter(kinds))] += 1
                if "scope_differs" not in kinds:
                    scope_agreed_pairs += 1
                    for kind in kinds:
                        scope_agreed[kind] += 1
                if all(r.startswith("unrecoverable") for r in verdict.refusals):
                    provisional.append((p, k, tuple(sorted(kinds))))
                # Ranked by **scope agreement first**, not by blocker count. Counting blockers
                # rewards pairs that dodge checks for free: two markets with no threshold on either
                # side cannot be blocked by `threshold_differs`, so the first version of this list
                # filled up with "Will Jesus Christ return before 2027?" against every undated
                # Kalshi market sharing its settlement instant. Scope agreement is the question the
                # list exists to answer.
                rank = (1 if "scope_differs" in kinds else 0, len(kinds))
                if len(near) < 12 or rank < near[-1][0]:
                    near.append((rank, p.label, k.label, tuple(sorted(kinds))))
                    near.sort(key=lambda r: r[0])
                    del near[12:]

    print(f"      descriptors with no recoverable settlement instant : {no_instant}")
    print(f"      resolution dates listed on both venues             : {len(shared_days)}")
    print(f"      same-date candidate pairs examined                 : {candidates}")
    print(f"      VERIFIED as the same event                         : {len(verified)}")
    print(f"      agreeing on everything either venue PUBLISHES       : {len(provisional)}")
    if candidates:
        print(f"\n      {'blocking evidence':<28} {'pairs blocked':>14} {'SOLE blocker':>14}")
        print("      " + "-" * 58)
        for kind, count in refusal.most_common():
            print(f"      {kind:<28} {count:>14} {sole_blocker.get(kind, 0):>14}")
        print("\n      'sole blocker' is the informative column: it counts pairs that agreed on")
        print("      everything else. A check that is never a sole blocker is never the binding")
        print("      constraint, and a large sole-blocker count names the evidence the two venues")
        print("      do not share.")
    if provisional:
        print(f"\n      PROVISIONAL PAIRS ({len(provisional)}) - agree on every piece of evidence")
        print("      both venues publish, blocked only by evidence one of them does not. These are")
        print("      NOT candidates and are deliberately left unpriced: putting a deviation on the")
        print("      table before the instrument that recovers the missing evidence has passed a")
        print("      null gate is measuring with an uncalibrated instrument (A7), and knowing the")
        print("      answer first is what cost Look 1 its alpha.")
        for p, k, kinds in provisional[:10]:
            print(f"        {ascii_safe(p.label)[:42]:<42} | {ascii_safe(k.label)[:42]}")
            print(f"            missing: {', '.join(kinds)}")

    if near and not verified:
        print(f"\n      CLOSEST PAIRS ({len(near)} shown). With nothing verified this is the only")
        print("      evidence on whether the venues lack dual-listed events or the matcher lacks")
        print("      recall on real phrasing - the ambiguity Gate C said it could not resolve.")
        for rank, left, right, kinds in near:
            tag = "scope AGREED" if "scope_differs" not in kinds else f"{rank[1]} blockers"
            print(f"        [{tag}] {ascii_safe(left)[:42]:<42} | {ascii_safe(right)[:42]}")
            print(f"            blocked by: {', '.join(kinds)}")

    # ---- price the verified pairs ----
    print(f"\n[4/4] Pricing {min(len(verified), args.max_priced)} verified pairs off both real "
          f"books...", flush=True)
    by_size: dict[float, list[float]] = {s: [] for s in SIZES}
    zero_fee: dict[float, list[float]] = {s: [] for s in SIZES}
    book_census: collections.Counter[str] = collections.Counter()
    free = replace(CONSERVATIVE, taker_fee_coeff=0.0)
    rows: list[tuple[str, str, float, float]] = []

    for p, k in verified[: args.max_priced]:
        p_yes, reason = fetch_book_result(p.yes_handle)
        if p_yes is None:
            book_census[f"polymarket_yes:{reason}"] += 1
            continue
        p_no, reason = fetch_book_result(p.no_handle)
        if p_no is None:
            book_census[f"polymarket_no:{reason}"] += 1
            continue
        k_yes, k_no, reason = fetch_books(k.market_id)
        if k_yes is None or k_no is None:
            book_census[f"kalshi:{reason}"] += 1
            continue
        days = max(days_until(p.settle_iso) or 0.0, days_until(k.settle_iso) or 0.0)
        priced_any = False
        for size in SIZES:
            dev, why = best_direction(p_yes, p_no, k_yes, k_no,
                                      size=size, days=days, costs=CONSERVATIVE)
            if dev is None:
                book_census[f"size{size:.0f}:{why.split(':')[-1]}"] += 1
                continue
            by_size[size].append(dev.edge)
            zero_fee[size].append(edge_from_vwaps(dev.yes_vwap, dev.no_vwap, days, free))
            if size == 25.0:
                rows.append((p.label, k.label, dev.edge, days))
            priced_any = True
        if priced_any:
            book_census["priced"] += 1
        time.sleep(0.05)

    for key, count in book_census.most_common():
        print(f"      {key:<40} {count}")

    # ---- verdict, under the rule written before the numbers ----
    print(f"\n{'=' * 92}\nRESULT\n{'=' * 92}")
    primary = by_size[25.0]
    if primary:
        print(f"  {'size':>6} {'pairs':>7} {'median edge':>14} {'best':>12} {'clearing costs':>16}")
        for size in SIZES:
            edges = by_size[size]
            if not edges:
                print(f"  {size:>6.0f} {0:>7}  (nothing filled at this size)")
                continue
            print(f"  {size:>6.0f} {len(edges):>7} {statistics.median(edges):>+14.5f} "
                  f"{max(edges):>+12.5f} {sum(e > 0 for e in edges):>16}")
        for left, right, edge, days in sorted(rows, key=lambda r: -r[2])[:10]:
            print(f"    {edge:+.5f}  {days:6.1f}d  {ascii_safe(left)[:40]:<40} | "
                  f"{ascii_safe(right)[:40]}")

    print()
    median = statistics.median(primary) if primary else None
    if len(verified) < MIN_VERIFIED_PAIRS:
        print("  VERDICT: WITHHELD - underpowered.")
        print(f"  {len(verified)} verified pairs against a registered floor of "
              f"{MIN_VERIFIED_PAIRS}. This is 'not enough evidence', NEVER 'no effect' (A1), and")
        print("  the kill rule does NOT fire on it.")
        if all("settlement_time" in d.identity.missing for d in polys) and polys:
            print("\n  AND THE ZERO IS STRUCTURAL, NOT EMPIRICAL: no Polymarket market has a")
            print("  recoverable determination instant, so under the evidence rule no pair CAN")
            print("  verify. Reading it as a fact about the venues would take an apparatus limit")
            print("  for a finding (G12).")
        print(f"\n  The question the funnel actually asks: {scope_agreed_pairs} pair(s) agreed on")
        print("  SCOPE - those are the genuinely dual-listed events, the ones a human would call")
        print("  the same market. What stopped them:")
        for kind, count in scope_agreed.most_common():
            print(f"      {kind:<34} {count}")
        if scope_agreed.get("settlement_time_differs"):
            print("\n  `settlement_time_differs` on a scope-agreeing pair is NOT an apparatus")
            print("  artefact. It means two markets a human would call identical settle at")
            print("  different instants - and in the window between them one venue pays YES while")
            print("  the other pays NO, so a position held as a hedge is not hedged. That is")
            print("  semantic non-fungibility, measured on live markets rather than assumed.")
        print("\n  So the honest next move is the one the registration prescribed: a different")
        print("  venue PAIR. Not because the instrument is weak - it was built and it worked -")
        print("  but because this pair appears to list very few mutually fungible events, and a")
        print("  floor of 200 verified pairs is not reachable by improving extraction alone.")
        print("  Loosening any check instead is NOT available: Gate C proved each one necessary")
        print("  by showing exactly one null world starts pairing when it is removed (A8).")
    elif median is not None and median > 0.0:
        stake = 1.0 - median
        bound = residual_failure_bound(trials=0)  # no resolved dual-listed pairs measured yet
        need = break_even_failure_rate(median, max(stake, 1e-6))
        print(f"  Median executable deviation {median:+.5f} at 25 contracts CLEARS both venues'")
        print("  combined round-trip costs. Under the registered rule a candidate class exists.")
        print(f"\n  But NOT YET a candidate. The resolution-divergence bound is UNMEASURED "
              f"({bound:.3f})")
        print(f"  against a break-even failure rate of {need:.3f}. Two markets verified as the same")
        print("  event can still RESOLVE differently, and that case loses both legs rather than")
        print("  one. The registration requires the bound measured on resolved dual-listed pairs")
        print("  before any pair is promoted. Until then no candidate may be declared (A6).")
    else:
        print("  Median executable deviation does NOT clear combined round-trip costs.")
        zf = statistics.median(zero_fee[25.0]) if zero_fee[25.0] else None
        if zf is not None and zf <= 0.0:
            print(f"  It does not clear them at ZERO fees either ({zf:+.5f}), so the unverified")
            print("  Kalshi schedule cannot be what killed it. The registered TERMINAL branch")
            print("  applies: Class B is concluded and the programme ends.")
        else:
            print(f"  At zero fees the median would be {zf:+.5f}. The verdict therefore TURNS ON an")
            print("  unverified fee schedule, and the terminal branch is WITHHELD until Kalshi's")
            print("  published terms are checked. Ending a programme on an unaudited input is the")
            print("  one thing the kill rule must not do (G3).")

    print("\n  Not covered here, named rather than implied: quote persistence, settlement-timing")
    print("  risk between two venues that do not resolve simultaneously, and venue eligibility -")
    print("  an operator precondition this repo neither assumes nor asserts. F3 stands.")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
