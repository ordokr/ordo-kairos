"""Gate M.0: the maker dead-on-arrival check.

    python gatem.py [--pages 21]

``docs/PROTOCOL.md`` Class M / Gate M.0. Registered 2026-09-14, before this was built and before any
spread or volume number existed.

Every measurement in this repository is a **taker** measurement: ``half_spread`` is charged as the
cost of crossing, and ``maker_fee_coeff`` has sat at ``0.0`` unused. A maker inverts that term and,
more to the point, changes *what the constraint is* -- a taker's opportunity set is visible
mispricings, which Gate 4.0 measured at **$24.40**, while a maker's is flow crossing their quote,
which scales with venue volume.

**The primary falsifier is tick room, not spread size.** A market already quoted at one tick offers
an entrant nothing: the quote cannot be improved, so the only way in is the back of an existing
queue and queue position decides the fills. An aggregate spread that looks attractive while sitting
entirely in one-tick markets is a spread that is **not available to a new participant**.

This gate is cheap because Gamma publishes ``spread``, ``orderPriceMinTickSize`` and ``volumeNum``
on the market listing itself. **No order book is fetched.**

**It is expected to pass, and passing is expected to mean very little.** Adverse selection, queue
position, competition and inventory risk are all excluded and all cut against; Polymarket's
published maker rewards are excluded and cut for. A REFUTED verdict here refutes *spread capture*,
not market making. Nothing here trades or quotes (F3).
"""

from __future__ import annotations

import argparse
import collections
import random
import time
import urllib.error
from datetime import datetime, timezone
from statistics import median

from kairos.costs import CONSERVATIVE
from kairos.polymarket import _get_retry

GAMMA = "https://gamma-api.polymarket.com/markets"
PAGE = 100

#: Registered floor: ten times the taker ceiling Gate 4.0 measured ($10.47/yr). Absolute and
#: internally sourced, never a rate -- CORRECTIONS.md Pass 27.1. Below 10x, a structural change has
#: not changed the structure, it has moved a number while adding machinery.
TAKER_CEILING_ANNUAL = 10.47
FLOOR_ANNUAL = 10.0 * TAKER_CEILING_ANNUAL


def days_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        start = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(1.0, (datetime.now(timezone.utc) - start).total_seconds() / 86400.0)


