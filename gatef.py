"""Gate F: funding-rate carry, net of four crossings and of the liquidation that pays for it.

    python gatef.py --nulls      # the null gate, which must pass first
    python gatef.py              # the measurement

``docs/PROTOCOL.md`` Class F. Registered 2026-09-14, before this was written and before any carry
P&L was computed.

**The false-positive generator is a sample without an unwind.** Any carry backtest over a calm
window shows smooth accumulation, because that is what the strategy does right up until it doesn't.
And the reachable history is **98 days** — OKX caps it there and Binance is HTTP 451 from this
jurisdiction — so the real sample cannot be guaranteed to contain a drawdown. **The null gate
therefore carries the crash discipline**, and the measurement is only admissible after it passes.

Nothing here trades (F3). Venue eligibility is an operator precondition this repo does not assert.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import time
import urllib.request
from statistics import median

from kairos.carry import deployed_capital, liquidation_move, naive_carry, simulate
from kairos.costs import CONSERVATIVE

OKX = "https://www.okx.com/api/v5"

#: C11 — leverage raises return on capital and lowers the breach threshold at the same time.
LEVERAGES = (1.0, 2.0, 3.0, 5.0, 10.0)

#: OKX taker fee, conservative retail tier.
TAKER_FEE = 0.0005

#: Filling worse than the liquidation trigger, plus the exchange's liquidation charge.
PENALTY = 0.01

INSTRUMENTS = ("BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP")
PERIODS_PER_YEAR = 3 * 365          # funding settles every 8 hours
MIN_INSTRUMENTS = 3


def _get(url: str, tries: int = 3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=25).read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def funding_history(inst: str, pages: int = 12) -> list[tuple[int, float]]:
    """``(timestamp_ms, rate)`` newest-first, to the depth OKX serves.

    An empty page is a **genuine end** and an exception is **not** — the retrying fetcher above is
    what makes that distinction real, and conflating them is how a rate limit becomes a fact
    (``CORRECTIONS.md`` Pass 9).
    """
    out: list[tuple[int, float]] = []
    after: str | None = None
    for _ in range(pages):
        url = f"{OKX}/public/funding-rate-history?instId={inst}&limit=100"
        if after:
            url += f"&after={after}"
        rows = (_get(url) or {}).get("data") or []
        if not rows:
            break
        out += [(int(r["fundingTime"]), float(r["fundingRate"])) for r in rows]
        after = rows[-1]["fundingTime"]
        time.sleep(0.3)
    return out


def daily_candles(inst: str) -> list[tuple[int, float, float]]:
    """``(timestamp_ms, close, high)`` newest-first."""
    url = f"{OKX}/market/history-candles?instId={inst}&bar=1D&limit=300"
    rows = (_get(url) or {}).get("data") or []
    return [(int(r[0]), float(r[4]), float(r[2])) for r in rows]


# ---------------------------------------------------------------------------
# Gate F - the null gate
# ---------------------------------------------------------------------------

def world(n: int, *, funding_mean: float, funding_sd: float, vol: float, seed: int,
          shock_at: int | None = None, shock_size: float = 0.0
          ) -> tuple[list[float], list[float]]:
    """A funding path and a price path, with an optional sustained upward squeeze."""
    rng = random.Random(seed)
    f = [rng.gauss(funding_mean, funding_sd) for _ in range(n)]
    r = [rng.gauss(0.0, vol) for _ in range(n)]
    if shock_at is not None:
        for i in range(shock_at, min(shock_at + 10, n)):
            r[i] += shock_size / 10.0
    return f, r


H = 0.0002   # a healthy 8h funding rate: ~22%/yr gross

#: ``(name, kwargs, carry_pays)``. ``carry_pays`` is the ground truth the estimator must recover.
#: The **nulls are the worlds where carry does not pay once risk is counted** - reporting a profit
#: there licenses capital against a losing trade, which is the dangerous direction.
WORLDS = (
    ("liquidation_cascade (squeeze at t=40)", dict(funding_mean=H, funding_sd=H / 2, vol=0.004,
                                                   shock_at=40, shock_size=0.35), False),
    ("bear_regime        (funding negative)", dict(funding_mean=-H, funding_sd=H / 2,
                                                   vol=0.004), False),
    ("costs_exceed_carry (funding ~0)", dict(funding_mean=H / 40, funding_sd=H / 40,
                                             vol=0.002), False),
    ("steady_carry       (calm, healthy)", dict(funding_mean=H, funding_sd=H / 2,
                                                vol=0.004), True),
    ("high_funding       (rich, survivable)", dict(funding_mean=2 * H, funding_sd=H,
                                                   vol=0.006), True),
)


def hurdle_for(periods: int) -> float:
    """The 6%/yr capital hurdle, pro-rated to the holding period."""
    return CONSERVATIVE.settlement_wedge_annual * periods / PERIODS_PER_YEAR


def run_nulls(reps: int, periods: int, leverage: float) -> int:
    from kairos.nullworld import ALPHA, FPR_TAIL_ALPHA, POWER_FLOOR, _binomial_tail

    print("=" * 92)
    print("GATE F - NULL GATE for the carry estimator")
    print("=" * 92)
    print("  The false-positive generator is A SAMPLE WITHOUT AN UNWIND. Carry accumulates smoothly")
    print("  right up until it doesn't, and funding spikes POSITIVE during the squeeze that")
    print("  liquidates the short leg - it pays most when it is most dangerous.")
    print(f"  {reps} replications x {periods} periods | leverage {leverage:.0f}x "
          f"| breach at +{liquidation_move(leverage):.1%} | hurdle {hurdle_for(periods):.3%}")

    print(f"\n  {'world':<40} {'median RoC':>11} {'pays':>7} {'liq':>6} {'tail':>8} {'truth':>7}")
    ok = True
    for name, kw, pays in WORLDS:
        calls: collections.Counter[str] = collections.Counter()
        rocs: list[float] = []
        for rep in range(reps):
            f, r = world(periods, seed=500 + rep, **kw)
            res = simulate(f, r, leverage=leverage, taker_fee=TAKER_FEE, penalty=PENALTY)
            rocs.append(res.return_on_capital)
            calls["pays" if res.return_on_capital > hurdle_for(periods) else "no"] += 1
            calls["liq"] += 1 if res.liquidated else 0
        rate = calls["pays"] / reps
        tail = _binomial_tail(calls["pays"], reps, ALPHA)
        verdict = "PASS" if ((rate >= POWER_FLOOR) if pays else (tail >= FPR_TAIL_ALPHA)) else "FAIL"
        ok = ok and verdict == "PASS"
        print(f"  {name:<40} {median(rocs):>+11.4%} {rate:>6.0%} {calls['liq'] / reps:>5.0%} "
              f"{'-' if pays else f'{tail:8.4f}'} {str(pays):>7}  {verdict}")

    print(f"\n  EXHIBIT - the naive carry sum, blind to the price path:")
    f, r = world(periods, seed=99, **WORLDS[0][1])
    real = simulate(f, r, leverage=leverage, taker_fee=TAKER_FEE, penalty=PENALTY)
    naive = naive_carry(f, taker_fee=TAKER_FEE) / deployed_capital(leverage)
    print(f"      liquidation_cascade: naive says {naive:+.4%}, truth is {real.return_on_capital:+.4%}"
          f"  (liquidated at period {real.periods_held})")
    print(f"      A backtest that never looks at the price reports the PREMIUM and ignores the risk")
    print(f"      it is paid for. That is the entire reason this gate exists.")

    print(f"\n{'=' * 92}")
    print(f"  GATE F NULL GATE: {'PASSED' if ok else 'FAILED'}")
    if not ok:
        print("  The estimator does not separate the worlds. Fix it; do not tune them (A8).")
    else:
        print("  It reports losses where the carry is taken back and profits where it survives.")
        print("  `python gatef.py` is licensed.")
    print("=" * 92)
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# The measurement
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nulls", action="store_true")
    ap.add_argument("--reps", type=int, default=40)
    ap.add_argument("--periods", type=int, default=300)
    ap.add_argument("--leverage", type=float, default=5.0)
    args = ap.parse_args()
    if args.nulls:
        return run_nulls(args.reps, args.periods, args.leverage)

    print("=" * 92)
    print("GATE F - FUNDING CARRY, NET OF CROSSINGS AND LIQUIDATION")
    print("=" * 92)
    print(f"  hurdle {CONSERVATIVE.settlement_wedge_annual:.0%}/yr on DEPLOYED CAPITAL "
          f"(spot notional + perp margin), never on notional alone")
    print(f"  taker {TAKER_FEE:.2%}/crossing x4 | liquidation penalty {PENALTY:.1%}")
    print("  Binance is HTTP 451 from this jurisdiction; OKX caps history at ~98 days.")
    print("  NOTHING IS TRADED. Venue eligibility is an operator precondition, not asserted here.")

    print(f"\n[1/2] Fetching funding and price history...", flush=True)
    data = {}
    for inst in INSTRUMENTS:
        try:
            fund = funding_history(inst)
            cand = daily_candles(inst)
        except Exception as e:
            print(f"      {inst:16s} unfetchable: {type(e).__name__}")
            continue
        if not fund or not cand:
            print(f"      {inst:16s} no data")
            continue
        # Funding settles 3x daily; the candles are daily. Pair them oldest-first.
        fund = list(reversed(fund))
        cand = list(reversed(cand))
        rets = [cand[i][1] / cand[i - 1][1] - 1.0 for i in range(1, len(cand))]
        days = min(len(rets), len(fund) // 3)
        daily_f = [sum(x[1] for x in fund[3 * i:3 * i + 3]) for i in range(days)]
        data[inst] = (daily_f, rets[-days:])
        gross = (sum(daily_f) / days) * 365
        print(f"      {inst:16s} {days:>4}d  gross funding {gross:>+7.2%}/yr  "
              f"max 1d move {max(rets[-days:]):>+6.2%}")

    if len(data) < MIN_INSTRUMENTS:
        print(f"\n  WITHHELD - {len(data)} instruments against a floor of {MIN_INSTRUMENTS}.")
        return 0

    print(f"\n[2/2] Net return on deployed capital, by leverage")
    print(f"  {'instrument':<16} {'lev':>5} {'breach at':>10} {'net RoC/yr':>12} "
          f"{'liq':>5} {'vs 6%':>7}")
    best = (-1e18, None, None)
    for inst, (f, r) in data.items():
        for lev in LEVERAGES:
            res = simulate(f, r, leverage=lev, taker_fee=TAKER_FEE, penalty=PENALTY)
            ann = res.return_on_capital * 365 / len(f)
            clears = ann > CONSERVATIVE.settlement_wedge_annual
            print(f"  {inst:<16} {lev:>4.0f}x {liquidation_move(lev):>9.1%} {ann:>+12.2%} "
                  f"{'YES' if res.liquidated else '-':>5} {'CLEARS' if clears else 'below':>7}")
            if ann > best[0]:
                best = (ann, inst, lev)
    ann, inst, lev = best

    print(f"\n{'=' * 92}\nVERDICT\n{'=' * 92}")
    print(f"  instruments measured : {len(data)}  over {len(next(iter(data.values()))[0])} days")
    print(f"  best net return on capital : {ann:+.2%}/yr  ({inst} at {lev:.0f}x)")
    print(f"  hurdle                     : {CONSERVATIVE.settlement_wedge_annual:+.2%}/yr")
    if ann <= CONSERVATIVE.settlement_wedge_annual:
        print("\n  GATE F: REFUTED - carry does not clear the cost of the capital it locks.")
        print("  At no leverage does net return on deployed capital beat the 6% this repo already")
        print("  charges for locked collateral. Per the registered rule Class F closes.")
    else:
        print("\n  GATE F: NOT REFUTED at this leverage, on this window.")
        print("  The window is 98 days and CANNOT be guaranteed to contain an unwind - which is")
        print("  precisely the sample defect the null gate exists to price. Treat with suspicion:")
        print("  the carry is paid FOR the crash, so a window without one overstates it.")
    print("\n  Unmodelled and cutting against: exchange default (Pindza measures it as worse than")
    print("  price crashes; FTX is the realized case), crowding, cross-venue basis, and breach")
    print("  detection on daily CLOSES, which misses intraday squeezes.")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
