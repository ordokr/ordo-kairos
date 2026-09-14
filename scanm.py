"""Gate M measurement: what a maker actually keeps, on real Polymarket price history.

    python scanm.py [--markets 150]

``docs/PROTOCOL.md`` Gate M. **`python gatem.py --nulls` must pass first** and did, on 2026-09-14:
the estimator reports losses where flow is informed, the half-spread where it is not, and abstains
rather than guessing when the sample cannot carry the call.

The statistic is the realized half-spread ``R(60) = mean of D_t x (p_t - p_{t+60})`` — what a maker
who took the other side of each trade still holds an hour later. It **already nets** gross spread
capture against adverse selection, so a positive value means the spread survived the informed flow
and a negative one means it did not.

Two preconditions from the registration are enforced before anything is measured: the **longshot
band** (Pass 26.1, the exclusion no scanner in this repo applied until now) and **tick room** — a
market quoted at one tick is one an entrant cannot quote in, so it is not in the population.

Two limits, both measured rather than assumed
---------------------------------------------

**Power.** The null gate measured detection of a one-half-spread loss as needing on the order of
**100,000 pooled observations**; at 20,000 it fired 2 times in 10. No single market carries that, so
contributions are pooled across markets and the pooled count is reported against the threshold. Below
it the verdict is WITHHELD, never "no effect" (AXIOMS A1).

**The tick test attenuates.** With impact large relative to the spread, ``p_t - p_{t-1}`` is driven
by the previous trade's permanent move as much as by this trade's side, so direction is misclassified
worst exactly when impact is largest. Measured: a true ``R`` of ``-0.010`` reads as ``-0.0025``. The
bias pulls toward zero, which **flatters the maker** — so a REFUTED verdict here is safer than a
passing one, and a passing one deserves the suspicion.

Nothing here trades or quotes (F3).
"""

from __future__ import annotations

import argparse
import collections
import json
import time
import urllib.error
from statistics import median

from kairos.microstructure import bootstrap_ci, contributions, realized_half_spread
from kairos.polymarket import _get_retry, cache_dir
from gatem import HORIZONS, interval_verdict, open_universe, quote

CLOB_HISTORY = "https://clob.polymarket.com/prices-history"

#: Registered decision horizon.
HORIZON = 60

#: From the registration's stopping rule.
MIN_MARKETS = 100

#: From the null gate's measured detection threshold, not chosen here.
MIN_OBSERVATIONS = 100_000


