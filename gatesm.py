"""Gate SM.0: a different counterparty population. Does Smarkets quote a wider spread?

    python gatesm.py [--events 200]

``docs/PROTOCOL.md`` Class SM. Registered 2026-09-14, before this was written and before any
Smarkets spread figure was computed.

**This is not another venue test.** Gate K.0 varied the venue and found two indistinguishable. The
variable never varied is the **counterparty**: every class here traded against political and crypto
participants, who Gate M measured taking **96.1%** of the half-spread. Smarkets' flow is largely
recreational sports bettors.

**The primary statistic is the half-spread in probability units, never ticks.** Smarkets ladders in
decimal odds, giving a probability-space tick of ~0.005-0.008 — finer than Polymarket's and Kalshi's
cent. "Spread exceeds one tick" is therefore easier to satisfy here for reasons that have nothing to
do with the counterparty, and using Gate K.0's statistic would manufacture a difference out of a
tick-size artefact.

Nothing here trades or quotes (F3).
"""

from __future__ import annotations

import argparse
import collections
import json
import urllib.error
import urllib.request

from kairos.costs import CONSERVATIVE
from kairos.inference import weighted_share_ci

BASE = "https://api.smarkets.com/v3"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}

#: Kalshi's measured flow-weighted median half-spread (Gate K.0: 1.00 tick of $0.01), which is also
#: this repository's standing `CONSERVATIVE.half_spread`. The two agreeing is why it is the comparator.
COMPARATOR_HALF_SPREAD = 0.005

MIN_MARKETS = 200

#: Decimal-odds ladder, derived empirically from 283 distinct prices across 2,563 books rather than
#: taken from documentation. `(odds_below, increment)`, first match wins.
ODDS_LADDER = ((2.0, 0.01), (3.0, 0.02), (4.0, 0.05), (6.0, 0.10),
               (10.0, 0.20), (20.0, 0.50), (float("inf"), 1.00))


