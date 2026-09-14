"""Gate D.0: the dead-on-arrival check that runs *before* a convergence pipeline is built.

    python gated.py [--size 25] [--pairs N]

``docs/PROTOCOL.md`` Class C registers this as the first thing that runs, and registers the prior
against it in the same breath:

    Measure, on the existing 140-pair alignment table, the full four-crossing round-trip cost and
    the observed entry gap. If the largest observed gap does not exceed the median round-trip cost,
    Class C is refuted and no convergence pipeline is built.

**The arithmetic was expected to point this way before the number existed.** A convergence round
trip crosses four books; the Class B trade crossed two and let settlement pay the rest. From the
Class B run, of ``0.0834`` zero-fee cost, carry at 114 days accounts for roughly ``0.019``, leaving
about ``0.065`` of crossing cost for two legs -- so four crossings is around ``0.13`` against carry
savings of at most ``0.019``. On those figures Class C is worse than the hypothesis that already
failed. That is recorded in the registration so a negative result here is the expected outcome
rather than a surprise.

What this run is allowed to use
-------------------------------

Pairs come from the **adjudicated alignment table only**, never from their observed gap (Class C
data discipline 1). No price *history* is fetched for any pair, so no pair is spent (discipline 3).
The holding horizon is the registered 7 days, not the ~114-day median to settlement: holding for a
week instead of to resolution is the entire economic claim of this class, and charging settlement
carry here would refute it for a reason it does not assert (AXIOMS C7).

The unverified Kalshi fee is reported as a dependency, not assumed away
----------------------------------------------------------------------

``KALSHI_FEES`` is **unverified** -- the published schedule 429ed on 2026-09-09 -- and this verdict
is terminal, so an overstated fee would kill the class on an input nobody checked. The run therefore
reports the zero-fee verdict alongside the costed one. If the class is refuted at *zero* fees, the
unverified schedule cannot be the cause, and the verdict does not rest on it (AXIOMS A6, G3).

Nothing here trades, sizes a position, or touches capital (F3).
"""

from __future__ import annotations

import argparse
import collections
import json
import time
import urllib.error
from dataclasses import replace
from pathlib import Path
from statistics import median

from kairos.book import fetch_book_result
from kairos.costs import CONSERVATIVE
from kairos.crossvenue import gate_d0_verdict, round_trip_cost
from kairos.kalshi import KALSHI_FEES, fetch_books
from kairos.polymarket import _get_retry

GAMMA_MARKET = "https://gamma-api.polymarket.com/markets"

#: Frozen in the Class C registration (C11: a design variable is not held at one value).
SIZES = (5.0, 10.0, 25.0, 50.0)
HEADLINE_SIZE = 25.0

#: Registered holding horizon. Carry is charged over this, once, on the entry capital.
DAYS_HELD = 7.0


def aligned_pairs() -> list[dict]:
    """The adjudicated table's non-DISTINCT pairs, in table order.

    Table order, not gap order: selecting pairs by their observed deviation is the forking path the
    registration's data discipline exists to close.
    """
    table = json.loads((Path(__file__).resolve().parent / "docs" / "ALIGNMENT.json")
                       .read_text(encoding="utf-8"))
    return [t for t in table["pairs"] if t["label"] != "DISTINCT"]


def poly_handles(pm_id: str) -> tuple[str, str] | str:
    """``(yes_token, no_token)`` for a Polymarket market id, or a named refusal."""
    try:
        raw = _get_retry(f"{GAMMA_MARKET}/{pm_id}", timeout=20)
    except urllib.error.HTTPError as e:
        return f"http_{e.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        return "network"
    except json.JSONDecodeError:
        return "unparseable"
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return "unexpected_payload"
    if raw.get("closed"):
        return "closed_since_adjudication"
    try:
        tokens = json.loads(raw["clobTokenIds"])
        return str(tokens[0]), str(tokens[1])
    except (KeyError, ValueError, TypeError, IndexError):
        return "no_clob_tokens"


