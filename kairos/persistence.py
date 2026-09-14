"""Subsidy persistence: succession, revision direction, and a hazard that can only be bounded.

``docs/PROTOCOL.md`` Class S. Gate M2 returned NOT REFUTED with **77% of the gross coming from the
maker rebate**, which makes the venue's willingness to keep paying the dominant term. This module
does **not** forecast that willingness. Polymarket publishes no treasury, no budget and no
intentions, and nothing here converts a private business decision into a measurement.

What it measures instead
------------------------

**Succession.** The API exposes each market's *current* ``feeType`` and its ``createdAt`` — never the
history of schedule assignment. So the only observable question is whether the markets carrying a
later version were created after the markets carrying an earlier one. :func:`separation_auc` answers
it non-parametrically, and it is able to answer **0.5**, which is the finding that voids the rest.

**Direction, separately from instability.** A *signed* mean of revision deltas averages a randomly
churning programme to approximately zero and reports stability. :func:`weighted_direction` answers
"did revisions cut the maker's take?"; :func:`weighted_instability` answers "did the terms move at
all?". The churn null world in ``gates.py`` passes the first and must fail the second, which is the
whole reason they are two functions.

**A bound, never an estimate.** Every live schedule is alive; observed withdrawals number **zero**.
:func:`rule_of_three` therefore returns an upper bound on the hazard — with zero events in ``n``
units the 95% bound on the per-unit probability is ``3/n`` — and there is deliberately no function in
this module that returns a survival probability.

.. warning::

   ``n`` is a **correlated** count. One decision withdraws every schedule at once, so summing
   schedule-months treats eleven consequences of a single choice as eleven independent trials and
   produces a bound far tighter than the evidence supports. Callers must report the programme-level
   count beside it and let the wider one govern (``CORRECTIONS.md`` Pass 34).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

__all__ = [
    "parse_schedule_version", "maker_take", "separation_auc", "rule_of_three",
    "annual_hazard_bound", "weighted_direction", "weighted_instability", "months_between",
    "take_pair",
    "SuccessionPair", "detect_succession",
]

#: Trailing ``_v<n>``. A family whose name merely contains a "v" is not a version.
_VERSION = re.compile(r"^(.+)_v(\d+)$")

#: Mean Gregorian month, in seconds.
SECONDS_PER_MONTH = 365.2425 * 86400.0 / 12.0

#: Cohorts below this cannot support a permutation test worth running.
MIN_COHORT = 5

#: Permutation replications for the succession test.
N_PERMUTATIONS = 2000


def parse_schedule_version(fee_type: str | None) -> tuple[str, int] | None:
    """``"sports_fees_v3" -> ("sports_fees", 3)``; an unsuffixed name is version **1**, not missing."""
    if not fee_type or not isinstance(fee_type, str):
        return None
    m = _VERSION.match(fee_type)
    if m:
        return m.group(1), int(m.group(2))
    return fee_type, 1


def maker_take(fee_rate: float, rebate_rate: float) -> float:
    """What a maker keeps per filled contract, stripped of the ``(p(1-p))^exponent`` price factor.

    Two schedules' takes are comparable **only at equal exponent** — see :func:`take_pair`. Nearly
    every live schedule is ``exponent: 1``, which is what makes the two sports schedules directly
    comparable despite differing taker fees, but ``crypto_15_min`` is live at ``exponent: 2`` and
    is not on the same scale as any of them.
    """
    if fee_rate < 0.0 or rebate_rate < 0.0:
        raise ValueError(f"rates must be non-negative, got {fee_rate!r} and {rebate_rate!r}")
    return fee_rate * rebate_rate


def take_pair(older: tuple[float, float, int],
              newer: tuple[float, float, int]) -> tuple[float, float]:
    """Takes for a revision, as ``(rate, rebateRate, exponent)`` each, refusing mismatched exponents.

    At differing exponents the products are not a smaller and a larger take; they are quantities in
    different units, and subtracting them produces a number with no meaning.
    """
    r0, b0, e0 = older
    r1, b1, e1 = newer
    if e0 != e1:
        raise ValueError(
            f"takes are not comparable across a price exponent change: {e0} -> {e1}. "
            f"The fee is rate x (p(1-p))^exponent, so the stripped products are in different units."
        )
    return maker_take(r0, b0), maker_take(r1, b1)


def _ranks(values: Sequence[float]) -> list[float]:
    """Midranks, so ties contribute exactly one half to the AUC."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mid = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = mid
        i = j + 1
    return out


def separation_auc(older: Sequence[float], newer: Sequence[float]) -> float | None:
    """``P(newer > older) + 0.5 P(tie)`` — 1.0 is clean succession, 0.5 is full interleaving.

    ``None`` when either cohort is empty: there is no statistic, which is not the same as 0.5.
    """
    n_a, n_b = len(older), len(newer)
    if n_a == 0 or n_b == 0:
        return None
    ranks = _ranks(list(older) + list(newer))
    r_newer = sum(ranks[n_a:])
    u = r_newer - n_b * (n_b + 1) / 2.0
    return u / (n_a * n_b)


