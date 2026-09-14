"""Does the edge pay for the machine? A **Level-0 capacity screen**.

.. warning::

   Everything here is a **screening upper bound**, not an economic forecast. It may kill a
   candidate cheaply; it may not certify one. Capacity, cost and edge are all endogenous to
   deployed size: strategy performance declines with scale, impact is nonlinear, slow impact decay
   reduces apparent capacity (Landier et al. 2015; Chan 2022, `10.2139/ssrn.3911635`), and a
   misspecified impact model can turn expected profits into losses (Hey et al. 2023,
   `10.2139/ssrn.4465282`). A surviving candidate must be re-expressed as a profit-versus-size
   curve ``net_profit(size)`` - built when a candidate requires it, not before
   (``docs/AXIOMS.md`` D3, E1).

   Do **not** annualise a short sample as though opportunity frequency were stationary. Extrapolating
   173 games to a season is a scenario estimate. Label it as one.

An edge is not a business. The screen is::

    annual value ~ edge x capacity x frequency - execution costs - fixed costs

which can rank a **2% edge with $100k of capacity above a 15% edge you can fill for $20**. Ranking
by ROI or Sharpe cannot see that difference, and it is exactly the difference between a beautiful
backtest and money.

The motivating measurement is Cheng et al. 2026 (arXiv 2605.00864), who reconstructed 75M order-book
snapshots across 173 Polymarket NBA games: combinatorial arbitrage delivered a median **101 bps**,
but **76.9%** of opportunities were capped near **14.8 shares**. A 1% edge on 15 contracts is
roughly fifteen cents. :func:`worth_building` exists so that number gets computed before, not after,
someone spends a month on an executor.

This also encodes an operating constraint the literature is blunt about: research is a cost centre.
Prediction Arena (arXiv 2604.07355) found **research volume uncorrelated with returns**, and Page &
Siemroth 2017 (Games Econ. Behav.) found traders over-acquire information to the point of
**negative profits net of information costs**. So research spend belongs in ``annual_fixed_cost``,
where it subtracts, rather than being treated as free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

__all__ = [
    "EconomicsError",
    "StrategyEconomics",
    "rank_strategies",
    "effective_sample_size",
    "sufficient_evidence",
]


class EconomicsError(ValueError):
    """Raised when a strategy's economics are not well defined."""


@dataclass(frozen=True)
class StrategyEconomics:
    """Annualised economics of one strategy family.

    Attributes:
        name: Identifier.
        edge_per_contract: Expected profit per contract **after** spread, fees and settlement
            costs, in dollars (a $1-payoff contract, so 0.01 is a one-cent edge).
        fillable_contracts: Contracts actually fillable per opportunity at the quoted edge. Not
            top-of-book size that vanishes when you take it - measured fill size.
        opportunities_per_year: How often the opportunity appears.
        capital_required: Capital that must be posted and locked to run it.
        annual_fixed_cost: Infrastructure, data, and research - including your own time. Research
            belongs here because it is a cost, not an edge.
        hit_rate: Fraction of identified opportunities that actually execute. Latency, races and
            partial fills live here; the default of 1.0 is optimistic and should be measured.
    """

    name: str
    edge_per_contract: float
    fillable_contracts: float
    opportunities_per_year: float
    capital_required: float
    annual_fixed_cost: float = 0.0
    hit_rate: float = 1.0

    def __post_init__(self) -> None:
        for field_name in (
            "fillable_contracts",
            "opportunities_per_year",
            "capital_required",
            "annual_fixed_cost",
        ):
            if getattr(self, field_name) < 0.0:
                raise EconomicsError(
                    f"{field_name} must be non-negative, got {getattr(self, field_name)!r}"
                )
        if not 0.0 <= self.hit_rate <= 1.0:
            raise EconomicsError(f"hit_rate must lie in [0, 1], got {self.hit_rate!r}")

    @property
    def gross_annual_value(self) -> float:
        """Expected annual dollars before fixed costs."""
        return (
            self.edge_per_contract
            * self.fillable_contracts
            * self.opportunities_per_year
            * self.hit_rate
        )

    @property
    def net_annual_value(self) -> float:
        """Expected annual dollars after fixed costs. The number that decides."""
        return self.gross_annual_value - self.annual_fixed_cost

    @property
    def return_on_capital(self) -> float:
        """Net annual value per dollar of capital locked up.

        Returns ``inf`` for a strategy needing no capital, which is a modelling error rather than a
        free lunch - so callers should treat a non-finite result as "capital not characterised".
        """
        if self.capital_required <= 0.0:
            return float("inf")
        return self.net_annual_value / self.capital_required

    def required_opportunities_for(self, hurdle_annual: float) -> float:
        """How often this opportunity must recur per year to clear ``hurdle_annual``.

        The inverse of :attr:`net_annual_value` in ``opportunities_per_year``, and the instance's
        own frequency is deliberately **ignored** — the question is what the rate would have to be,
        not what it was guessed at.

        Reported because recurrence is the one input Gate 4.0 cannot measure: no price history has
        been fetched, and annualising a short sample as though opportunity frequency were stationary
        is exactly what ``docs/PROTOCOL.md`` Gate 4 forbids. Inverting an unmeasured term turns it
        into a dependency the reader can judge; inventing it would hide the assumption inside a
        dollar figure (AXIOMS A6, G3).

        Returns ``inf`` when no recurrence can ever clear the hurdle — a non-positive edge, or
        nothing fillable. That is not a large number, it is an impossibility, and callers must not
        render it as one.
        """
        per_opportunity = self.edge_per_contract * self.fillable_contracts * self.hit_rate
        shortfall = hurdle_annual + self.annual_fixed_cost
        if shortfall <= 0.0:
            return 0.0
        if per_opportunity <= 0.0:
            return float("inf")
        return shortfall / per_opportunity

    def worth_building(self, hurdle_annual: float) -> bool:
        """Whether net annual value clears an explicit hurdle.

        The hurdle should be what the same effort earns elsewhere, not zero. A strategy that nets
        $400/year is not a positive result just because $400 > $0.
        """
        return self.net_annual_value > hurdle_annual

    def summary(self) -> str:
        return (
            f"{self.name}: gross ${self.gross_annual_value:,.0f}/yr, "
            f"net ${self.net_annual_value:,.0f}/yr, "
            f"capital ${self.capital_required:,.0f}, "
            f"RoC {self.return_on_capital:.1%}"
            if self.capital_required > 0
            else (
                f"{self.name}: gross ${self.gross_annual_value:,.0f}/yr, "
                f"net ${self.net_annual_value:,.0f}/yr, capital unmodelled"
            )
        )


