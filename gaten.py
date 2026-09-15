"""Gate N.0: new-listing dynamics. Is there room in a book nobody has quoted yet?

    python gaten.py [--pages 20] [--books 150]

``docs/PROTOCOL.md`` Class N. Registered 2026-09-14, before this was written and before any
spread-by-age figure was computed.

Every maker result here is bounded by two constraints, and **both belong to established markets**:
one-tick pinning (77.4% of Polymarket flow, 73.4% of Kalshi) and queue position (Gate 3.0). A market
listed ten minutes ago has neither. This is the only remaining hypothesis that attacks the binding
constraint instead of varying something around it.

Two traps, both handled deliberately:

**``gatem.days_since`` floors at 1.0 day** and cannot be reused — the entire youngest bucket would
collapse into "1 day". :func:`age_hours` below is unfloored.

**Every prior gate counted a market with no two-sided book as a refusal.** For this hypothesis an
empty book is the **signal**, so it is retained and counted rather than discarded (AXIOMS G5).

Nothing here trades or quotes (F3).
"""

from __future__ import annotations

import argparse
import collections
import json
import time
from datetime import datetime, timezone

from kairos.book import fetch_book_result
from kairos.costs import CONSERVATIVE
from kairos.inference import weighted_share_ci
from kairos.polymarket import _get_retry
from gatem import GAMMA, PAGE, open_universe

#: Frozen in the registration. Moving a boundary after seeing a result converts the test into a
#: search over cut points (AXIOMS A8, C7).
BUCKETS = ((6.0, "<6h"), (24.0, "6-24h"), (24.0 * 7, "1-7d"),
           (24.0 * 30, "7-30d"), (float("inf"), ">30d"))

YOUNG = ("<6h", "6-24h")
MATURE = ">30d"

#: Below this share of flow the addressable market is under a twentieth of the venue.
CAPACITY_FLOOR = 0.05

MIN_YOUNG_MARKETS = 200


def age_sorted(pages: int, ascending: str) -> list[dict]:
    """Sweep the open universe ordered by **creation date**, newest or oldest first.

    ``open_universe`` orders by volume, and a market listed an hour ago has had no time to
    accumulate any — so a volume-ordered frame systematically under-samples the population this
    class is about. That is why the first run WITHHELD at 173 young markets from a sweep of 3,996
    (PROTOCOL Class N, Amendment 1).
    """
    out: list[dict] = []
    for i in range(pages):
        try:
            batch = _get_retry(
                f"{GAMMA}?closed=false&limit={PAGE}&offset={i * PAGE}"
                f"&order=createdAt&ascending={ascending}"
            )
        except Exception:                                    # noqa: BLE001 - apparatus, reported
            break
        if not isinstance(batch, list) or not batch:
            break
        out.extend(batch)
    return out


def universe(pages: int) -> list[dict]:
    """Volume sweep UNION age sweep from both ends, deduplicated by market id.

    A superset of every prior gate's frame, and still bounded by pagination: an apparatus ceiling,
    never a venue total (AXIOMS G12).
    """
    seen: set[str] = set()
    out: list[dict] = []
    for source in (open_universe(pages), age_sorted(pages, "false"), age_sorted(pages, "true")):
        for m in source:
            key = str(m.get("id") or m.get("conditionId") or "")
            if key and key not in seen:
                seen.add(key)
                out.append(m)
    return out


def age_hours(iso: str | None) -> float | None:
    """Hours since ``iso``, **unfloored**.

    ``gatem.days_since`` returns ``max(1.0, ...)`` days, which is correct for turning cumulative
    volume into a daily rate and useless here: it cannot tell ten minutes from twenty-three hours.
    """
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return max(0.0, (datetime.now(timezone.utc) - t).total_seconds() / 3600.0)


def signed_hours_until(iso: str | None) -> float | None:
    """Hours until ``iso``, **signed and unfloored** — negative once the date has passed.

    :func:`age_hours` floors at zero, which is right for an age and wrong for a deadline: every
    future end date collapses to 0.0 and the age/duration confound becomes unmeasurable. That
    defect produced a column of `-0h` in this gate's first measuring run.
    """
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return (t - datetime.now(timezone.utc)).total_seconds() / 3600.0


def bucket_of(hours: float) -> str:
    for edge, name in BUCKETS:
        if hours < edge:
            return name
    return BUCKETS[-1][1]