def get(path: str) -> dict:
    try:
        req = urllib.request.Request(f"{BASE}{path}", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as fh:
            return json.loads(fh.read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        # AXIOMS G5: a fetch failure is an error, never a measurement of zero.
        return {"_error": f"{type(exc).__name__}: {exc}"}


def odds_increment(odds: float) -> float:
    for below, step in ODDS_LADDER:
        if odds < below:
            return step
    return ODDS_LADDER[-1][1]


def probability_tick(price: float) -> float | None:
    """Probability-space tick at ``price``, from the decimal-odds ladder.

    One rung up the ladder from odds ``o`` is ``o + delta``, so the probability step is
    ``1/o - 1/(o+delta)`` — which shrinks as the price rises and is **not** a constant.
    """
    if not 0.0 < price < 1.0:
        return None
    odds = 1.0 / price
    delta = odds_increment(odds)
    return price - 1.0 / (odds + delta)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=200)
    args = ap.parse_args()

    print("=" * 94)
    print("GATE SM.0 - A DIFFERENT COUNTERPARTY POPULATION (Smarkets)")
    print("=" * 94)
    print("  PRIMARY units: PROBABILITY (dollars per $1 contract). Never ticks - the three venues")
    print("  have different tick sizes and ticks are not comparable across them.")
    print("  Weighting: by TRADED VOLUME, not market count (Pass 28.1). Scale-invariant.")
    print(f"  Comparator: {COMPARATOR_HALF_SPREAD} half-spread (Kalshi measured; repo standing).")
    print("  NO fee or commission is measured. NOTHING IS TRADED OR QUOTED.")

    print(f"\n[1/3] Fetching live events and markets...", flush=True)
    ev = get(f"/events/?state=live&limit={args.events}")
    if "_error" in ev:
        print(f"  WITHHELD - event fetch failed: {ev['_error']}")
        return 1
    events = ev.get("events", [])
    markets, errors = [], collections.Counter()
    for i in range(0, len(events), 20):
        ids = ",".join(e["id"] for e in events[i:i + 20])
        r = get(f"/events/{ids}/markets/")
        if "_error" in r:
            errors["market_fetch"] += 1
            continue
        markets.extend(r.get("markets", []))
    print(f"      live events {len(events)}   markets {len(markets)}   fetch errors {errors['market_fetch']}")

    print(f"\n[2/3] Fetching books and volumes...", flush=True)
    # Volume is per MARKET; quotes are per CONTRACT. Both are needed, so both are fetched.
    volumes: dict[str, float] = {}
    quotes: dict[str, dict] = {}
    contract_market: dict[str, str] = {}
    # `contract_selections` on the market object is null; the mapping lives on /contracts/.
    # Verified rather than assumed, after a first run WITHHELD with zero eligible markets.
    for i in range(0, len(markets), 40):
        mids = [m["id"] for m in markets[i:i + 40]]
        if not mids:
            continue
        joined = ",".join(mids)
        v = get(f"/markets/{joined}/volumes/")
        if "_error" in v:
            errors["volume_fetch"] += 1
        else:
            for row in v.get("volumes", []):
                try:
                    volumes[str(row["market_id"])] = float(row.get("volume") or 0.0)
                except (KeyError, TypeError, ValueError):
                    errors["bad_volume"] += 1
        c = get(f"/markets/{joined}/contracts/")
        if "_error" in c:
            errors["contract_fetch"] += 1
        else:
            for row in c.get("contracts", []):
                try:
                    contract_market[str(row["id"])] = str(row["market_id"])
                except (KeyError, TypeError):
                    errors["bad_contract"] += 1
        q = get(f"/markets/{joined}/quotes/")
        if "_error" in q:
            errors["quote_fetch"] += 1
            continue
        for cid, book in q.items():
            if isinstance(book, dict):
                quotes[str(cid)] = book
    print(f"      contracts quoted {len(quotes)}   mapped {len(contract_market)}   "
          f"markets with volume {len(volumes)}   "
          f"errors {dict(errors)}")

    print(f"\n[3/3] Half-spread in probability units, weighted by volume")
    census: collections.Counter[str] = collections.Counter()
    rows = []
    for cid, book in quotes.items():
        bids, offers = book.get("bids") or [], book.get("offers") or []
        if not bids or not offers:
            census["no_two_sided_quote"] += 1
            continue
        try:
            bid = max(float(d["price"]) for d in bids) / 10000.0
            ask = min(float(d["price"]) for d in offers) / 10000.0
        except (KeyError, TypeError, ValueError):
            census["bad_price"] += 1
            continue
        if not 0.0 < bid < ask < 1.0:
            census["crossed_or_degenerate"] += 1
            continue
        mid = (bid + ask) / 2.0
        if not (CONSERVATIVE.min_price <= mid <= CONSERVATIVE.max_price):
            census["longshot_out_of_band"] += 1
            continue
        mid_key = contract_market.get(cid)
        vol = volumes.get(mid_key or "", 0.0)
        if vol <= 0.0:
            census["no_flow"] += 1
            continue
        tick = probability_tick(mid)
        if tick is None or tick <= 0.0:
            census["no_tick"] += 1
            continue
        rows.append(((ask - bid) / 2.0, tick, mid, vol))
        census["eligible"] += 1
    for k, c in census.most_common(8):
        print(f"      {k:<28} {c}")

    if len(rows) < MIN_MARKETS:
        print(f"\n  WITHHELD - {len(rows)} markets against a floor of {MIN_MARKETS}. Apparatus,")
        print("  not evidence: no reading about the counterparty is licensed from this.")
        return 0

    total = sum(f for _, _, _, f in rows)
    ordered = sorted(((hs, f) for hs, _, _, f in rows), key=lambda x: x[0])
    cum, fw_median = 0.0, ordered[-1][0]
    for hs, f in ordered:
        cum += f
        if cum >= total / 2.0:
            fw_median = hs
            break

    # Interval on the PRIMARY (Pass 36): share of flow whose half-spread beats the comparator.
    beats = [hs > COMPARATOR_HALF_SPREAD for hs, _, _, _ in rows]
    w = [f for _, _, _, f in rows]
    ci = weighted_share_ci(beats, w, seed=20260914)
    share_beating = sum(f for b, f in zip(beats, w) if b) / total

    tick_room = sum(f for hs, t, _, f in rows if 2.0 * hs > t + 1e-12) / total

    print(f"\n      markets eligible                {len(rows)}")
    print(f"      flow-weighted MEDIAN half-spread {fw_median:.6f}   "
          f"(comparator {COMPARATOR_HALF_SPREAD})")
    print(f"      flow with half-spread > {COMPARATOR_HALF_SPREAD}      {share_beating:.1%}"
          + (f"   95% CI [{ci[0]:.1%}, {ci[1]:.1%}]" if ci else "   (no interval)"))
    print(f"      SECONDARY flow with tick room    {tick_room:.1%}"
          f"   <- NOT comparable to Kalshi's 26.6%: the tick here is ~0.005-0.008, not 0.01")

    print(f"\n{'=' * 94}\nVERDICT\n{'=' * 94}")
    print(f"  Smarkets flow-weighted median half-spread : {fw_median:.6f}")
    print(f"  Comparator (Kalshi measured, repo standing): {COMPARATOR_HALF_SPREAD:.6f}")

    if ci is None:
        print("\n  GATE SM.0: WITHHELD - no interval could be computed. Apparatus.")
    elif ci[1] < 0.5:
        print("\n  GATE SM.0: REFUTED. Most of the flow is quoted at or inside the comparator, so")
        print("  Smarkets offers a maker no more gross spread than venues already measured.")
        print("  The counterparty-population question is MOOT: retaining a larger share of")
        print("  nothing is nothing. Class SM closes.")
    elif ci[0] > 0.5:
        print("\n  GATE SM.0: NOT REFUTED on the cheap gate ONLY. A majority of flow is quoted")
        print("  wider than the comparator. This licenses a realized-half-spread measurement as")
        print("  a NEW registration, and licenses no claim about profitability whatever:")
        print("  Gate M found 96.1% of a wider spread going to adverse selection.")
    else:
        print("\n  GATE SM.0: NO VERDICT. The interval straddles, so the flow is not shown to be")
        print("  quoted either wider or tighter than the venues already measured.")
        print("  Three-state discipline (validity.py). Class SM neither closes nor licenses.")

    print("\n  Unmodelled: commission on NET WINNINGS (structurally hostile to a maker and not")
    print("  in the API), mechanisms that tax consistent winners, adverse selection itself,")
    print("  queue position, and operator eligibility on a UK-licensed venue. F3 stands.")
    print("=" * 94)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