def best_round_trip(p_yes, p_no, k_yes, k_no, *, size, costs):
    """The better-gapped of the two hedge directions, or the reasons neither could be priced.

    Chosen by ``gross_gap`` because that is the quantity an entry decision is actually made on --
    not by cost, which would pick the cheapest trade rather than the one the hypothesis would take.
    """
    best = None
    reasons: list[str] = []
    for name, yes_book, no_book in (("yes_polymarket", p_yes, k_no),
                                    ("yes_kalshi", k_yes, p_no)):
        rt = round_trip_cost(yes_book, no_book, size=size, days_held=DAYS_HELD, costs=costs)
        if isinstance(rt, str):
            reasons.append(f"{name}:{rt}")
            continue
        if best is None or rt.gross_gap > best[1].gross_gap:
            best = (name, rt)
    return best, "|".join(reasons)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=float, default=HEADLINE_SIZE,
                    help="headline size the verdict is rendered at")
    ap.add_argument("--pairs", type=int, default=0, help="cap pairs (0 = the whole table)")
    args = ap.parse_args()

    free = replace(CONSERVATIVE, taker_fee_coeff=0.0)
    pairs = aligned_pairs()
    if args.pairs:
        pairs = pairs[:args.pairs]

    print("=" * 88)
    print("GATE D.0 - CLASS C DEAD-ON-ARRIVAL CHECK (four crossings vs the observed gap)")
    print("=" * 88)
    print("  The registration expects this to refute: ~0.13 of crossing cost against carry savings")
    print("  of at most ~0.019. Recorded before the number, not after it.")
    print(f"  holding horizon {DAYS_HELD:.0f}d (registered) | sizes "
          f"{'/'.join(f'{s:.0f}' for s in SIZES)} | headline {args.size:.0f}")
    print(f"  Kalshi fee schedule verified: {KALSHI_FEES.verified} "
          f"({KALSHI_FEES.note}) -> zero-fee verdict reported alongside")
    print("  NOTHING IS TRADED. Pairs come from the adjudicated table, never from their gap.")

    print(f"\n[1/2] Resolving {len(pairs)} aligned pairs to live books on both venues...",
          flush=True)
    census: collections.Counter[str] = collections.Counter()
    gaps: dict[float, list[float]] = {s: [] for s in SIZES}
    trips: dict[float, list[float]] = {s: [] for s in SIZES}
    free_trips: dict[float, list[float]] = {s: [] for s in SIZES}
    # The same measurement restricted to the registered tradeable band. Kept separate rather than
    # substituted: which of the two the verdict rests on is itself the finding (see the header).
    band_gaps: dict[float, list[float]] = {s: [] for s in SIZES}
    band_trips: dict[float, list[float]] = {s: [] for s in SIZES}
    rows: list[tuple[str, float, float, bool]] = []

    for t in pairs:
        handles = poly_handles(str(t["pm_id"]))
        if isinstance(handles, str):
            census[f"polymarket:{handles}"] += 1
            time.sleep(0.05)
            continue
        p_yes, why_y = fetch_book_result(handles[0])
        p_no, why_n = fetch_book_result(handles[1])
        k_yes, k_no, why_k = fetch_books(str(t["kx_ticker"]))
        # A failed fetch is not an empty book. Merging them would report a claim about venue depth
        # that was really a claim about the network (AXIOMS G5, the SCANB lesson).
        if p_yes is None or p_no is None:
            census[f"unfetchable_polymarket:{why_y if p_yes is None else why_n}"] += 1
            time.sleep(0.05)
            continue
        if k_yes is None or k_no is None:
            census[f"unfetchable_kalshi:{why_k}"] += 1
            time.sleep(0.05)
            continue

        priced = False
        for size in SIZES:
            best, reason = best_round_trip(p_yes, p_no, k_yes, k_no, size=size, costs=CONSERVATIVE)
            if best is None:
                census[f"size{size:.0f}:{reason.split(':')[-1]}"] += 1
                continue
            _, rt = best
            gaps[size].append(rt.gross_gap)
            trips[size].append(rt.cost)
            free_best, _ = best_round_trip(p_yes, p_no, k_yes, k_no, size=size, costs=free)
            if free_best is not None:
                free_trips[size].append(free_best[1].cost)
            in_band = (CONSERVATIVE.price_in_band(rt.yes_vwap)
                       and CONSERVATIVE.price_in_band(rt.no_vwap))
            if in_band:
                band_gaps[size].append(rt.gross_gap)
                band_trips[size].append(rt.cost)
            elif size == args.size:
                census["excluded_longshot_at_headline_size"] += 1
            if size == args.size:
                rows.append((str(t["pm_title"]).encode("ascii", "replace").decode()[:52],
                             rt.gross_gap, rt.cost, in_band))
            priced = True
        census["priced" if priced else "unpriced_at_every_size"] += 1
        time.sleep(0.05)

    for key, count in census.most_common():
        print(f"      {key:<44} {count}")

    print(f"\n[2/2] Four-crossing round trip vs the observed entry gap")
    print(f"  {'size':>6} {'n':>5} {'median gap':>12} {'largest gap':>13} "
          f"{'median trip':>13} {'zero-fee trip':>15}")
    for size in SIZES:
        n = len(trips[size])
        if not n:
            print(f"  {size:6.0f} {n:5d}   (nothing priced at this size)")
            continue
        print(f"  {size:6.0f} {n:5d} {median(gaps[size]):>+12.5f} {max(gaps[size]):>+13.5f} "
              f"{median(trips[size]):>13.5f} "
              f"{median(free_trips[size]) if free_trips[size] else float('nan'):>15.5f}")

    if rows:
        print(f"\n  widest gaps at size {args.size:.0f} (gap must exceed the round trip to survive)")
        print(f"  {'pair':<54} {'gap':>10} {'round trip':>12} {'in band':>8}")
        for title, gap, cost, in_band in sorted(rows, key=lambda r: -r[1])[:10]:
            print(f"  {title:<54} {gap:>+10.5f} {cost:>12.5f} {str(in_band):>8}")

    v = gate_d0_verdict(gaps=gaps[args.size], round_trips=trips[args.size])
    v_free = gate_d0_verdict(gaps=gaps[args.size], round_trips=free_trips[args.size])
    v_band = gate_d0_verdict(gaps=band_gaps[args.size], round_trips=band_trips[args.size])

    print(f"\n{'=' * 88}\nVERDICT\n{'=' * 88}")
    print(f"  pairs priced at size {args.size:.0f} : {v.pairs}")
    if v.largest_gap is None:
        print("  No pair could be priced on both venues, so there is no verdict to render.")
        print("  'Not enough evidence' is not 'no effect' (AXIOMS A1). Class C stays registered")
        print("  and untested; the honest next move is to diagnose the apparatus, not the class.")
        print("=" * 88)
        return 0

    print(f"  largest observed gap        : {v.largest_gap:+.5f}")
    print(f"  median four-crossing trip   : {v.median_round_trip:.5f}")
    print(f"  ...at zero fees             : "
          f"{v_free.median_round_trip if v_free.median_round_trip is not None else float('nan'):.5f}"
          f"  -> {v_free.verdict}")
    print(f"\n  as measured (no band)            : {v.verdict}  "
          f"(n={v.pairs}, largest gap {v.largest_gap:+.5f})")
    if v_band.largest_gap is None:
        print(f"  inside the registered band       : NO VERDICT (n={v_band.pairs})")
    else:
        print(f"  inside the registered band       : {v_band.verdict}  "
              f"(n={v_band.pairs}, largest gap {v_band.largest_gap:+.5f}, "
              f"median trip {v_band.median_round_trip:.5f})")
    print(f"  longshot pairs excluded by the band: "
          f"{census['excluded_longshot_at_headline_size']}")
    if v.verdict != v_band.verdict:
        print("\n  THE TWO DISAGREE. PROTOCOL's market-selection preconditions exclude longshots")
        print("  'at every gate', but price_in_band is enforced only in kairos.gate and")
        print("  kairos.sizing - no scanner in this repo applies it, scanb.py and scanc.py")
        print("  included. So the banded row is the protocol-compliant reading and the unbanded")
        print("  row is what every prior Class B measurement here actually did. Both are")
        print("  reported; neither is quietly chosen (AXIOMS A6, G3).")

    print(f"\n  GATE D.0 (as measured): {v.verdict}")
    if v.verdict == "REFUTED":
        print("  The largest gap the table offers does not exceed the median cost of crossing four")
        print("  books to harvest it. Per the registered decision rule, Class C is refuted before")
        print("  it is built: no convergence pipeline, no null gate, no history fetched.")
        if v_free.verdict == "REFUTED":
            print("  Refuted at zero fees too, so the unverified Kalshi schedule is not the cause.")
        else:
            print("  NOTE: not refuted at zero fees. The verdict depends on an unverified fee")
            print("  coefficient and must not be announced as terminal until it is checked (A6).")
    else:
        print("  The largest gap exceeds the median round trip, so the cheap falsifier does not")
        print("  kill the class. This licenses Gate D (the convergence null gate) and nothing")
        print("  else -- it is not a candidate, and no history may be fetched until Gate D passes.")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