def rank_strategies(strategies: Iterable[StrategyEconomics]) -> list[StrategyEconomics]:
    """Sort by net annual value, descending. Deliberately not by edge, ROI, or Sharpe."""
    return sorted(strategies, key=lambda s: s.net_annual_value, reverse=True)


def effective_sample_size(
    cluster_sizes: Sequence[int], intracluster_correlation: float = 1.0
) -> float:
    """Independent-information count, not observation count.

    Twenty contracts on the same election are not twenty observations, and a hundred parameter
    mutations tested against one holdout are not a hundred confirmations. The standard design
    effect applies::

        n_eff = n / (1 + (mean_cluster_size - 1) * rho)

    The default ``rho = 1.0`` treats each cluster as one observation, which is the conservative
    reading and the right default when the correlation has not been measured.

    .. warning::

       **Planning heuristic only. Do not feed this to a significance calculation.** An earlier
       version of this docstring said it "should feed
       :func:`kairos.score.deflated_sharpe_ratio`"; that is retracted. The formula assumes one
       specific within-cluster dependence structure, ignores unequal cluster sizes, and cannot see
       dependence *across* nominal events arising from shared news regimes, common participants,
       common information sources, temporal structure, related resolution criteria, or market-wide
       liquidity shocks. Use it to decide whether an evaluation set is worth running. For inference,
       use paired score differences with block/cluster bootstrap - wild-cluster bootstrap when the
       number of clusters is small (``docs/AXIOMS.md`` C4, ``docs/PROTOCOL.md`` Gate 2).
    """
    if not cluster_sizes:
        raise EconomicsError("cannot compute effective sample size from zero clusters")
    if any(c <= 0 for c in cluster_sizes):
        raise EconomicsError(f"cluster sizes must be positive, got {list(cluster_sizes)!r}")
    if not 0.0 <= intracluster_correlation <= 1.0:
        raise EconomicsError(
            f"intracluster_correlation must lie in [0, 1], got {intracluster_correlation!r}"
        )
    n = float(sum(cluster_sizes))
    mean_size = n / len(cluster_sizes)
    return n / (1.0 + (mean_size - 1.0) * intracluster_correlation)


def sufficient_evidence(
    cluster_sizes: Sequence[int],
    *,
    required_effective_n: float,
    intracluster_correlation: float = 1.0,
) -> tuple[bool, str]:
    """Whether an evaluation set carries enough independent information to decide anything.

    Returns ``(ok, explanation)``. This replaces elapsed calendar time as the statistical criterion:
    a deadline is a project-management constraint, not evidence.
    """
    n_eff = effective_sample_size(cluster_sizes, intracluster_correlation)
    ok = n_eff >= required_effective_n
    return ok, (
        f"{sum(cluster_sizes)} observations in {len(cluster_sizes)} clusters "
        f"-> effective n {n_eff:.1f} vs required {required_effective_n:.1f}"
        + ("" if ok else " - INSUFFICIENT")
    )