def minute_history(token_id: str) -> list[float]:
    """One day of minute-sampled prices for a CLOB token, or ``[]``.

    Cached under its **own** directory. ``kairos.polymarket.fetch_history`` keys its cache on the
    token alone while requesting a different interval and fidelity, so sharing that cache would
    silently serve daily data to a minute-resolution measurement.

    A failed fetch is never cached — the lesson `fetch_history` records in its own docstring, where
    618 of 14,005 cached histories turned out to be empty with no way to tell a measured empty from
    a swallowed network error (AXIOMS G5).
    """
    cache = cache_dir() / "history_1m"
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{token_id[:40]}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    try:
        raw = _get_retry(f"{CLOB_HISTORY}?market={token_id}&interval=1d&fidelity=1", timeout=25)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
            json.JSONDecodeError):
        return []
    points = raw.get("history", []) if isinstance(raw, dict) else []
    prices = [float(p["p"]) for p in points if isinstance(p, dict) and "p" in p]
    path.write_text(json.dumps(prices), encoding="utf-8")
    time.sleep(0.1)
    return prices


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=21)
    ap.add_argument("--markets", type=int, default=150, help="markets to fetch history for")
    args = ap.parse_args()

    print("=" * 88)
    print("GATE M - WHAT A MAKER KEEPS (realized half-spread on real price history)")
    print("=" * 88)
    print("  Null gate PASSED 2026-09-14. Preconditions applied: longshot band, tick room > 1.")
    print(f"  horizon {HORIZON}m | need >= {MIN_MARKETS} markets and >= {MIN_OBSERVATIONS:,} "
          f"pooled observations")
    print("  The tick test attenuates R toward zero, which FLATTERS the maker: a refutation here")
    print("  is safer than a pass. NOTHING IS TRADED OR QUOTED.")

    print(f"\n[1/3] Sweeping for in-band markets with tick room...", flush=True)
    census: collections.Counter[str] = collections.Counter()
    eligible: list[tuple[dict, float]] = []
    for m in open_universe(args.pages):
        q = quote(m)
        if isinstance(q, str):
            census[q] += 1
            continue
        spread, tick, price, _ = q
        if spread / tick <= 1.0 + 1e-9:
            census["no_tick_room"] += 1
            continue
        eligible.append((m, spread))
    for key, count in census.most_common():
        print(f"      {key:<34} {count}")
    print(f"      {'eligible (in band, tick room)':<34} {len(eligible)}")

    print(f"\n[2/3] Fetching minute history for up to {args.markets} of them...", flush=True)
    pooled: list[float] = []
    per_market: list[float] = []
    pooled_by_horizon: dict[int, list[float]] = {k: [] for k in HORIZONS}
    half_spreads: list[float] = []
    used = 0
    for m, spread in eligible[:args.markets]:
        try:
            token = json.loads(m["clobTokenIds"])[0]
        except (KeyError, ValueError, TypeError, IndexError):
            census["bad_token"] += 1
            continue
        prices = minute_history(str(token))
        if len(prices) < 2 * HORIZON:
            census["history_too_short"] += 1
            continue
        obs = contributions(prices, HORIZON)
        if not obs:
            census["no_directional_trades"] += 1
            continue
        r = realized_half_spread(prices, HORIZON)
        if r is None:
            census["no_measurement"] += 1
            continue
        used += 1
        pooled += obs
        per_market.append(r)
        half_spreads.append(spread / 2.0)
        for k in HORIZONS:
            pooled_by_horizon[k] += contributions(prices, k)
    print(f"      markets with usable history      {used}")
    print(f"      pooled observations              {len(pooled):,}")
    for key in ("history_too_short", "no_directional_trades", "bad_token", "no_measurement"):
        if census[key]:
            print(f"      {key:<32} {census[key]}")

    print(f"\n[3/3] Realized half-spread")
    print(f"  {'horizon':>8} {'R(k)':>10} {'interval':>26} {'obs':>10}")
    for k in HORIZONS:
        obs = pooled_by_horizon[k]
        ci = bootstrap_ci(obs, seed=k, draws=400)
        mean = sum(obs) / len(obs) if obs else float("nan")
        band = f"[{ci[0]:+.5f}, {ci[1]:+.5f}]" if ci else "(no interval)"
        print(f"  {k:>8} {mean:>+10.5f} {band:>26} {len(obs):>10,}")

    quoted_half = median(half_spreads) if half_spreads else float("nan")
    ci = bootstrap_ci(pooled, seed=7, draws=800)
    call = interval_verdict(ci)

    print(f"\n{'=' * 88}\nVERDICT\n{'=' * 88}")
    print(f"  markets                     : {used} (need {MIN_MARKETS})")
    print(f"  pooled observations         : {len(pooled):,} (need {MIN_OBSERVATIONS:,})")
    print(f"  median quoted half-spread   : {quoted_half:+.5f}")
    if per_market:
        print(f"  unweighted mean of per-market R(60) : "
              f"{sum(per_market) / len(per_market):+.5f}  (flow-weighted is the primary)")
    if ci:
        print(f"  flow-weighted R(60)         : [{ci[0]:+.5f}, {ci[1]:+.5f}]")
        print(f"  implied adverse selection   : {quoted_half - (ci[0] + ci[1]) / 2:+.5f} "
              f"per contract (quoted half-spread less what survives)")

    if used < MIN_MARKETS or len(pooled) < MIN_OBSERVATIONS:
        print("\n  GATE M: WITHHELD - underpowered.")
        print("  The null gate measured detection of a one-half-spread loss as needing ~100,000")
        print("  pooled observations. Below that a null reading is a statement about the sample,")
        print("  not about the venue. 'Not enough evidence' is never 'no effect' (AXIOMS A1).")
    elif call == "loss":
        print("\n  GATE M: REFUTED - informed flow takes the whole spread.")
        print("  The entire interval sits below zero: a maker taking the other side of this flow")
        print("  does not keep the spread. Per the registered decision rule Class M closes, and")
        print("  with Classes A, B and C already closed the registered programme ends.")
        print("  The tick test attenuates toward zero, so the true loss is LARGER than measured.")
    elif call == "profit":
        print("\n  GATE M: NOT REFUTED - the spread survives the flow at this horizon.")
        print("  A maker edge is not excluded at this venue. Proceeds to Gate 3, which for this")
        print("  class must model QUEUE POSITION - nothing here measures whether the fills would")
        print("  arrive at all, and 77.4% of flow sits in one-tick markets an entrant cannot")
        print("  improve on (GATEM-RESULTS.md). Treat with suspicion: the estimator's known bias")
        print("  points this way.")
    else:
        print("\n  GATE M: NO VERDICT - the interval straddles zero.")
        print("  Powered, and still unable to call it. That is a finding about effect size, not")
        print("  an invitation to re-run at a different horizon (A8).")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
