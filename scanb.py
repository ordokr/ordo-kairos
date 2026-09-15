"""Class B candidate scan: live negRisk groups, verified leg sets, real book depth.

    python scanb.py [--groups N] [--size 25]

**This produces candidates, never confirmed arbitrage** (AXIOMS A5, D1). Nothing here trades, sizes
a position, or touches capital (F3). Its output is a shortlist and, more usefully, a **census of why
groups were refused** — which is the part that says whether Class B has raw material at all.

Everything it does was licensed by something measured first:

- **Gate B** (`gateb.py`) established that the pipeline finds nothing in six arbitrage-free worlds
  and detects an unambiguous edge every time, so a scanner is permitted at all.
- **`kairos.legset`** verifies the leg set against `/events/<id>` before any arithmetic. Real groups
  assembled through offset pagination are **49% truncated, missing 60% of their legs** — a scanner
  without this is wrong about half the time.
- **`kairos.book`** replaces Gate B's synthetic depth with the real ask book, and prices each leg at
  the **VWAP to fill the target size** rather than at the touch. An edge on six contracts is not an
  edge on twenty-five.
- **Exhaustiveness** is tested at the measured edge, because if no listed outcome wins the set pays
  $0 and the whole stake is lost. 512/512 resolved groups had exactly one winner, bounding that at
  0.59%, so the tradeable floor is ~1%.

Known weakness, stated rather than buried: ``days_to_settlement`` comes from the **nominal**
``endDate``, because an open market has no realised resolution date to measure. Markets routinely
resolve early, so the nominal date is usually *late*, which overstates carry and makes edges look
**worse** than they are. That is the safe direction, but it is an estimate and it is the reason a
long-dated candidate here deserves less trust than a short-dated one.
"""

from __future__ import annotations

import argparse
import collections
import json
import time
import urllib.error
import urllib.request

from kairos.book import cost_to_buy, fetch_book_result
from kairos.costs import CONSERVATIVE
from kairos.legset import (
    break_even_failure_rate,
    fetch_event,
    residual_failure_bound,
    verify_leg_set,
)
from kairos.polymarket import HEADERS, _get_retry

GAMMA = "https://gamma-api.polymarket.com/markets"
PAGE = 100

#: Contracts per leg the edge must survive. Gate B's MIN_FILL, now enforced against a real book.
TARGET_SIZE = 25.0

#: Groups below this many legs are not negRisk sets worth the name.
MIN_LEGS = 3


def days_until(iso: str | None) -> float | None:
    from datetime import datetime, timezone

    if not iso:
        return None
    try:
        end = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0.0, (end - datetime.now(timezone.utc)).total_seconds() / 86400.0)