def classify(m: dict) -> tuple[str, float, float | None, float, float | None] | str:
    """``(bucket, age_h, half_spread|None, flow, ttr_h|None)`` or a named refusal.

    ``half_spread`` is ``None`` when the market has **no usable two-sided quote** — which is the
    signal for this gate, not a rejection.
    """
    if not m.get("active"):
        return "inactive"
    age = age_hours(m.get("createdAt"))
    if age is None:
        return "no_created_at"
    try:
        flow = float(m.get("volume24hr") or 0.0)
    except (TypeError, ValueError):
        return "bad_volume"
    ttr = signed_hours_until(m.get("endDate"))

    half = None
    try:
        spread = float(m["spread"])
        price = float(m["lastTradePrice"])
    except (KeyError, TypeError, ValueError):
        return bucket_of(age), age, None, flow, ttr
    if spread <= 0.0 or not (0.0 < price < 1.0):
        return bucket_of(age), age, None, flow, ttr
    if not CONSERVATIVE.price_in_band(price):
        return "longshot_out_of_band"
    half = spread / 2.0
    return bucket_of(age), age, half, flow, ttr


def flow_weighted_median(pairs: list[tuple[float, float]]) -> float | None:
    """Value at which cumulative weight crosses half. ``None`` when there is no weight."""
    total = sum(w for _, w in pairs)
    if total <= 0.0:
        return None
    cum = 0.0
    for v, w in sorted(pairs, key=lambda x: x[0]):
        cum += w
        if cum >= total / 2.0:
            return v
    return pairs[-1][0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--books", type=int, default=150)
    args = ap.parse_args()

    print("=" * 94)
    print("GATE N.0 - NEW-LISTING DYNAMICS (is there room in a book nobody has quoted?)")
    print("=" * 94)
    print("  Units: HOURS for age, PROBABILITY for half-spread, PERCENT OF FLOW for capacity.")
    print("  Weighting: by traded volume, not market count (Pass 28.1).")
    print(f"  Capacity floor: {CAPACITY_FLOOR:.0%} of flow in markets under 24h old.")
    print("  A market with NO two-sided book is RETAINED as signal, not refused (G5).")
    print("  NOTHING IS TRADED OR QUOTED")

    print(f"\n[1/3] Sweeping the open universe for age, spread and flow...", flush=True)
    census: collections.Counter[str] = collections.Counter()
    rows = []
    for m in universe(args.pages):
        r = classify(m)
        if isinstance(r, str):
            census[r] += 1
            continue
        rows.append((r, m))
        census["classified"] += 1
    for k, c in census.most_common(6):
        print(f"      {k:<26} {c}")

    order = [name for _, name in BUCKETS]
    by_bucket: dict[str, list] = {n: [] for n in order}
    for (b, age, half, flow, ttr), _m in rows:
        by_bucket[b].append((age, half, flow, ttr))

    young_n = sum(len(by_bucket[b]) for b in YOUNG)
    print(f"\n      markets in the two youngest buckets: {young_n}")
    if young_n < MIN_YOUNG_MARKETS:
        print(f"\n  WITHHELD - {young_n} against a floor of {MIN_YOUNG_MARKETS}. Apparatus, not")
        print("  evidence: nothing about new listings is licensed from this.")
        return 0

    total_flow = sum(f for (_b, _a, _h, f, _t), _m in rows)

    print(f"\n[2/3] By age bucket")
    print(f"      {'bucket':>8} {'markets':>8} {'no book':>9} {'flow $':>14} {'flow %':>8} "
          f"{'med half-spread':>16} {'med hrs to res':>15}")
    for b in order:
        v = by_bucket[b]
        if not v:
            print(f"      {b:>8} {'0':>8}")
            continue
        nobook = sum(1 for _, h, _, _ in v if h is None)
        bflow = sum(f for _, _, f, _ in v)
        quoted = [(h, f) for _, h, f, _ in v if h is not None]
        med = flow_weighted_median(quoted)
        ttrs = sorted(t for _, _, _, t in v if t is not None)
        med_ttr = ttrs[len(ttrs) // 2] if ttrs else float("nan")
        print(f"      {b:>8} {len(v):>8} {nobook / len(v):>8.1%} "
              f"{'$' + format(bflow, ',.0f'):>14} {bflow / total_flow if total_flow else 0:>7.1%} "
              f"{(f'{med:.6f}' if med is not None else 'no quoted flow'):>16} "
              f"{med_ttr:>14.0f}h")

    print(f"\n[3/3] The two registered primaries")
    young_flow = sum(f for b in YOUNG for _, _, f, _ in by_bucket[b])
    capacity = young_flow / total_flow if total_flow else 0.0

    young_q = [(h, f) for b in YOUNG for _, h, f, _ in by_bucket[b] if h is not None]
    mature_q = [(h, f) for _, h, f, _ in by_bucket[MATURE] if h is not None]
    y_med = flow_weighted_median(young_q)
    m_med = flow_weighted_median(mature_q)

    # Interval on the comparison, per Pass 36/37: share of YOUNG flow quoted wider than the
    # MATURE median. Straddling 50% means the two are not distinguished.
    ci = None
    if m_med is not None and young_q:
        ci = weighted_share_ci([h > m_med for h, _ in young_q], [f for _, f in young_q],
                               seed=20260914)
    wider = (sum(f for h, f in young_q if m_med is not None and h > m_med) /
             sum(f for _, f in young_q)) if young_q else 0.0

    print(f"      A  young (<24h) median half-spread : "
          f"{y_med if y_med is None else f'{y_med:.6f}'}")
    print(f"         mature (>30d) median half-spread: "
          f"{m_med if m_med is None else f'{m_med:.6f}'}")
    print(f"         young flow quoted WIDER than mature median: {wider:.1%}"
          + (f"   95% CI [{ci[0]:.1%}, {ci[1]:.1%}]" if ci else "   (no interval)"))
    print(f"      B  capacity: share of flow under 24h old : {capacity:.2%}"
          f"   (floor {CAPACITY_FLOOR:.0%})")

    young_nobook = sum(1 for b in YOUNG for _, h, _, _ in by_bucket[b] if h is None)
    young_total = sum(len(by_bucket[b]) for b in YOUNG)
    mature_nobook = sum(1 for _, h, _, _ in by_bucket[MATURE] if h is None)
    mature_total = max(1, len(by_bucket[MATURE]))
    print(f"      C  no two-sided book: young {young_nobook / max(1, young_total):.1%}  "
          f"vs mature {mature_nobook / mature_total:.1%}")

    # The declared confound, quantified rather than hidden.
    ages = [a for (_b, a, _h, _f, t), _m in rows if t is not None]
    ttrs = [t for (_b, _a, _h, _f, t), _m in rows if t is not None]
    if len(ages) > 2:
        ma, mt = sum(ages) / len(ages), sum(ttrs) / len(ttrs)
        num = sum((a - ma) * (t - mt) for a, t in zip(ages, ttrs))
        den = (sum((a - ma) ** 2 for a in ages) * sum((t - mt) ** 2 for t in ttrs)) ** 0.5
        print(f"      CONFOUND age vs time-to-resolution, correlation "
              f"{num / den if den else float('nan'):+.3f} on {len(ages)} markets")

    if args.books > 0:
        print(f"\n      Queue depth at touch (bounded subsample of {args.books})")
        depth: dict[str, list[float]] = collections.defaultdict(list)
        per = max(1, args.books // 3)
        taken: collections.Counter[str] = collections.Counter()
        for (b, _a, h, _f, _t), m in rows:
            if h is None or b not in (*YOUNG, MATURE) or taken[b] >= per:
                continue
            try:
                token = json.loads(m["clobTokenIds"])[0]
            except (KeyError, ValueError, TypeError, IndexError):
                continue
            book, _why = fetch_book_result(str(token))
            taken[b] += 1
            if book and book.bids and book.asks:
                depth[b].append((book.bids[0].size + book.asks[0].size) / 2.0)
            time.sleep(0.03)
        for b in (*YOUNG, MATURE):
            d = sorted(depth[b])
            if d:
                print(f"      {b:>8} n={len(d):<4} median touch size {d[len(d) // 2]:,.0f}")
            else:
                print(f"      {b:>8} no books sampled")

    print(f"\n{'=' * 94}\nVERDICT\n{'=' * 94}")
    if capacity < CAPACITY_FLOOR:
        print(f"  GATE N.0: REFUTED ON CAPACITY. Markets under 24h old carry {capacity:.2%} of")
        print(f"  flow against a registered floor of {CAPACITY_FLOOR:.0%}. Whatever the spread shows,")
        print("  a wide quote nobody trades against is not an opportunity. Flow arrives after the")
        print("  spread has already tightened. Class N closes.")
    elif ci is not None and ci[0] <= 0.5 <= ci[1]:
        print("  GATE N.0: NO VERDICT. Capacity clears, but the interval on the spread comparison")
        print("  straddles: young books are not shown to be quoted wider than mature ones.")
    elif ci is not None and ci[1] < 0.5 and young_nobook / max(1, young_total) <= \
            mature_nobook / mature_total:
        print("  GATE N.0: REFUTED. New listings are neither quoted wider nor emptier. The two")
        print("  constraints bind from the first minute. Class N closes.")
    else:
        print("  GATE N.0: NOT REFUTED on the cheap gate ONLY. Licenses a forward-tracking cohort")
        print("  study of new listings as a NEW registration. It licenses no profitability claim:")
        print("  adverse selection on fresh markets is UNMEASURED and plausibly worse, since the")
        print("  first trades against a new market are the best-informed ones.")

    print("\n  Unmodelled: adverse selection on new listings (cuts against), inventory risk with")
    print("  no other maker to exit to, the race to be first, and the age/duration confound above.")
    print("  One cross-sectional snapshot of surviving open markets only (Pass 34.6). F3 stands.")
    print("=" * 94)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
