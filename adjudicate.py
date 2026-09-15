"""Build the alignment table: frozen group labels, then two mechanical guards.

    python adjudicate.py

``docs/PROTOCOL.md`` Gate C3 registers the table. This script makes it **reproducible** rather than
a shell artefact: the group labels are data, the guards are code, and running it regenerates
``docs/ALIGNMENT.json`` from the frozen candidate pool.

**Why the guards exist, measured rather than anticipated.** Adjudication is done per *event group* -
one semantic judgement covering N outcome pairs - because the same question answered thirteen times
drifts. But a group key names the **Kalshi** event, and the Polymarket side of a group is **not
homogeneous**. Applying a group label to every member asserts a homogeneity nobody checked, and the
first run of this table did exactly that. The measurement caught it: the pairs claiming the largest
edges were all mispairs.

===============================================  ===============================================
Polymarket                                       Kalshi
===============================================  ===============================================
Will a country leave **BRICS** in 2026?          Will another country leave **OPEC** in 2026?
**Trump** out as President by September 30?      **Gianni Infantino** out as President of **FIFA**
Morgan Wallen **Billboard** #1 top artist        Top artist on **Spotify**
Frankfurt **to score first**                     Mainz vs Frankfurt: **BTTS**
Balance of Power: **R Senate, D House**          **R-House, D-Senate**
===============================================  ===============================================

A +0.75 "edge" is not an arbitrage, it is a mispair announcing itself. **94 of 234 labelled pairs -
40% - failed subject containment.** So the group label is now treated as what it is: a claim that a
Kalshi event matches *some* Polymarket series, which every member must then earn.
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "docs" / "alignment-candidates.json"
GROUPS = ROOT / "docs" / "alignment-groups.json"
TABLE = ROOT / "docs" / "ALIGNMENT.json"

#: Groups whose outcome encoding cannot be verified mechanically. "R Senate, D House" against
#: "R-House, D-Senate" is an **inversion**; the party letters are one character each, so no token
#: rule sees it - and hand-adjudication got it wrong on the first pass. A group whose outcomes
#: cannot be checked is refused whole rather than trusted (AXIOMS A6).
UNVERIFIABLE = {"2026 Midterms: Congress Balance of Power?"}

STOP = frozenset({
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "will", "be", "is",
    "yes", "no", "before", "after", "win", "wins", "winner", "2026", "2027", "2028", "person",
    "next", "who", "what", "another", "any", "new",
})


def ascii_safe(text: str) -> str:
    return (text or "").encode("ascii", "replace").decode("ascii")


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", ascii_safe(text).lower())
            if t not in STOP and len(t) > 2}


def build() -> dict:
    pool = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    labels = {ascii_safe(k): v for k, v in json.loads(GROUPS.read_text(encoding="utf-8")).items()}

    table: list[dict] = []
    demoted: collections.Counter[str] = collections.Counter()
    kept = 0
    for i, c in enumerate(pool):
        full = ascii_safe(c["kx_title"])
        parts = full.split(" / ", 1)
        key = parts[0].strip()
        pm = tokens(c["pm_title"])

        def refuse(reason: str, tag: str) -> None:
            demoted[tag] += 1
            table.append({**c, "index": i, "label": "DISTINCT", "reason": reason})

        if key not in labels:
            refuse("group not adjudicated as the same question", "unadjudicated")
            continue
        if key in UNVERIFIABLE:
            refuse("outcome encoding cannot be verified mechanically", "unverifiable_outcome")
            continue
        # SUBJECT CONTAINMENT. The Kalshi event's own content tokens must all appear on the
        # Polymarket side. Its absence is what let BRICS pair with OPEC.
        absent = tokens(key) - pm
        if absent:
            refuse(f"group label does not hold for this pair: {sorted(absent)} absent from the "
                   f"Polymarket title", "subject_mismatch")
            continue
        outcome = tokens(parts[1]) if len(parts) == 2 else set()
        if outcome and not (outcome & pm):
            refuse("event matches but the OUTCOME does not - wrong contestant", "outcome_mismatch")
            continue
        kept += 1
        table.append({**c, "index": i, "label": "FUNGIBLE-WITH-BASIS", "reason": labels[key]})

    return {
        "registered": "docs/PROTOCOL.md Gate C3",
        "adjudicated": ("2026-09-09 by event group, from titles and settlement instants only; no "
                        "price data fetched. Group labels frozen against a 700-pair pool and "
                        "applied unchanged to the larger pool - no group relabelled after the "
                        "count was known."),
        "identical_count": 0,
        "identical_note": ("EMPTY. IDENTICAL requires a YES on one venue and a NO on the other to "
                           "pay $1 in EVERY state; even for pairs sharing a settlement instant to "
                           "the minute, the venues' resolution criteria could not be verified "
                           "equal from published text, so none is described as riskless (A6)."),
        "guards": dict(demoted),
        "aligned": kept,
        "pairs": table,
    }


def main() -> int:
    out = build()
    TABLE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"aligned {out['aligned']} | distinct {len(out['pairs']) - out['aligned']}")
    for tag, count in sorted(out["guards"].items(), key=lambda kv: -kv[1]):
        print(f"   demoted by {tag}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