def open_universe(pages: int) -> list[dict]:
    """Sweep the open universe from both ends of the volume distribution, deduped.

    The same construction ``scanb.py`` uses and for the same reason: a measurement taken only on the
    high-attention head is weakest exactly where the literature locates surviving mispricing.
    ``offset`` caps at 2100 (HTTP 422 beyond), so this is the universe offset pagination reaches.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for ascending in ("false", "true"):
        for i in range(pages):
            try:
                batch = _get_retry(f"{GAMMA}?closed=false&limit={PAGE}&offset={i * PAGE}"
                                   f"&order=volumeNum&ascending={ascending}")
            except urllib.error.HTTPError as e:
                if e.code == 422:
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
                if mid and mid not in seen:
                    seen.add(mid)
                    out.append(m)
            time.sleep(0.12)
    return out


def quote(m: dict) -> tuple[float, float, float, float] | str:
    """``(spread, tick, price, daily_volume)`` for one market, or a named refusal."""
    # `active` is the only flag that predicts a real book. Measured in SCANB-RESULTS: every leg
    # returning HTTP 404 from /book had active=False while enableOrderBook and acceptingOrders were
    # both True. The two obvious flags are misleading and this one tracks reality.
    if not m.get("active"):
        return "inactive"
    if not m.get("enableOrderBook"):
        return "no_order_book"
    try:
        spread = float(m["spread"])
        tick = float(m["orderPriceMinTickSize"])
        price = float(m["lastTradePrice"])
        volume = float(m["volumeNum"])
    except (KeyError, TypeError, ValueError):
        return "missing_quote_fields"
    if tick <= 0.0:
        return "no_tick_size"
    if not 0.0 <= price <= 1.0:
        return "price_out_of_range"
    # The exclusion Pass 26 found unenforced in every scanner. A one-tick spread on a 0.4c contract
    # is a 50% relative half-spread: an artefact of the tick grid, not an opportunity.
    if not CONSERVATIVE.price_in_band(price):
        return "longshot_out_of_band"
    age = days_since(m.get("startDate"))
    if age is None:
        return "no_start_date"
    return spread, tick, price, volume / age


# ---------------------------------------------------------------------------
# Gate M - the null gate for the realized-half-spread estimator
# ---------------------------------------------------------------------------

#: Horizons reported. 60 minutes is the registered decision horizon; the rest are the term structure,
#: which shows how fast information arrives rather than separating bounce from information.
HORIZONS = (1, 5, 15, 60)


def synthetic_market(n: int, *, half_spread: float, informed_frac: float, impact: float,
                     vol: float, drift: float, seed: int, stale: float = 0.0) -> list[float]:
    """A trade-price series with a controlled amount of informed flow.

    Each step: the true value moves exogenously, a trade prints on the bid or the ask, and **if that
    trade was informed the value then moves permanently in its direction**. So ``informed_frac`` and
    ``impact`` set how much of the spread gets taken, and the expected realized half-spread is
    ``half_spread - informed_frac * impact`` — which is what the estimator has to recover without
    being told any of it.
    """
    rng = random.Random(seed)
    value = 0.50
    prices: list[float] = []
    last: float | None = None
    for _ in range(n):
        # `stale` makes the series a **minute-sampled** one rather than a trade sequence: most
        # minutes carry no trade and repeat the last price. Measured on real Polymarket history:
        # 95.7% of minute-to-minute prices are unchanged and 59.6% of contributions are exactly
        # zero. A null world that trades every step does not resemble the data the estimator is
        # pointed at, which is the G14 failure Gate C committed -- power 1.000 on its own parser's
        # dialect and 0/26 on real text.
        if last is not None and rng.random() < stale:
            prices.append(last)
            continue
        value += rng.gauss(0.0, vol) + drift
        side = rng.choice((-1.0, 1.0))
        informed = rng.random() < informed_frac
        last = value + side * half_spread
        prices.append(last)
        if informed:
            value += side * impact
    return prices


#: ``(name, kwargs, maker_profits)``. ``maker_profits`` is the ground truth the estimator must
#: recover: False worlds are the **nulls** (informed flow takes the spread, and reporting a profit
#: there licenses spend on a losing strategy), True worlds are the **power** side (an estimator that
#: reports losses everywhere refuses everything and is worth nothing).
H = 0.01
WORLDS = (
    ("informed_strong      (impact 2x spread)", dict(informed_frac=1.0, impact=2 * H,
                                                     vol=0.0, drift=0.0), False),
    ("informed_breakeven   (impact = spread)", dict(informed_frac=1.0, impact=H,
                                                    vol=0.0, drift=0.0), False),
    ("toxic_minority       (10% at 15x)", dict(informed_frac=0.10, impact=15 * H,
                                               vol=0.0, drift=0.0), False),
    ("pure_bounce          (no information)", dict(informed_frac=0.0, impact=0.0,
                                                   vol=0.0, drift=0.0), True),
    ("walk_plus_bounce     (uninformed vol)", dict(informed_frac=0.0, impact=0.0,
                                                   vol=0.3 * H, drift=0.0), True),
    # The two worlds that match the regime the real measurement actually runs in. Added after the
    # real history was measured at 95.7% staleness, because the worlds above trade every step and
    # therefore validated the estimator on a process the data does not resemble (AXIOMS G14).
    ("STALE informed       (95.7% no-trade)", dict(informed_frac=1.0, impact=2 * H,
                                                   vol=0.0, drift=0.0, stale=0.957), False),
    ("STALE bounce         (95.7% no-trade)", dict(informed_frac=0.0, impact=0.0,
                                                   vol=0.0, drift=0.0, stale=0.957), True),
)

#: Diagnostic, not gated. A trending market with flow that does not predict the trend: the maker is
#: on the wrong side of the drift, which is genuine inventory risk rather than an estimator fault, so
#: pre-asserting a direction here would be asserting an answer.
DIAGNOSTIC = ("drift_uninformed     (trend, blind flow)",
              dict(informed_frac=0.0, impact=0.0, vol=0.1 * H, drift=0.02 * H))


def interval_verdict(ci: tuple[float, float] | None) -> str:
    """``"profit"`` / ``"loss"`` / ``"none"``. Three states, because two forced the first failure."""
    if ci is None:
        return "none"
    lo, hi = ci
    if lo > 0.0:
        return "profit"
    if hi < 0.0:
        return "loss"
    return "none"


def run_nulls(reps: int, n: int) -> int:
    from kairos.microstructure import realized_half_spread_ci, term_structure
    # One implementation, not two - the same import gateb.py makes, for the same reason. The first
    # version of this gate hard-coded `rate <= 0.05`, which is precisely the "invented tolerance"
    # every other gate here refuses.
    from kairos.nullworld import ALPHA, FPR_TAIL_ALPHA, POWER_FLOOR, _binomial_tail

    print("=" * 88)
    print("GATE M - NULL GATE for the realized half-spread")
    print("=" * 88)
    print("  The claim under test is maker PROFITABILITY, so the nulls are the worlds where")
    print("  informed flow takes the spread. Reporting a profit there is the failure that")
    print("  licenses spend on a losing strategy (PROTOCOL Gate M, amendment 2 of 2026-09-14).")
    print("  Verdicts are block-bootstrap INTERVALS, not point estimates: the first run of this")
    print("  gate failed because a point estimate forces a two-way call on a noisy quantity.")
    print(f"  half-spread {H} | {reps} replications x {n:,} trades | decision horizon 60m")

    print(f"\n  {'world':<42} {'R(60)':>9} {'profit':>8} {'loss':>7} {'none':>7} "
          f"{'tail':>7} {'truth':>7}")
    ok = True
    for name, kw, profits in WORLDS:
        calls: collections.Counter[str] = collections.Counter()
        points: list[float] = []
        for rep in range(reps):
            prices = synthetic_market(n, half_spread=H, seed=1000 + rep, **kw)
            ci = realized_half_spread_ci(prices, 60, seed=rep, draws=300)
            calls[interval_verdict(ci)] += 1
            if ci is not None:
                points.append((ci[0] + ci[1]) / 2.0)
        rate_profit = calls["profit"] / reps
        # Power worlds are gated on the floor; null worlds on the exact binomial tail of their
        # false-profit count, which is what "exceeds what chance allows" means here.
        tail = _binomial_tail(calls["profit"], reps, ALPHA)
        verdict = "PASS" if ((rate_profit >= POWER_FLOOR) if profits
                             else (tail >= FPR_TAIL_ALPHA)) else "FAIL"
        ok = ok and verdict == "PASS"
        print(f"  {name:<42} {median(points) if points else float('nan'):>+9.5f} "
              f"{rate_profit:>7.0%} {calls['loss'] / reps:>6.0%} {calls['none'] / reps:>6.0%} "
              f"{'-' if profits else f'{tail:7.4f}'} {str(profits):>7}  {verdict}")

    name, kw = DIAGNOSTIC
    prices = synthetic_market(n, half_spread=H, seed=7, **kw)
    ts = term_structure(prices, HORIZONS)
    print(f"  {name:<42} {ts[60]:>+9.5f}                          (diagnostic, not gated)")

    # The exhibit: the same estimator read at a single short horizon, which is what a gate written
    # without a term structure would have used. Information has not arrived by k=1, so R(1) still
    # looks like the half-spread in worlds where the maker is being run over.
    print(f"\n  EXHIBIT - a gate decided at R(1) instead of R(60):")
    misled = 0
    losing = sum(1 for _, _, p in WORLDS if not p)
    for name, kw, profits in WORLDS:
        if profits:
            continue
        prices = synthetic_market(n, half_spread=H, seed=99, **kw)
        ci1 = realized_half_spread_ci(prices, 1, seed=1, draws=300)
        if interval_verdict(ci1) == "profit":
            misled += 1
            print(f"      {name:<42} R(1) interval says PROFIT, truth is LOSS")
    print(f"      {misled} of {losing} losing worlds would have passed on a single short horizon")

    print(f"\n{'=' * 88}")
    print(f"  GATE M NULL GATE: {'PASSED' if ok else 'FAILED'}")
    if not ok:
        print("  The estimator does not separate the worlds. Fix it; do not tune the worlds (A8).")
        print("  No measurement may run.")
    else:
        print("  The estimator reports losses where flow is informed and the half-spread where it")
        print("  is not, and abstains rather than guessing when the sample cannot carry the call.")
        print(f"  Minimum usable observations per unit is set by this: below ~{n:,} the loss")
        print("  worlds return `none` rather than `loss`. `python scanm.py` is licensed.")
    print("=" * 88)
    return 0 if ok else 1


def flow_share_at_one_tick(rows: list[tuple[float, float, float, float]]) -> float:
    """Share of **flow** sitting in markets quoted at one tick, from ``(spread, tick, price, vol)``.

    The registered condition weights every market equally; the hypothesis is about flow, and the two
    disagree whenever wide spreads and volume are anti-correlated — which is the measured shape here
    (37.2% of markets at one tick carrying 77.4% of the volume). Reported alongside the registered
    statistic, never substituted for it (``CORRECTIONS.md`` Pass 28.1).
    """
    total = sum(v for _, _, _, v in rows)
    if total <= 0.0:
        return 0.0
    return sum(v for s, t, _, v in rows if s / t <= 1.0 + 1e-9) / total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=21)
    ap.add_argument("--nulls", action="store_true",
                    help="run Gate M's null gate for the realized-half-spread estimator")
    ap.add_argument("--reps", type=int, default=40)
    ap.add_argument("--trades", type=int, default=4000)
    args = ap.parse_args()

    if args.nulls:
        return run_nulls(args.reps, args.trades)

    print("=" * 88)
    print("GATE M.0 - MAKER DEAD-ON-ARRIVAL CHECK (is there room to quote)")
    print("=" * 88)
    print("  Registered before the number existed, WITH the expectation that it passes and that")
    print("  passing means very little. Adverse selection, queue position, competition and")
    print("  inventory risk are all excluded and all cut against. Rewards are excluded and cut for.")
    print(f"  floor ${FLOOR_ANNUAL:.2f}/yr = 10x the taker ceiling Gate 4.0 measured")
    print("  NOTHING IS TRADED OR QUOTED.")

    print(f"\n[1/2] Sweeping the open universe, both volume orderings...", flush=True)
    markets = open_universe(args.pages)
    census: collections.Counter[str] = collections.Counter()
    rows: list[tuple[float, float, float, float]] = []
    rewarded = 0
    for m in markets:
        q = quote(m)
        if isinstance(q, str):
            census[q] += 1
            continue
        rows.append(q)
        if m.get("rewardsMaxSpread"):
            rewarded += 1
    print(f"      {len(markets)} open markets swept")
    for key, count in census.most_common():
        print(f"      {key:<34} {count}")
    print(f"      {'in band, quotable, measured':<34} {len(rows)}")

    if not rows:
        print("\n  Nothing measurable. WITHHELD as apparatus, not as a finding (AXIOMS A1, G12).")
        return 0

    ticks = sorted(s / t for s, t, _, _ in rows)
    med_ticks = median(ticks)
    at_one_tick = sum(1 for x in ticks if x <= 1.0 + 1e-9)

    print(f"\n[2/2] Tick room and gross capture")
    print(f"  spread in ticks   p25 {ticks[len(ticks) // 4]:.1f} | median {med_ticks:.1f} | "
          f"p75 {ticks[3 * len(ticks) // 4]:.1f} | max {ticks[-1]:.1f}")
    print(f"  markets quoted at one tick (no room to improve) : {at_one_tick}/{len(rows)} "
          f"({at_one_tick / len(rows):.1%})")

    # The registered condition weights every market equally. The hypothesis is about *flow*, so the
    # same question asked of the flow is the one that matters and the two can disagree: a 2-page
    # sample of the volume head returned a median of 1.0 tick where the full universe returns 2.0.
    # Reported alongside, never substituted for the registered condition (see GATEM-RESULTS.md).
    share_stuck = flow_share_at_one_tick(rows)
    print(f"  SHARE OF FLOW sitting in one-tick markets       : {share_stuck:.1%} "
          f"- room and flow are anti-correlated if this is high")
    print(f"  markets advertising maker rewards               : {rewarded}/{len(rows)} "
          f"- an unmodelled revenue line that cuts FOR the hypothesis")

    # Gross capture per dollar of flow. `volumeNum` is assumed to be dollars; that is unverified, so
    # the alternative reading is reported rather than assumed away (AXIOMS A6, G3).
    flow = sum(v for _, _, _, v in rows) * 365.0
    captured = sum(CONSERVATIVE.maker_capture(s, p) / p * v * 365.0 for s, _, p, v in rows)
    rate = captured / flow if flow > 0 else 0.0
    print(f"  volume-weighted gross capture per $ of flow     : {rate:.4%}")
    print(f"  published annual flow across measured markets   : ${flow:,.0f}"
          f"  (volumeNum assumed dollars, UNVERIFIED)")
    required = FLOOR_ANNUAL / rate if rate > 0 else float("inf")
    print(f"  flow required to clear the floor                : ${required:,.0f}/yr"
          f"  = {required / flow:.6%} of it" if flow > 0 else "")

    # The ceiling restricted to markets an entrant can actually improve on. This is the honest
    # version of the same number: capture where there is room, not capture everywhere.
    with_room = [(s, t, p, v) for s, t, p, v in rows if s / t > 1.0 + 1e-9]
    room_flow = sum(v for _, _, _, v in with_room) * 365.0
    room_capture = sum(CONSERVATIVE.maker_capture(s, p) / p * v * 365.0 for s, _, p, v in with_room)
    print(f"  ...restricted to markets WITH tick room         : ${room_capture:,.0f}/yr "
          f"on ${room_flow:,.0f} of flow ({len(with_room)} markets)")

    print(f"\n{'=' * 88}\nVERDICT\n{'=' * 88}")
    room = med_ticks > 1.0 + 1e-9
    ceiling = captured
    print(f"  median spread            : {med_ticks:.1f} ticks  "
          f"-> {'room to improve the quote' if room else 'NO ROOM - one tick or less'}")
    print(f"  gross capture ceiling    : ${ceiling:,.0f}/yr at 100% of measured flow")
    print(f"  floor                    : ${FLOOR_ANNUAL:,.2f}/yr")

    if not room:
        print("\n  GATE M.0: REFUTED - no tick room.")
        print("  The median in-band market is already quoted at one tick, so an entrant cannot")
        print("  improve the quote and can only join the back of an existing queue. Spread")
        print("  capture is unavailable whatever its size. Class M closes.")
    elif ceiling <= FLOOR_ANNUAL:
        print("\n  GATE M.0: REFUTED - ceiling below the floor.")
        print("  Even capturing every dollar of measured flow, the gross spread does not beat the")
        print("  taker ceiling by an order of magnitude. The structural change did not change the")
        print("  structure.")
    else:
        print("\n  GATE M.0: NOT REFUTED.")
        print("  There is room to quote and the gross capture clears the floor. This licenses")
        print("  ONE thing: Gate M, a measurement of adverse selection and queue position on real")
        print("  trade data. It licenses no executor, no quoting and no capital (F3).")
        print("  The excluded terms are the whole of maker P&L. This number is not a profit")
        print("  estimate and may not be reported as one.")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
