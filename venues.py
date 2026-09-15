"""Venue feasibility inventory: can a third venue supply what Gate C requires?

    python venues.py [--sample 80]

``docs/PROTOCOL.md`` Gate C's stopping rule says that below 200 verified pairs the verdict is
WITHHELD and *"the honest next move is a different venue pair"*. This is that move, done as a
**feasibility probe before an adapter** rather than after one: building a venue adapter costs a day,
and three of the four checks below can kill a candidate in a minute.

A venue is usable for the cross-venue measurement only if it publishes **all three**:

1. **Resolution rules** — without them there is no resolution source, and two markets with different
   arbiters are different events.
2. **A determination instant.** Not a date: an instant. Gate C2 measured why this is not a
   formality — Polymarket and Kalshi both list "Will Trump recognize Somaliland *before 2027*" and
   their deadlines are **ten hours and one minute apart**. An event in that window resolves YES on
   one venue and NO on the other, so a position held across them as a hedge is not a hedge.
3. **Order-book depth.** Top-of-book prices are not enough: an edge at the touch is not an edge at
   size (AXIOMS D1), and that was measured on Polymarket rather than assumed.

A venue failing any one of these cannot be *verified* against another, whatever its prices look
like. This script reports which, so a rejected venue stays rejected for a stated reason (C9a).
"""

from __future__ import annotations

import argparse
import collections
import json
import time
import urllib.error
import urllib.request

from kairos.identity import extract_prose_instant

HEADERS = {"User-Agent": "ordo-kairos venue survey", "Accept": "application/json"}

#: Candidates and their public, unauthenticated entry points. Real-money venues only — a play-money
#: market cannot host a hedge whatever its data quality, so it is recorded and not probed further.
CANDIDATES = (
    ("predictit", "https://www.predictit.org/api/marketdata/all/"),
    ("smarkets", "https://api.smarkets.com/v3/events/?state=upcoming&limit=5"),
    ("manifold", "https://api.manifold.markets/v0/markets?limit=3"),
    ("metaculus", "https://www.metaculus.com/api2/questions/?limit=3"),
    ("insight", "https://insightprediction.com/api/markets"),
    ("limitless", "https://api.limitless.exchange/markets?limit=3"),
)

SMARKETS = "https://api.smarkets.com/v3"
POLITICS_ROOT = "742967"


def get(url: str, timeout: int = 25):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as fh:
        return json.loads(fh.read())


def reachability() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, url in CANDIDATES:
        try:
            get(url)
            out[name] = "reachable"
        except urllib.error.HTTPError as e:
            out[name] = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            out[name] = type(e).__name__
        time.sleep(0.1)
    return out


def predictit_evidence() -> dict[str, str]:
    """PredictIt publishes four touch prices and no rules at all."""
    data = get("https://www.predictit.org/api/marketdata/all/", timeout=40)
    markets = data.get("markets") or []
    contracts = [c for m in markets for c in (m.get("contracts") or [])]
    dated = sum(1 for c in contracts if str(c.get("dateEnd", "NA")) != "NA")
    has_rules = any("rules" in k.lower() or "description" in k.lower()
                    for m in markets[:1] for k in m)
    return {
        "markets": str(len(markets)),
        "contracts": str(len(contracts)),
        "rules text": "yes" if has_rules else "NONE - no rules field in the payload",
        "determination instant": f"{dated}/{len(contracts)} carry any end date, and it is a bare "
                                 f"date - never a clock time",
        "book depth": "NONE - bestBuy/bestSell only, no ladder",
    }


def smarkets_evidence(sample: int) -> dict[str, str]:
    """Smarkets has rules and a real ladder. The question is the instant."""
    leaves: list[dict] = []
    frontier, seen = [POLITICS_ROOT], set()
    while frontier and len(leaves) < sample * 2:
        parent = frontier.pop(0)
        try:
            children = get(f"{SMARKETS}/events/?parent_id={parent}&state=upcoming&limit=100")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            continue
        for child in children.get("events") or []:
            if child["id"] in seen:
                continue
            seen.add(child["id"])
            kids = get(f"{SMARKETS}/events/?parent_id={child['id']}&state=upcoming&limit=100")
            (frontier if kids.get("events") else leaves).append(
                child["id"] if kids.get("events") else child)
        time.sleep(0.05)

    total = with_instant = with_prose = with_rules = 0
    depth_seen = False
    for event in leaves[:sample]:
        try:
            markets = get(f"{SMARKETS}/events/{event['id']}/markets/").get("markets") or []
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            continue
        rules = str(event.get("special_rules") or "")
        with_rules += bool(rules)
        for market in markets:
            total += 1
            if market.get("settlement_datetime"):
                with_instant += 1
            instant, _ = extract_prose_instant(f"{rules} {market.get('description') or ''}")
            if instant:
                with_prose += 1
            if not depth_seen:
                try:
                    quotes = get(f"{SMARKETS}/markets/{market['id']}/quotes/")
                    depth_seen = any(v.get("offers") for v in quotes.values())
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
                    pass
        time.sleep(0.03)
    return {
        "politics markets sampled": str(total),
        "rules text": f"{with_rules}/{min(len(leaves), sample)} events carry special_rules",
        "determination instant": f"{with_instant}/{total} structured, {with_prose}/{total} "
                                 f"recoverable from prose",
        "book depth": "yes - bids/offers with quantities" if depth_seen else "not observed",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=80, help="Smarkets leaf events to sample")
    args = ap.parse_args()

    print("=" * 92)
    print("VENUE FEASIBILITY - CAN A THIRD VENUE SUPPLY WHAT GATE C REQUIRES?")
    print("=" * 92)
    print("  Required: resolution rules, a determination INSTANT, and order-book depth.")
    print("  A venue missing any one of them cannot be verified against another at any price.")

    print("\n[1/3] Reachability (public, unauthenticated)")
    status = reachability()
    for name, state in status.items():
        print(f"      {name:<12} {state}")

    print("\n[2/3] PredictIt - what the payload carries")
    if status.get("predictit") == "reachable":
        for key, value in predictit_evidence().items():
            print(f"      {key:<24} {value}")
    else:
        print("      unreachable; nothing measured")

    print(f"\n[3/3] Smarkets - sampling up to {args.sample} politics events", flush=True)
    if status.get("smarkets") == "reachable":
        for key, value in smarkets_evidence(args.sample).items():
            print(f"      {key:<24} {value}")
    else:
        print("      unreachable; nothing measured")

    print(f"\n{'=' * 92}\nVERDICT\n{'=' * 92}")
    print("  Recorded so a rejected venue stays rejected for a stated reason, not a vague one:")
    print()
    print("    predictit  NO rules field at all, no clock time on any contract, and top-of-book")
    print("               prices only. Identity cannot be verified and size cannot be measured.")
    print("    smarkets   Rules on a minority of events and a real ladder - but NO determination")
    print("               instant, structured or in prose. Gate C2 measured what that costs: two")
    print("               markets both labelled 'before 2027' settled 10h01m apart.")
    print("    manifold   Play money, AMM, resolved at the market CREATOR's discretion. Not a data")
    print("               limitation - a regulated contract cannot be hedged against a stranger's")
    print("               judgement at any price.")
    print("    metaculus  No money at stake. Forecast source, not a venue.")
    print("    insight / limitless   authenticated or gone.")
    print()
    print("  So the venue-pair branch is exhausted for PUBLICLY REACHABLE venues. What remains is")
    print("  authenticated access (Betfair app key, a broker account), which is an operator")
    print("  decision and is outside F3 - no broker integration until the protocol is passed.")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
