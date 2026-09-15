"""``q_raw -> q_ref``: an *estimated* probability benchmark built from market information.

.. danger::

   **STATUS AFTER LOOK 3 (2026-09-08) — READ BEFORE USING ANYTHING HERE.**

   This module holds three components with **three different statuses**. Treating them as one thing
   is what made the Look-2 registration commit to deleting the whole file, which would have taken a
   live Class-B component with it:

   ===================== ============ =========================================================
   ``LogitRecalibration``  **REJECTED** This *is* ``C_logit``. On 1,966 fresh events (983 tested
                                       out of sample) it scored ``+0.00371`` — ``p = 0.0335``
                                       against a registered ``alpha = 0.025``, and 0.987% of the
                                       benchmark against a 1% materiality floor. Look #1's
                                       ``+0.01341`` was a **72% overestimate**. Do not put it in a
                                       Class A path.
   ``MarketBaseline``      **REJECTED** ``D_both``. Rejected at Gate 1 and never revived.
   ``SettlementTerms``     **ALIVE**    Not a Class A transformation here — the carry model
                                       ``census.py`` uses for **Class B**, where it *reverses the
                                       sign* on every long-dated negRisk group. Class B is
                                       untested, not refuted.
   ===================== ============ =========================================================

   The two rejected classes are **retained deliberately and are not re-exported from ``kairos``**.
   ``gate1.py`` needs them to reproduce Gates 1–2a and Looks 1–3; a result whose code has been
   deleted is an assertion rather than a result, and this workspace is not a git repository, so the
   deletion would be irreversible. ``tests/test_baseline.py`` enforces both halves: the rejected
   names are absent from the package surface, and only an allowlisted set of files may import them.

.. warning::

   ``q_ref`` is **not** "the market's belief" and **not** a "fair probability". Yu et al. 2022
   (`10.1145/3490486.3538347`) show equilibrium prediction-market prices converge to *different*
   weighted means of participants' beliefs depending on utility functions and even trading order -
   there is no uniquely recoverable latent belief behind a quote. This module produces the best
   frozen, out-of-sample probability benchmark constructible from market information at decision
   time. It is an estimator. It has uncertainty. It can be wrong, and it holds no epistemic
   privilege over the candidate forecaster (``docs/AXIOMS.md`` A2).

   **Symbol rename resolved 2026-09-09 (CORRECTIONS item 1).** ``q*`` is now ``q_ref``
   everywhere it means this benchmark. It was **not** applied blindly: ``kairos.legset`` uses
   ``q*`` for an unrelated quantity — the break-even non-exhaustiveness rate — and a mass rename
   would have silently corrupted it (E3).

   The **class** rename ``MarketBaseline`` -> ``MarketReference`` is declined rather than deferred.
   Look 3 rejected this hypothesis; the class survives only so Gates 1-2a and Looks 1-3 stay
   reproducible, and renaming a refuted artifact is churn that would also make every results doc's
   references stale (C9, C9a).

**Nothing here is validated.** Every transformation below must beat the raw quote out of sample in
the four-way ablation registered as ``docs/PROTOCOL.md`` Gate 1, or be deleted (AXIOMS C9).

The comparison that decides this project is *does the forecaster carry information beyond the
market*. The quoted price is a biased estimate of that, for reasons that are all monotone
distortions:

- **Settlement discounting.** Collateral is locked until oracle settlement, so a near-certain dollar
  is a delayed dollar and trades below its probability. Gebele & Matthes 2026 (arXiv 2605.31431)
  *recover* an implied discount term structure and find that adjusting for it explains **48-88%** of
  the near-certainty horizon gradient. Applying a known wedge is arithmetic; **obtaining the correct
  wedge is estimation** - it is maturity-dependent, time-varying, and altered by market architecture
  (NegRisk conversion, yield-bearing collateral). It is also partly an economic *funding friction*
  rather than a forecast error, which is why it must not be corrected here and then charged again in
  :mod:`kairos.costs` (AXIOMS B5).
- **Domain- and horizon-dependent calibration.** Le 2026 (arXiv 2602.19520), on **353M trades across
  429k Kalshi and Polymarket contracts**, fits *cell-level logistic recalibration slopes* and finds
  calibration varies with domain, time-to-resolution and trade size - with political markets showing
  persistent compression toward 50%. This module fits the same object: a two-parameter logistic
  recalibration in logit space. Le also finds roughly half the raw slope variation is estimation
  noise, so the default is the identity and a fitted slope has to earn its place.
- **Fee-induced favourite-longshot bias.** Whelan 2023 (Quantitative Finance,
  DOI 10.1080/14697688.2023.2257756) shows commercial prediction-market fee structures bend prices
  away from probabilities. Monotone, so the same recalibration absorbs it.

The evaluation design this supports is Hindcast's (Ye et al. 2026, arXiv 2607.14051), which scores
each forecast "against both what happened and the market's own price at t0". Scoring against
outcomes alone flatters any forecaster that has merely learned the base rate.

Order of operations is fixed: **undiscount settlement, then recalibrate**, with the recalibration
fitted on settlement-adjusted prices.

.. note::

   An earlier version of this docstring claimed that ordering the transformations this way means
   they "can't double-count". **That was wrong and is retracted.** Sequential code order removes
   ambiguity about *execution* order; it does not establish statistical orthogonality. The
   recalibration can still re-learn a distortion correlated with settlement horizon that the first
   transformation already tried to remove. Only the Gate-1 out-of-sample ablation can settle it: if
   settlement-only and settlement-plus-recalibration are indistinguishable OOS, one of them goes
   (``docs/AXIOMS.md`` C7).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

__all__ = [
    "BaselineError",
    "SettlementTerms",
    "LogitRecalibration",
    "MarketBaseline",
]

_EPS = 1e-9
DAYS_PER_YEAR = 365.0


class BaselineError(ValueError):
    """Raised when a baseline cannot be constructed from the inputs given."""


def _logit(p: float) -> float:
    p = min(max(p, _EPS), 1.0 - _EPS)
    return math.log(p / (1.0 - p))


def _expit(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass(frozen=True)
class SettlementTerms:
    """Cost of having capital locked from trade until oracle settlement."""

    days_to_settlement: float
    annual_wedge: float = 0.06

    def __post_init__(self) -> None:
        if self.days_to_settlement < 0.0:
            raise BaselineError(
                f"days_to_settlement must be non-negative, got {self.days_to_settlement!r}"
            )
        if self.annual_wedge < 0.0:
            raise BaselineError(f"annual_wedge must be non-negative, got {self.annual_wedge!r}")

    @property
    def discount_factor(self) -> float:
        """Present-value factor applied to the $1 payoff by the lock-up."""
        return 1.0 / (1.0 + self.annual_wedge * self.days_to_settlement / DAYS_PER_YEAR)

    def undiscount(self, price: float) -> float:
        """Recover the implied probability from a settlement-discounted price.

        A contract paying $1 at settlement with probability ``pi`` trades near
        ``pi * discount_factor``. Dividing it back out raises the price toward its probability,
        which is why "free money" in 97c contracts is mostly this and not mispricing.
        """
        if not 0.0 <= price <= 1.0:
            raise BaselineError(f"price must lie in [0, 1], got {price!r}")
        return min(1.0, price / self.discount_factor)


@dataclass(frozen=True)
class LogitRecalibration:
    """``q_ref = expit(intercept + slope * logit(q))`` - Le 2026's logistic recalibration.

    ``slope > 1`` expands prices away from 0.5, undoing the compression Le documents in political
    markets. ``slope == 1, intercept == 0`` is the identity and is the default: an unfitted baseline
    must not silently move prices.
    """

    intercept: float = 0.0
    slope: float = 1.0

    @property
    def is_identity(self) -> bool:
        return abs(self.intercept) < 1e-12 and abs(self.slope - 1.0) < 1e-12

    def apply(self, price: float) -> float:
        if not 0.0 <= price <= 1.0:
            raise BaselineError(f"price must lie in [0, 1], got {price!r}")
        if self.is_identity:
            return price
        return _expit(self.intercept + self.slope * _logit(price))

    @classmethod
    def fit(
        cls,
        prices: Sequence[float],
        outcomes: Sequence[float],
        *,
        max_iter: int = 100,
        tol: float = 1e-10,
    ) -> "LogitRecalibration":
        """Two-parameter logistic regression of outcome on ``logit(price)``, by Newton-Raphson.

        Returns the identity if the fit is degenerate (no variation in price, no variation in
        outcome, or a singular Hessian) rather than raising - a baseline that cannot be estimated
        should fall back to the quoted price, not to a fabricated correction.
        """
        if len(prices) != len(outcomes):
            raise BaselineError(
                f"prices and outcomes must be the same length, got "
                f"{len(prices)} and {len(outcomes)}"
            )
        if not prices:
            raise BaselineError("cannot fit a recalibration on zero observations")
        for o in outcomes:
            if o not in (0, 1, 0.0, 1.0):
                raise BaselineError(f"outcome {o!r} must be 0 or 1")

        xs = [_logit(p) for p in prices]
        ys = [float(o) for o in outcomes]
        if max(xs) - min(xs) < _EPS or min(ys) == max(ys):
            return cls()

        a, b = 0.0, 1.0
        for _ in range(max_iter):
            g0 = g1 = h00 = h01 = h11 = 0.0
            for x, y in zip(xs, ys):
                mu = _expit(a + b * x)
                r = y - mu
                w = mu * (1.0 - mu)
                g0 += r
                g1 += r * x
                h00 += w
                h01 += w * x
                h11 += w * x * x
            det = h00 * h11 - h01 * h01
            if abs(det) < 1e-14:
                return cls()
            da = (h11 * g0 - h01 * g1) / det
            db = (h00 * g1 - h01 * g0) / det
            a += da
            b += db
            if abs(da) < tol and abs(db) < tol:
                break
        if not (math.isfinite(a) and math.isfinite(b)):
            return cls()
        return cls(intercept=a, slope=b)


@dataclass(frozen=True)
class MarketBaseline:
    """An estimated probability benchmark from market information - ``q_ref``, not truth.

    Composition order is fixed: settlement first, recalibration second. Both default to no-ops, so
    an unconfigured baseline returns the quoted price unchanged, which is the correct behaviour for
    an estimator that has not yet earned its corrections out of sample.
    """

    recalibration: LogitRecalibration = LogitRecalibration()
    annual_wedge: float = 0.06

    def fair_probability(self, raw_mid: float, days_to_settlement: float = 0.0) -> float:
        """Map a quoted mid to the market's implied probability."""
        terms = SettlementTerms(days_to_settlement, self.annual_wedge)
        return self.recalibration.apply(terms.undiscount(raw_mid))

    @classmethod
    def fit(
        cls,
        prices: Sequence[float],
        outcomes: Sequence[float],
        days_to_settlement: Sequence[float],
        *,
        annual_wedge: float = 0.06,
    ) -> "MarketBaseline":
        """Fit the recalibration on settlement-adjusted prices.

        Fitting on raw prices and then applying both would obviously double-count. Doing the
        adjustment here removes that *particular* error - it does **not** prove the two corrections
        are statistically independent, which only the Gate-1 ablation can test.

        Callers must fit on events strictly prior to those they evaluate. This method cannot enforce
        that, so it is a protocol obligation (``docs/PROTOCOL.md`` Gate 1), and violating it
        produces an in-sample number that means nothing (AXIOMS A5).
        """
        if not (len(prices) == len(outcomes) == len(days_to_settlement)):
            raise BaselineError(
                f"prices, outcomes and days_to_settlement must be the same length, got "
                f"{len(prices)}, {len(outcomes)} and {len(days_to_settlement)}"
            )
        adjusted = [
            SettlementTerms(d, annual_wedge).undiscount(p)
            for p, d in zip(prices, days_to_settlement)
        ]
        return cls(
            recalibration=LogitRecalibration.fit(adjusted, outcomes),
            annual_wedge=annual_wedge,
        )

    def baseline_series(
        self, prices: Sequence[float], days_to_settlement: Sequence[float]
    ) -> list[float]:
        """Vectorised ``q_ref`` for a whole evaluation set - what to pass as ``skill_score`` baseline."""
        if len(prices) != len(days_to_settlement):
            raise BaselineError(
                f"prices and days_to_settlement must be the same length, got "
                f"{len(prices)} and {len(days_to_settlement)}"
            )
        return [self.fair_probability(p, d) for p, d in zip(prices, days_to_settlement)]
