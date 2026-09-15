"""Feasibility census: is either hypothesis class *measurable* before it is interesting?

    python census.py [--pages N] [--probe M]

Gate 0 established that detecting a market-relative forecasting edge needs **hundreds of
independent events**. That turns a question nobody had asked into the gating one: does the venue
actually supply them? This script answers it from public data, for both hypothesis classes, in one
pass - before any adapter, model or scanner is built (``docs/AXIOMS.md`` E1, E2).

**Class A — forecasting supply.** Counts resolved binary markets, measures how many carry a usable
resolution and retrievable decision-time price history, and clusters them into independent events.
Reports a *range*, because "independent event" has an upper and a conservative reading and pretending
otherwise would be false precision.

**Class B — structural supply.** Counts negRisk groups and their leg sums. Critically, it compares
each apparent deviation against the **settlement-discount null**: a multi-year contract paying $1 at
resolution is *supposed* to trade below its probability, so a group summing to 0.90 two years out is
priced correctly, not mispriced. Two independent false-positive sources are separated here:

1. **Truncated leg sets.** A paginated scan sees part of a group and reports a huge fake edge. A
   first hand-probe of this API produced apparent "53% arbitrage" entirely from this artifact.
2. **Carry.** Most of the residual deviation at long horizons is capital lock-up
   (Gebele & Matthes 2026), which `kairos.baseline.SettlementTerms` already models.

Read-only. Writes nothing to the repo but the report; raw data goes to a scratch directory.
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from kairos.baseline import SettlementTerms

GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB_HISTORY = "https://clob.polymarket.com/prices-history"
# The CLOB host 403s the default urllib agent. Discovered by probing, not assumed.
HEADERS = {"User-Agent": "Mozilla/5.0 (ordo-kairos feasibility census)"}
PAGE = 100

#: Gate 0's measured requirement: ~300 independent events for 90%+ power against a *large* edge.
REQUIRED_EVENTS = 300


def fetch(url: str, timeout: int = 40):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.loads(fh.read().decode("utf-8"))


def pull_closed(pages: int) -> list[dict]:
    out: list[dict] = []
    for i in range(pages):
        try:
            batch = fetch(f"{GAMMA}?closed=true&limit={PAGE}&offset={i * PAGE}&order=endDate&ascending=false")
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  page {i}: FAILED ({exc}) - stopping pull", file=sys.stderr)
            break
        if not batch:
            break
        out.extend(batch)
        print(f"  page {i + 1}/{pages}: +{len(batch)} (total {len(out)})", flush=True)
        time.sleep(0.15)
    return out


#: Resolved markets report near-0/near-1 floats, not exact 0/1 - e.g.
#: ``["0.00000101108", "0.99999898891"]``. An exact-equality check silently rejects every one of
#: them, which is how the first run of this census reported 0% resolved. Voided markets report
#: ``["0", "0"]`` and are correctly excluded by the sum test.
RESOLUTION_TOL = 1e-4


def resolution_of(market: dict) -> float | None:
    """The realised binary outcome, or None if the market did not resolve cleanly."""
    try:
        prices = [float(x) for x in json.loads(market["outcomePrices"])]
    except (KeyError, ValueError, TypeError):
        return None
    if len(prices) != 2 or abs(sum(prices) - 1.0) > RESOLUTION_TOL:
        return None
    if prices[0] > 1.0 - RESOLUTION_TOL:
        return 1.0
    if prices[0] < RESOLUTION_TOL:
        return 0.0
    return None  # settled between the extremes: not a clean binary resolution


def days_between(start: str | None, end: str | None) -> float | None:
    def parse(s):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None

    a, b = parse(start), parse(end)
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 86400.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=30, help="pages of 100 closed markets")
    ap.add_argument("--probe", type=int, default=25, help="markets to probe for price history")
    args = ap.parse_args()

    print("=" * 78)
    print("ORDO KAIROS - FEASIBILITY CENSUS (Polymarket, public API, read-only)")
    print("=" * 78)
    print(f"\nPulling up to {args.pages * PAGE} closed markets...")
    markets = pull_closed(args.pages)
    if not markets:
        print("\nNo data retrieved. Census inconclusive.")
        return 1

    # ---------------- Class A: forecasting supply ----------------
    print(f"\n{'=' * 78}\nCLASS A - FORECASTING SUPPLY\n{'=' * 78}")
    resolved = [m for m in markets if resolution_of(m) is not None]
    with_tokens = [m for m in resolved if m.get("clobTokenIds")]
    horizons = [
        d for d in (days_between(m.get("startDate"), m.get("endDate")) for m in resolved)
        if d is not None and d > 0
    ]

    print(f"  markets pulled                {len(markets)}")
    print(f"  cleanly resolved binary       {len(resolved)}  ({100*len(resolved)/len(markets):.1f}%)")
    print(f"  ...with CLOB token ids        {len(with_tokens)}")
    if horizons:
        # NOMINAL horizon only. Many markets resolve long before their stated end date - one
        # sampled market ran 7 days against a 2029 end date - so this is an upper bound on
        # trading life, not a measure of it. The probe below measures usable history directly.
        print(f"  NOMINAL horizon (days)        median {statistics.median(horizons):.1f}, "
              f"p10 {sorted(horizons)[len(horizons)//10]:.1f}, max {max(horizons):.0f}")
        print("    (nominal only - markets often resolve early; see history probe below)")

    # Independent-event clustering: report the range honestly.
    grouped = collections.defaultdict(list)
    for m in resolved:
        grouped[m.get("negRiskMarketID") or f"solo:{m.get('id')}"].append(m)
    upper = len(resolved)
    conservative = len(grouped)
    print(f"\n  independent events (upper bound, each market)   {upper}")
    print(f"  independent events (negRisk groups collapsed)  {conservative}")
    verdict_a = "SUPPLY OK" if conservative >= REQUIRED_EVENTS else "INSUFFICIENT IN THIS SAMPLE"
    print(f"  Gate-0 requirement                             {REQUIRED_EVENTS}")
    print(f"  -> {verdict_a}")

    # Price-history availability rate, measured not assumed.
    print(f"\n  probing usable price history on {args.probe} markets (fidelity=1440, daily)...")
    ok = 0
    failed = 0
    points: list[int] = []
    spans: list[float] = []
    for m in with_tokens[: args.probe]:
        try:
            tid = json.loads(m["clobTokenIds"])[0]
        except (KeyError, ValueError, TypeError, IndexError):
            failed += 1  # malformed record, not a market without history
            continue
        try:
            hist = fetch(f"{CLOB_HISTORY}?market={tid}&interval=max&fidelity=1440", timeout=25)
        except Exception:
            # A FETCH FAILURE IS NOT A MEASUREMENT (AXIOMS G5). Counting it as "no history"
            # understates retrievability and would kill a hypothesis class on an apparatus
            # artefact - which is exactly what the HTTP 403 in Pass 5 nearly did.
            failed += 1
            time.sleep(0.1)
            continue
        h = hist.get("history", []) if isinstance(hist, dict) else []
        if h:
            ok += 1
            points.append(len(h))
            if len(h) > 1:
                spans.append((h[-1]["t"] - h[0]["t"]) / 86400.0)
        time.sleep(0.1)
    probed = min(args.probe, len(with_tokens))
    measured = probed - failed
    if measured > 0:
        print(f"  history retrievable           {ok}/{measured} ({100*ok/measured:.0f}%) "
              f"of markets actually MEASURED")
    if failed:
        print(f"  !! fetch failed               {failed}/{probed} - excluded from the rate above,")
        print(f"     because a failed measurement is not evidence of absent history (AXIOMS G5).")
    if probed:
        if points:
            usable = sum(1 for n in points if n >= 5)
            print(f"  points per market             median {int(statistics.median(points))}, "
                  f"min {min(points)}, max {max(points)}")
            if spans:
                print(f"  ACTUAL traded span (days)     median {statistics.median(spans):.1f}, "
                      f"max {max(spans):.1f}")
            print(f"  markets with >=5 price points {usable}/{len(points)} "
                  f"({100*usable/len(points):.0f}%)")
            print("\n  BINDING CONSTRAINT for Class A: usable history density, not event count.")
            print("  Point counts are parameter-sensitive (fidelity=60 returned 1 pt where")
            print("  fidelity=1440 returned 8) and many markets resolve within days of listing.")
            print("  A real Gate-1 adapter must measure per-market history before including it.")

    # ---------------- Class B: structural supply ----------------
    print(f"\n{'=' * 78}\nCLASS B - STRUCTURAL SUPPLY (negRisk groups)\n{'=' * 78}")
    open_groups = collections.defaultdict(list)
    print("  pulling open markets for live group structure...")
    open_markets: list[dict] = []
    truncated = False
    for i in range(10):
        try:
            batch = fetch(f"{GAMMA}?closed=false&limit={PAGE}&offset={i * PAGE}")
        except Exception:
            # Distinguished from "no more pages" on purpose: a silent break here understates group
            # structure and looks identical to having reached the end (AXIOMS G5). The same
            # confusion made three HTTP-500 quarters read as "no markets resolved then".
            truncated = True
            break
        if not batch:
            break
        open_markets.extend(batch)
        time.sleep(0.15)
    if truncated:
        print("  !! open-market pull was TRUNCATED by a fetch failure - group structure below is a")
        print("     LOWER BOUND, not a measurement of what exists (AXIOMS G5).")
    for m in open_markets:
        if m.get("negRiskMarketID"):
            open_groups[m["negRiskMarketID"]].append(m)

    rows = []
    for gid, legs in open_groups.items():
        if len(legs) < 4:
            continue
        total = 0.0
        ok_group = True
        for m in legs:
            try:
                total += float(json.loads(m["outcomePrices"])[0])
            except (KeyError, ValueError, TypeError, IndexError):
                # Narrow on purpose: a malformed record IS a measurement that this leg is
                # unusable. A bare `except Exception` here would also swallow interpreter and
                # memory errors as "bad data" (AXIOMS G5).
                ok_group = False
                break
        if not ok_group:
            continue
        # Days from NOW to resolution. The first version passed None as the start date, so every
        # horizon came back None and the carry adjustment silently never ran.
        now = datetime.now(timezone.utc).isoformat()
        hs = [days_between(now, m.get("endDate")) for m in legs]
        hs = [h for h in hs if h is not None and h > 0]
        days = statistics.median(hs) if hs else None
        rows.append((gid, len(legs), total, days, legs[0].get("question", "")[:44]))

    print(f"  open markets pulled           {len(open_markets)}")
    print(f"  negRisk groups (>=4 legs)     {len(rows)}")
    if rows:
        print(f"\n  {'legs':>4} {'sum(YES)':>9} {'raw dev':>8} {'carry-adj dev':>14}   question")
        print(f"  {'-'*4} {'-'*9} {'-'*8} {'-'*14}   {'-'*40}")
        survivors = 0
        for gid, n, total, days, q in sorted(rows, key=lambda r: -r[1])[:10]:
            raw = total - 1.0
            if days and days > 0:
                # A $1 payoff `days` away should trade at the discounted value, so the
                # no-arbitrage sum is the discount factor, not 1.0.
                expected = SettlementTerms(days_to_settlement=days).discount_factor
                adj = total - expected
                adj_s = f"{adj:+14.4f}"
            else:
                adj = raw
                adj_s = f"{raw:+14.4f} *"
            if abs(adj) > 0.02:
                survivors += 1
            print(f"  {n:4d} {total:9.4f} {raw:+8.4f} {adj_s}   "
                  f"{q.encode('ascii', 'replace').decode()}")
        print(f"\n  groups whose deviation survives carry adjustment: {survivors}/{min(10,len(rows))}"
              " (shown)")
        print("  NOTE: leg sets may still be truncated by pagination. A surviving deviation here is")
        print("        a CANDIDATE, never a confirmed arbitrage (docs/AXIOMS.md A5, D1).")

    print(f"\n{'=' * 78}")
    print("Both classes measured from public data. Neither is validated by this census;")
    print("it establishes only whether the raw material exists to run PROTOCOL Gates 1-2.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