def open_neg_risk_markets(pages: int) -> list[dict]:
    """Sweep the open universe from **both ends of the volume distribution**, deduped.

    The first scan pulled only ``volumeNum`` descending, which is the high-attention head — and
    Sethi & Kline and Abínzano et al. both locate surviving mispricing in *low*-attention contracts.
    A null measured only on the head is therefore weakest exactly where an edge is most expected, so
    the ordering is swept in both directions.

    ``offset`` caps at 2100 on open markets too (HTTP 422 beyond), so this is the whole universe
    offset pagination can reach, not a sample of it.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for ascending in ("false", "true"):
        for i in range(pages):
            try:
                batch = _get_retry(
                    f"{GAMMA}?closed=false&limit={PAGE}&offset={i * PAGE}"
                    f"&order=volumeNum&ascending={ascending}"
                )
            except urllib.error.HTTPError as e:
                if e.code == 422:  # past the offset ceiling: the expected stop, not a fault
                    break
                print(f"  page {i} ({ascending}): HTTP {e.code} - partial universe", flush=True)
                break
            except (urllib.error.URLError, TimeoutError, OSError):
                print(f"  page {i} ({ascending}): network - partial universe", flush=True)
                break
            if not isinstance(batch, list) or not batch:
                break
            for m in batch:
                mid = str(m.get("id") or "")
                if mid and mid not in seen and m.get("negRiskMarketID") and m.get("clobTokenIds"):
                    seen.add(mid)
                    out.append(m)
            time.sleep(0.12)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--groups", type=int, default=40, help="verified groups to price")
    ap.add_argument("--size", type=float, default=TARGET_SIZE)
    args = ap.parse_args()

    print("=" * 88)
    print("CLASS B - CANDIDATE SCAN (live negRisk groups, verified leg sets, real book depth)")
    print("=" * 88)
    print(f"  target size {args.size:.0f} contracts/leg | exhaustiveness bound "
          f"{residual_failure_bound():.4f} | CANDIDATES ONLY, nothing is traded")

    print("\n[1/3] Pulling open negRisk markets...", flush=True)
    markets = open_neg_risk_markets(args.pages)
    by_event: dict[str, list[dict]] = collections.defaultdict(list)
    for m in markets:
        for e in m.get("events") or []:
            if e.get("id"):
                by_event[str(e["id"])].append(m)
                break
    groups = [(eid, ms) for eid, ms in by_event.items() if len(ms) >= MIN_LEGS]
    print(f"      {len(markets)} open negRisk markets in {len(by_event)} events "
          f"({len(groups)} with >= {MIN_LEGS} legs)")

    # Discovery is paginated; **pricing is not**. The paginated pull cuts across group boundaries —
    # 37 of 40 groups came back truncated on the first run, leaving 3 priceable, which is too few to
    # say anything about the venue. `/events/<id>` returns the full leg set *with token ids*, so the
    # authority supplies the legs and pagination only supplies the event ids worth asking about.
    # Verification is still what makes this sound: it is the reason the authority can be used as the
    # leg set rather than merely compared against one.
    print(f"\n[2/3] Verifying leg sets against /events/<id>...", flush=True)
    census: collections.Counter[str] = collections.Counter()
    verified: list[tuple[str, list[dict], object]] = []
    for eid, ms in groups:
        held = [str(m["id"]) for m in ms]
        v = verify_leg_set(eid, held)
        if v.refusals and set(v.refusals) != {"legs_missing"}:
            for r in v.refusals:
                census[r] += 1
            time.sleep(0.05)
            continue
        # Re-verify against the authority's own list: complete by construction, and the remaining
        # checks (single group id, authority not missing anything) still have to pass.
        ev = fetch_event(eid)
        all_legs = [m for m in (ev or {}).get("markets") or [] if m.get("clobTokenIds")]
        open_legs = [m for m in all_legs if not m.get("closed")]
        # `active` is the only field that predicts whether a leg has a CLOB book. Measured across
        # 10 groups: every leg returning HTTP 404 from /book had active=False, while
        # enableOrderBook and acceptingOrders were *both True* on those same legs - so the two
        # obvious flags are misleading and only this one tracks reality.
        inactive = [m for m in open_legs if not m.get("active")]
        if inactive:
            # Not an apparatus failure: these legs cannot be bought, so the set cannot be
            # completed, so the buy-every-leg identity is unavailable at any price (AXIOMS D1).
            census["group_has_untradeable_legs"] += 1
            time.sleep(0.05)
            continue
        auth_markets = open_legs
        if len(all_legs) > len(auth_markets):
            # A partially-settled group is a different object: some outcomes are already decided, so
            # buying the remaining legs does not reconstruct a $1 payoff. Refused with its own name
            # rather than surfacing as "legs_missing", which would blame the authority for a
            # property of the group.
            census["group_partially_settled"] += 1
            time.sleep(0.05)
            continue
        if len(auth_markets) < MIN_LEGS:
            census["authority_has_too_few_open_legs"] += 1
            time.sleep(0.05)
            continue
        v2 = verify_leg_set(eid, [str(m["id"]) for m in auth_markets])
        if not v2.complete:
            for r in v2.refusals:
                census[f"authority:{r}"] += 1
            time.sleep(0.05)
            continue
        census["verified"] += 1
        if "legs_missing" in v.refusals:
            census["  (recovered from a truncated pull)"] += 1
        verified.append((eid, auth_markets, v2))
        time.sleep(0.05)
    for k, c in census.most_common():
        print(f"      {k:44s} {c}")
    if not verified:
        print("\n  No group survived leg-set verification. No candidates.")
        return 0

    print(f"\n[3/3] Pricing {min(len(verified), args.groups)} verified groups off the real "
          f"ask book...", flush=True)
    results = []
    thin_detail: list[tuple[str, int, float]] = []
    priced = 0
    for eid, ms, v in verified[: args.groups]:
        auth = v.authoritative
        # `ms` is now the authority's own open-leg list, so every leg has market data by
        # construction. Pricing a set assembled from anywhere else would reopen the truncation hole.
        full = {str(m["id"]): m for m in ms}
        legs = set(full)
        total = 0.0
        worst_fill = float("inf")
        outcome = None            # "thin" | "unfetchable" | "bad_token" - never merged (AXIOMS G5)
        days = max((days_until(full[i].get("endDate")) or 0.0) for i in legs)
        for i in legs:
            try:
                tok = json.loads(full[i]["clobTokenIds"])[0]
            except (KeyError, ValueError, TypeError, IndexError):
                outcome = "bad_token"
                break
            book, reason = fetch_book_result(tok)
            if book is None:
                # A failed fetch is not an empty book. Merging them would report a measurement
                # about the venue's depth that was really a measurement of the network.
                outcome = f"unfetchable:{reason}"
                break
            fill = cost_to_buy(book, args.size)
            worst_fill = min(worst_fill, fill.filled)
            if not fill.complete:
                outcome = "thin"
                break
            total += CONSERVATIVE.effective_yes_cost_at(fill.vwap, days)
            time.sleep(0.03)
        if outcome == "thin":
            census["book_too_thin_at_size"] += 1
            thin_detail.append((eid, len(legs), worst_fill))
            continue
        if outcome is not None:
            census[f"leg_{outcome}"] += 1
            continue
        priced += 1
        edge = 1.0 - total
        stake = max(total, 1e-6)
        exh_ok = v.exhaustive(edge=edge, stake=stake) if edge > 0 else False
        results.append((eid, len(legs), days, edge, exh_ok, auth.has_other_leg if auth else False))

    print(f"      priced {priced}"
          f" | too thin at size {census['book_too_thin_at_size']}"
          f" | bad token {census['leg_bad_token']}")
    for k, c in sorted(census.items()):
        if k.startswith("leg_unfetchable"):
            print(f"      {k:44s} {c}")
    if thin_detail:
        med = sorted(d[2] for d in thin_detail)[len(thin_detail) // 2]
        print(f"      thin groups: median worst-leg depth {med:.0f} of {args.size:.0f} requested")

    print(f"\n{'=' * 88}\nRESULT\n{'=' * 88}")
    positive = [r for r in results if r[3] > 0]
    candidates = [r for r in positive if r[4]]
    print(f"  groups priced at {args.size:.0f} contracts/leg : {len(results)}")
    print(f"  with a positive post-cost edge             : {len(positive)}")
    print(f"  ...surviving the exhaustiveness test       : {len(candidates)}")

    if results:
        print(f"\n  {'event':>10} {'legs':>5} {'days':>7} {'edge/contract':>14} {'exh':>5} {'other':>6}")
        for eid, n, days, edge, exh, other in sorted(results, key=lambda r: -r[3])[:15]:
            print(f"  {eid:>10} {n:5d} {days:7.1f} {edge:>+14.5f} {str(exh):>5} {str(other):>6}")

    print()
    if candidates:
        print(f"  {len(candidates)} CANDIDATE(S). Not arbitrage - a shortlist to examine.")
        print("  Unverified here: quote persistence (a counterparty may withdraw on being hit),")
        print("  settlement/oracle risk, and the nominal endDate used for carry. Gate 3 territory.")
    else:
        print("  No candidate survived. On this sample the venue shows no executable structural")
        print("  edge at this size, which is a measurement about the venue and this size - not")
        print("  proof that none exists (AXIOMS A1).")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
