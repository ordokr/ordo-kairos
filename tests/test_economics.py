"""Economics tests.

The headline test computes the annual dollar value of the best-documented Polymarket arbitrage
opportunity from published numbers. It is the single most useful calculation in this repository,
because it takes about four lines and would have saved a month of executor work.
"""

from __future__ import annotations

import unittest

from kairos.economics import (
    EconomicsError,
    StrategyEconomics,
    effective_sample_size,
    rank_strategies,
    sufficient_evidence,
)

# Cheng et al. 2026 (arXiv 2605.00864), 173 Polymarket NBA games:
#   290 combinatorial episodes, median return 101 bps, 76.9% capped near 14.8 shares.
# An NBA regular season is 1,230 games.
NBA_GAMES_PER_SEASON = 1230
EPISODES_PER_GAME = 290 / 173


class TestPublishedArbitrageIsNotABusiness(unittest.TestCase):
    def test_polymarket_nba_combinatorial_arbitrage_nets_pocket_change(self):
        strategy = StrategyEconomics(
            name="polymarket-nba-combinatorial",
            edge_per_contract=0.0101,                       # 101 bps on a $1 contract
            fillable_contracts=14.8,                        # measured, not top-of-book
            opportunities_per_year=EPISODES_PER_GAME * NBA_GAMES_PER_SEASON,
            capital_required=5_000.0,
            annual_fixed_cost=0.0,                          # generously, before any engineering
        )
        self.assertLess(
            strategy.gross_annual_value,
            1_000.0,
            "the best-documented Polymarket arbitrage grosses under $1k/yr before costs",
        )
        self.assertGreater(strategy.gross_annual_value, 100.0)

    def test_it_fails_any_honest_hurdle_once_engineering_is_priced(self):
        strategy = StrategyEconomics(
            name="polymarket-nba-combinatorial",
            edge_per_contract=0.0101,
            fillable_contracts=14.8,
            opportunities_per_year=EPISODES_PER_GAME * NBA_GAMES_PER_SEASON,
            capital_required=5_000.0,
            annual_fixed_cost=2_000.0,      # data + hosting only; excludes any of your time
            hit_rate=0.5,                   # you will not win every 3.6-second race
        )
        self.assertLess(strategy.net_annual_value, 0.0)
        self.assertFalse(strategy.worth_building(hurdle_annual=0.0))


class TestCapacityBeatsEdge(unittest.TestCase):
    def test_a_small_edge_with_capacity_outranks_a_large_edge_without(self):
        """The ranking ROI and Sharpe cannot see."""
        big_edge_no_capacity = StrategyEconomics(
            name="15% edge, $20 fillable",
            edge_per_contract=0.15,
            fillable_contracts=20.0,
            opportunities_per_year=500.0,
            capital_required=1_000.0,
        )
        small_edge_real_capacity = StrategyEconomics(
            name="2% edge, $100k fillable",
            edge_per_contract=0.02,
            fillable_contracts=100_000.0,
            opportunities_per_year=50.0,
            capital_required=100_000.0,
        )
        self.assertGreater(big_edge_no_capacity.edge_per_contract,
                           small_edge_real_capacity.edge_per_contract)
        self.assertGreater(small_edge_real_capacity.net_annual_value,
                           big_edge_no_capacity.net_annual_value)
        self.assertEqual(
            rank_strategies([big_edge_no_capacity, small_edge_real_capacity])[0].name,
            "2% edge, $100k fillable",
        )

    def test_hit_rate_scales_value_linearly(self):
        base = dict(
            name="x", edge_per_contract=0.05, fillable_contracts=100.0,
            opportunities_per_year=1_000.0, capital_required=10_000.0,
        )
        full = StrategyEconomics(**base, hit_rate=1.0)
        half = StrategyEconomics(**base, hit_rate=0.5)
        self.assertAlmostEqual(half.gross_annual_value, full.gross_annual_value / 2, places=9)

    def test_fixed_costs_can_invert_the_ranking(self):
        cheap = StrategyEconomics("cheap", 0.01, 1_000.0, 100.0, 10_000.0, annual_fixed_cost=0.0)
        rich = StrategyEconomics("rich", 0.02, 1_000.0, 100.0, 10_000.0, annual_fixed_cost=5_000.0)
        self.assertGreater(rich.gross_annual_value, cheap.gross_annual_value)
        self.assertEqual(rank_strategies([rich, cheap])[0].name, "cheap")

    def test_hurdle_must_be_cleared_not_merely_positive(self):
        marginal = StrategyEconomics("marginal", 0.01, 100.0, 400.0, 5_000.0)
        self.assertGreater(marginal.net_annual_value, 0.0)
        self.assertFalse(marginal.worth_building(hurdle_annual=10_000.0))

    def test_invalid_economics_are_refused(self):
        with self.assertRaises(EconomicsError):
            StrategyEconomics("bad", 0.01, -1.0, 100.0, 1_000.0)
        with self.assertRaises(EconomicsError):
            StrategyEconomics("bad", 0.01, 1.0, 100.0, 1_000.0, hit_rate=1.5)


