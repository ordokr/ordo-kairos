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
    args = ap.parse_args()

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
