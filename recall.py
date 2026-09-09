"""Measure the matcher's RECALL — the number Gate C said it could not produce.

    python recall.py [--top 40]

Every conclusion drawn from ``scanc.py`` so far rests on an unmeasured quantity: how often the
matcher finds a cross-venue pair that really is one. Gate C measured **precision** exhaustively
(0.000 in nine null worlds) and stated plainly that it could not measure recall on real venue
phrasing. Two passes then drew conclusions from a near-zero verified count anyway — first "the
instrument is missing", then "the market is missing" — and AXIOMS G13 says those two look identical
from inside a blocked measurement.

Gebele et al. 2026 (`10.48550/arxiv.2601.01706`) aligned **100,000 events across ten venues** with a
semantic alignment framework and found **~6% concurrently dual-listed**. Against 4,156 Polymarket
markets that rate predicts a few hundred candidates. ``scanc.py`` found **3**. Either this venue pair
is unlike the ten Gebele studied, or the scope rule — exact content-token set equality — has recall
under two percent. **That is a measurable difference and this script measures it.**

**Method: a human screen the matcher cannot influence.** Candidate pairs are surfaced by token
overlap through an inverted index — deliberately *not* by any check the matcher makes, so a pair the
matcher would reject for date, threshold, source or modality reasons still appears. The pairs are
then adjudicated by reading the published rules. The matcher's verdict is recorded alongside but
takes no part in selection. This yields a **lower bound** on recall, which is all that is needed:
a low lower bound falsifies the "no fungible events" reading, and a high one confirms it.
"""

from __future__ import annotations

import argparse
import collections
import time

from kairos.crossvenue import kalshi_descriptor, polymarket_descriptor
from kairos.identity import compare_identities
from kairos.kalshi import fetch_events
from scanc import ascii_safe, polymarket_universe

#: Tokens appearing in more than this fraction of one venue's markets carry no discriminating
#: power and blow up the candidate lists ("will", "2026", "president"). Dropped from the index only
#: — never from the comparison, which is the matcher's business and not this script's.
STOP_FRACTION = 0.02

#: A candidate needs at least this many shared content tokens to be worth scoring.
MIN_SHARED = 2


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40, help="pairs to surface for adjudication")
    ap.add_argument("--pages", type=int, default=22)
    ap.add_argument("--kalshi-pages", type=int, default=200)
    args = ap.parse_args()

    print("=" * 96)
    print("MATCHER RECALL - the quantity every cross-venue conclusion has rested on and none measured")
    print("=" * 96)
    t0 = time.time()

    polys = [d for d in (polymarket_descriptor(m) for m in polymarket_universe(args.pages)) if d]
    kalshis = [d for d in (kalshi_descriptor(e, m)
                           for e in fetch_events(args.kalshi_pages)
                           for m in (e.get("markets") or [])) if d]
    print(f"  polymarket {len(polys)} | kalshi {len(kalshis)}")

    # Inverted index over Kalshi scope tokens, minus tokens too common to discriminate.
    freq: collections.Counter[str] = collections.Counter()
    for d in kalshis:
        freq.update(d.identity.scope)
    ceiling = max(1, int(len(kalshis) * STOP_FRACTION))
    index: dict[str, list[int]] = collections.defaultdict(list)
    for i, d in enumerate(kalshis):
        for token in d.identity.scope:
            if freq[token] <= ceiling:
                index[token].append(i)
    print(f"  index: {len(index)} discriminating tokens "
          f"({len(freq) - len(index)} dropped as too common)")

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
    print(f"  candidate pairs surfaced by token overlap: {len(scored)}")

    print(f"\n{'=' * 96}")
    print(f"TOP {args.top} BY TOKEN OVERLAP - for adjudication against the published rules")
    print("=" * 96)
    print("  The matcher's verdict is shown but took NO part in selection.\n")
    seen_pm: set[int] = set()
    shown = 0
    for score, pi, ki in scored:
        if pi in seen_pm:
            continue
        seen_pm.add(pi)
        p, k = polys[pi], kalshis[ki]
        verdict = compare_identities(p.identity, k.identity)
        kinds = sorted({r.split(":")[-1] if r.startswith("unrecoverable") else r
                        for r in verdict.refusals})
        print(f"  [{score:.2f}] PM  {ascii_safe(p.label)[:76]}")
        print(f"         KX  {ascii_safe(k.label)[:76]}")
        print(f"         matcher: {'PAIRED' if verdict.paired else 'refused'} "
              f"{'' if verdict.paired else '- ' + ', '.join(kinds)}")
        shown += 1
        if shown >= args.top:
            break

    print(f"\n  elapsed {time.time() - t0:.1f}s")
    print("=" * 96)
    print("  Adjudicate the list above by reading each pair's rules, then recall = (pairs the")
    print("  matcher PAIRED) / (pairs adjudicated as the same event). A low value falsifies the")
    print("  'these venues share no fungible events' reading; a high value confirms it.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