class TestRequiredRecurrenceInvertsTheUnmeasuredTerm(unittest.TestCase):
    """Gate 4.0. Three of the four inputs are measurable; recurrence is not.

    No price history has been fetched, so how often an opportunity reappears is unobserved, and
    PROTOCOL forbids annualising a short sample as though frequency were stationary. So the
    unmeasured term is **inverted**: report the recurrence the hurdle would require and let the
    reader judge it against the venue, rather than inventing a frequency and reporting dollars.
    """

    def _econ(self, **kw):
        base = dict(name="x", edge_per_contract=0.05, fillable_contracts=25.0,
                    opportunities_per_year=0.0, capital_required=25.0)
        base.update(kw)
        return StrategyEconomics(**base)

    def test_it_returns_the_rate_the_hurdle_arithmetically_requires(self):
        # 1000 / (0.05 * 25) = 800
        self.assertAlmostEqual(self._econ().required_opportunities_for(1000.0), 800.0, places=9)

    def test_at_the_returned_rate_the_strategy_exactly_meets_the_hurdle(self):
        """The property that matters: the answer round-trips through net_annual_value."""
        for hurdle in (0.0, 250.0, 1000.0, 1e6):
            for kw in ({}, {"annual_fixed_cost": 5000.0}, {"hit_rate": 0.4},
                       {"edge_per_contract": 0.002, "fillable_contracts": 3.0}):
                with self.subTest(hurdle=hurdle, **kw):
                    n = self._econ(**kw).required_opportunities_for(hurdle)
                    at_n = self._econ(opportunities_per_year=n, **kw)
                    self.assertAlmostEqual(at_n.net_annual_value, hurdle, places=6)

    def test_fixed_costs_raise_the_required_rate(self):
        bare = self._econ().required_opportunities_for(1000.0)
        loaded = self._econ(annual_fixed_cost=5000.0).required_opportunities_for(1000.0)
        self.assertGreater(loaded, bare)

    def test_an_optimistic_hit_rate_understates_it(self):
        perfect = self._econ(hit_rate=1.0).required_opportunities_for(1000.0)
        realistic = self._econ(hit_rate=0.5).required_opportunities_for(1000.0)
        self.assertAlmostEqual(realistic, 2.0 * perfect, places=9)

    def test_a_non_positive_edge_can_never_clear_any_positive_hurdle(self):
        """The case that actually obtains here. Every Class B group priced negative."""
        for edge in (0.0, -0.006):
            with self.subTest(edge=edge):
                n = self._econ(edge_per_contract=edge).required_opportunities_for(1000.0)
                self.assertEqual(n, float("inf"),
                                 "no amount of recurrence rescues a negative edge")

    def test_nothing_fillable_can_never_clear_either(self):
        self.assertEqual(self._econ(fillable_contracts=0.0).required_opportunities_for(1000.0),
                         float("inf"))

    def test_a_hurdle_already_cleared_requires_no_recurrence(self):
        self.assertEqual(self._econ(annual_fixed_cost=0.0).required_opportunities_for(0.0), 0.0)

    def test_it_ignores_the_frequency_the_instance_was_built_with(self):
        """Asking what the rate *would* have to be must not depend on the guess already in it."""
        a = self._econ(opportunities_per_year=0.0).required_opportunities_for(1000.0)
        b = self._econ(opportunities_per_year=99999.0).required_opportunities_for(1000.0)
        self.assertAlmostEqual(a, b, places=9)


class TestEffectiveSampleSize(unittest.TestCase):
    def test_twenty_contracts_on_one_election_are_one_observation(self):
        self.assertAlmostEqual(effective_sample_size([20]), 1.0, places=9)

    def test_twenty_independent_events_are_twenty_observations(self):
        self.assertAlmostEqual(effective_sample_size([1] * 20), 20.0, places=9)

    def test_clustering_shrinks_the_count(self):
        clustered = effective_sample_size([10] * 20)   # 200 rows, 20 events
        self.assertAlmostEqual(clustered, 20.0, places=9)
        self.assertLess(clustered, 200.0)

    def test_zero_correlation_recovers_the_raw_count(self):
        self.assertAlmostEqual(
            effective_sample_size([10] * 20, intracluster_correlation=0.0), 200.0, places=9
        )

    def test_partial_correlation_lands_between_the_bounds(self):
        n_eff = effective_sample_size([10] * 20, intracluster_correlation=0.5)
        self.assertGreater(n_eff, 20.0)
        self.assertLess(n_eff, 200.0)

    def test_sufficiency_check_reports_the_shortfall(self):
        ok, detail = sufficient_evidence([20] * 5, required_effective_n=30.0)
        self.assertFalse(ok)
        self.assertIn("INSUFFICIENT", detail)
        self.assertIn("100 observations in 5 clusters", detail)

    def test_sufficiency_passes_with_enough_independent_events(self):
        ok, detail = sufficient_evidence([1] * 200, required_effective_n=100.0)
        self.assertTrue(ok)
        self.assertNotIn("INSUFFICIENT", detail)

    def test_empty_and_invalid_inputs_are_refused(self):
        with self.assertRaises(EconomicsError):
            effective_sample_size([])
        with self.assertRaises(EconomicsError):
            effective_sample_size([0, 5])
        with self.assertRaises(EconomicsError):
            effective_sample_size([5], intracluster_correlation=2.0)


if __name__ == "__main__":
    unittest.main()
