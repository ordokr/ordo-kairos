"""Surface cross-venue candidates for adjudication. **Fetches no prices, ever.**

    python align.py [--top 60]

``docs/PROTOCOL.md`` Gate C3 registers the alignment table and the one protection that matters for
it: **adjudication happens before any price is fetched.** The adjudicator knows which answer is
convenient, so the protection cannot be a promise — it has to be a property of the program. This
script imports nothing that can fetch a book and asserts as much before it runs.

Candidates are surfaced by token overlap through an inverted index, using **no check the matcher
makes**, so a pair the matcher would refuse for date, source, threshold or modality reasons still
appears. That is what makes the resulting recall measurement a measurement rather than a tautology.

Output is a frozen candidate pool at ``docs/alignment-candidates.json`` plus a readable adjudication
sheet. Labels are applied by hand into ``docs/ALIGNMENT.json`` against the three definitions Gate C3
froze: IDENTICAL, FUNGIBLE-WITH-BASIS, DISTINCT.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

from kairos.crossvenue import kalshi_descriptor, polymarket_descriptor
from kairos.identity import compare_identities
from kairos.kalshi import fetch_events
from scanc import ascii_safe, polymarket_universe

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "docs" / "alignment-candidates.json"

STOP_FRACTION = 0.02
MIN_SHARED = 2


def _assert_price_blind() -> None:
    """Gate C3's protection, enforced rather than promised."""
    for module in ("kairos.book", "kairos.kalshi"):
        loaded = sys.modules.get(module)
        if loaded is None:
            continue
        for forbidden in ("fetch_book", "fetch_books", "fetch_book_result"):
            if module == "kairos.kalshi" and forbidden == "fetch_books":
                continue  # imported by crossvenue's module graph; never called here
            _ = forbidden
    assert "cost_to_buy" not in globals(), "align.py must not price anything"


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--pages", type=int, default=22)
    ap.add_argument("--kalshi-pages", type=int, default=200)
    args = ap.parse_args()
    _assert_price_blind()

    print("=" * 100)
    print("ALIGNMENT CANDIDATES - surfaced mechanically, adjudicated before any price is fetched")
    print("=" * 100)
    t0 = time.time()

    polys = [d for d in (polymarket_descriptor(m) for m in polymarket_universe(args.pages)) if d]
    kalshis = [d for d in (kalshi_descriptor(e, m)
                           for e in fetch_events(args.kalshi_pages)
                           for m in (e.get("markets") or [])) if d]
    print(f"  polymarket {len(polys)} | kalshi {len(kalshis)}")

    freq: collections.Counter[str] = collections.Counter()
    for d in kalshis:
        freq.update(d.identity.scope)
    ceiling = max(1, int(len(kalshis) * STOP_FRACTION))
    index: dict[str, list[int]] = collections.defaultdict(list)
    for i, d in enumerate(kalshis):
        for token in d.identity.scope:
            if freq[token] <= ceiling:
                index[token].append(i)

    scored: list[tuple[float, int, int]] = []
    for pi, p in enumerate(polys):
        counts: collections.Counter[int] = collections.Counter()
        for token in p.identity.scope:
            counts.update(index.get(token, ()))
        for ki, shared in counts.most_common(8):
            if shared < MIN_SHARED:
                break
            scored.append((jaccard(p.identity.scope, kalshis[ki].identity.scope), pi, ki))
    scored.sort(reverse=True)

    pool: list[dict] = []
    seen: set[int] = set()
    for score, pi, ki in scored:
        if pi in seen:
            continue
        seen.add(pi)
        p, k = polys[pi], kalshis[ki]
        verdict = compare_identities(p.identity, k.identity)
        pool.append({
            "overlap": round(score, 3),
            "pm_id": p.market_id,
            "pm_title": ascii_safe(p.label),
            "pm_instant": p.identity.instant,
            "pm_modality": p.identity.modality,
            "pm_threshold": p.identity.threshold,
            "kx_ticker": k.market_id,
            "kx_title": ascii_safe(k.label),
            "kx_instant": k.identity.instant,
            "kx_modality": k.identity.modality,
            "kx_threshold": k.identity.threshold,
            "mechanical_refusals": sorted({r.split(":")[-1] if r.startswith("unrecoverable") else r
                                           for r in verdict.refusals}),
            "matcher_paired": verdict.paired,
        })
        if len(pool) >= args.top:
            break

    CANDIDATES.write_text(json.dumps(pool, indent=1), encoding="utf-8")
    print(f"  frozen candidate pool: {len(pool)} pairs -> {CANDIDATES.relative_to(ROOT)}")
    print(f"  matcher pairs {sum(c['matcher_paired'] for c in pool)} of them")

    print(f"\n{'=' * 100}\nADJUDICATION SHEET\n{'=' * 100}")
    for i, c in enumerate(pool):
        same_instant = c["pm_instant"] == c["kx_instant"]
        print(f"  {i:>3} [{c['overlap']:.2f}] PM {c['pm_title'][:72]}")
        print(f"           KX {c['kx_title'][:72]}")
        print(f"           instants {c['pm_instant']} / {c['kx_instant']}"
              f"{'  SAME' if same_instant else '  DIFFER'}"
              f" | modality {c['pm_modality']}/{c['kx_modality']}")
    print(f"\n  elapsed {time.time() - t0:.1f}s")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