def rule_of_three(n_units: int) -> float:
    """95% upper bound on a per-unit event probability given **zero** events in ``n_units``.

    Returns ``1.0`` below three units: the data then excludes nothing at all.
    """
    if n_units <= 0:
        raise ValueError(f"cannot bound a hazard with no observation, got {n_units!r}")
    return min(1.0, 3.0 / n_units)


def annual_hazard_bound(monthly_bound: float) -> float:
    """Compound a monthly bound to a year. A bound of 1.0 stays 1.0."""
    if not 0.0 <= monthly_bound <= 1.0:
        raise ValueError(f"a probability bound must lie in [0,1], got {monthly_bound!r}")
    return 1.0 - (1.0 - monthly_bound) ** 12


def _weighted(pairs: Sequence[tuple[float, float]], weights: Sequence[float],
              f) -> float | None:
    if len(pairs) != len(weights):
        raise ValueError(f"{len(pairs)} pairs against {len(weights)} weights")
    if any(w < 0.0 for w in weights):
        raise ValueError("weights must be non-negative")
    total = sum(weights)
    if total <= 0.0:
        return None
    return sum(w * f(old, new) for (old, new), w in zip(pairs, weights)) / total


def weighted_direction(pairs: Sequence[tuple[float, float]],
                       weights: Sequence[float]) -> float | None:
    """Weighted mean **signed** change in the maker's take. Negative means revisions cut it."""
    return _weighted(pairs, weights, lambda old, new: new - old)


def weighted_instability(pairs: Sequence[tuple[float, float]],
                         weights: Sequence[float]) -> float | None:
    """Weighted mean **relative magnitude** of change, which churn cannot average away."""
    def rel(old: float, new: float) -> float:
        if old <= 0.0:
            raise ValueError("instability is undefined where there was no subsidy to destabilise")
        return abs(new - old) / old

    return _weighted(pairs, weights, rel)


def months_between(t0: float, t1: float) -> float:
    """Elapsed months between two epoch seconds, floored at zero."""
    return max(0.0, (t1 - t0) / SECONDS_PER_MONTH)


@dataclass(frozen=True)
class SuccessionPair:
    family: str
    older: int
    newer: int
    auc: float
    p_value: float
    n_older: int
    n_newer: int


def detect_succession(cohorts: Mapping[tuple[str, int], Sequence[float]], *,
                      auc_floor: float, alpha: float, rng: random.Random,
                      n_permutations: int = N_PERMUTATIONS) -> list[SuccessionPair]:
    """Adjacent versions of one family whose creation dates are **separated**, not interleaved.

    Two hurdles, both required: the AUC must clear ``auc_floor``, and a label permutation must
    reject the hypothesis that the separation is chance. Either alone is too easy — a small cohort
    can reach AUC 1.0 by accident, and a large one can reject at AUC 0.55, which is interleaving.
    """
    if not 0.5 <= auc_floor <= 1.0:
        raise ValueError(f"auc_floor must lie in [0.5, 1.0], got {auc_floor!r}")
    families: dict[str, list[int]] = {}
    for family, version in cohorts:
        families.setdefault(family, []).append(version)

    found: list[SuccessionPair] = []
    for family, versions in sorted(families.items()):
        versions.sort()
        for older_v, newer_v in zip(versions, versions[1:]):
            older = list(cohorts[(family, older_v)])
            newer = list(cohorts[(family, newer_v)])
            if len(older) < MIN_COHORT or len(newer) < MIN_COHORT:
                continue
            auc = separation_auc(older, newer)
            if auc is None or auc < auc_floor:
                continue
            p = _permutation_p(older, newer, auc, rng, n_permutations)
            if p >= alpha:
                continue
            found.append(SuccessionPair(family, older_v, newer_v, auc, p, len(older), len(newer)))
    return found


def _permutation_p(older: Sequence[float], newer: Sequence[float], observed: float,
                   rng: random.Random, n_permutations: int) -> float:
    """Fraction of label shuffles reaching the observed separation, with the +1 correction.

    AUC depends only on ranks, so the ranks are computed once and the *labels* are permuted.
    """
    n_a, n_b = len(older), len(newer)
    ranks = _ranks(list(older) + list(newer))
    denom = n_a * n_b
    hits = 0
    for _ in range(n_permutations):
        rng.shuffle(ranks)
        u = sum(ranks[n_a:]) - n_b * (n_b + 1) / 2.0
        if u / denom >= observed:
            hits += 1
    return (hits + 1) / (n_permutations + 1)
