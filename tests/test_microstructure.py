"""The realized half-spread, which is what Gate M actually decides on.

``R(k) = mean over trades of D_t x (p_t - p_{t+k})`` — what a maker keeps per fill after the price
has moved for ``k`` minutes. It **already nets** gross spread capture against adverse selection, so
nothing here has to separate bounce from information: in a pure-bounce world a maker genuinely earns
the half-spread, and that is the answer rather than a bias to be removed.

The registration reached this the long way round (``docs/PROTOCOL.md`` Gate M, amendment
2026-09-14): the first estimator measured signed impact, whose bounce bias does **not** decay with
horizon and points in the direction that flatters the maker.
"""

from __future__ import annotations

import random
import unittest

from kairos.microstructure import (
    bootstrap_ci,
    contributions,
    realized_half_spread,
    realized_half_spread_ci,
    term_structure,
    tick_sign,
)


def bounce_series(n: int, *, value: float, half_spread: float, seed: int) -> list[float]:
    """Pure bid-ask bounce: a constant true value, trades landing randomly on bid or ask."""
    rng = random.Random(seed)
    return [value + rng.choice((-1.0, 1.0)) * half_spread for _ in range(n)]


def informed_series(n: int, *, half_spread: float, impact: float, seed: int) -> list[float]:
    """Every trade is informed: the value moves permanently in the direction of the trade."""
    rng = random.Random(seed)
    value, prices = 0.50, []
    for _ in range(n):
        side = rng.choice((-1.0, 1.0))
        prices.append(value + side * half_spread)
        value += side * impact
    return prices


class TestTickSign(unittest.TestCase):
    def test_an_uptick_is_a_buy_and_a_downtick_is_a_sell(self):
        self.assertEqual(tick_sign([1.0, 2.0, 3.0]), (0, 1, 1))
        self.assertEqual(tick_sign([3.0, 2.0, 1.0]), (0, -1, -1))

    def test_an_unchanged_price_carries_the_previous_direction(self):
        """The standard rule. A trade at the same price is not a trade with no side."""
        self.assertEqual(tick_sign([1.0, 2.0, 2.0, 1.0]), (0, 1, 1, -1))

    def test_leading_unchanged_prices_have_no_direction_to_carry(self):
        self.assertEqual(tick_sign([1.0, 1.0, 2.0]), (0, 0, 1))

    def test_degenerate_inputs_do_not_invent_a_direction(self):
        self.assertEqual(tick_sign([]), ())
        self.assertEqual(tick_sign([0.5]), (0,))


class TestPureBounceIsNotAdverseSelection(unittest.TestCase):
    """The discriminating null. A maker in a bounce-only world keeps exactly the half-spread."""

    def test_the_realized_half_spread_recovers_the_actual_half_spread(self):
        prices = bounce_series(20_000, value=0.50, half_spread=0.01, seed=11)
        self.assertAlmostEqual(realized_half_spread(prices, 1), 0.01, delta=0.0015)

    def test_it_does_not_decay_with_the_horizon(self):
        """The amendment's whole point: the bounce term is a constant offset, not a transient."""
        prices = bounce_series(20_000, value=0.50, half_spread=0.01, seed=12)
        for k in (1, 5, 15, 60):
            with self.subTest(k=k):
                self.assertAlmostEqual(realized_half_spread(prices, k), 0.01, delta=0.0020)

    def test_a_wider_spread_is_recovered_as_a_wider_spread(self):
        wide = bounce_series(20_000, value=0.50, half_spread=0.04, seed=13)
        self.assertAlmostEqual(realized_half_spread(wide, 1), 0.04, delta=0.004)


class TestInformedFlowTakesTheSpread(unittest.TestCase):
    def test_a_trade_that_predicts_a_permanent_move_costs_the_maker(self):
        """Every trade is a buy and the price keeps rising: the maker is run over."""
        prices = [1.0 + 0.01 * i for i in range(200)]
        r = realized_half_spread(prices, 10)
        self.assertIsNotNone(r)
        self.assertLess(r, 0.0, "a maker filled into a trend loses, and R must say so")

    def test_the_loss_grows_with_the_horizon_when_information_keeps_arriving(self):
        prices = [1.0 + 0.01 * i for i in range(400)]
        self.assertLess(realized_half_spread(prices, 60), realized_half_spread(prices, 1))


class TestUninformedRandomWalk(unittest.TestCase):
    def test_a_walk_with_no_spread_pays_the_maker_nothing(self):
        rng = random.Random(7)
        p, prices = 0.50, []
        for _ in range(20_000):
            p += rng.gauss(0.0, 0.002)
            prices.append(p)
        self.assertAlmostEqual(realized_half_spread(prices, 5), 0.0, delta=0.0006)


class TestIntervalInferenceNotAPointEstimate(unittest.TestCase):
    """Gate M's null gate failed on a point estimate, and the diagnosis was inference, not bias.

    Medians were right in every world; single replications landed on the wrong side of zero 20-27%
    of the time in genuinely losing worlds, and 47.5% in a world whose truth *is* zero. `R` is a
    sample mean of serially correlated observations, so it needs a block bootstrap (AXIOMS C4) and
    a third state: no verdict.
    """

    def test_a_bounce_world_is_called_profitable_with_the_whole_interval_above_zero(self):
        prices = bounce_series(20_000, value=0.50, half_spread=0.01, seed=21)
        lo, hi = realized_half_spread_ci(prices, 60, seed=1)
        self.assertGreater(lo, 0.0)
        self.assertLess(lo, hi)

    def test_a_strongly_informed_world_is_called_a_loss_given_enough_observations(self):
        prices = informed_series(100_000, half_spread=0.01, impact=0.02, seed=22)
        lo, hi = realized_half_spread_ci(prices, 60, seed=1, draws=200)
        self.assertLess(hi, 0.0, "the whole interval must sit below zero")

    def test_the_same_world_is_undetectable_at_a_fifth_of_the_data(self):
        """Measured, not assumed: 2/10 replications detect it at 20k, 10/10 at 100k.

        This is Gate 0's lesson in a new domain — a zero reading is uninterpretable without knowing
        the sample can carry the effect — and it sets the minimum observation count the real
        measurement must clear before any verdict is rendered.
        """
        prices = informed_series(20_000, half_spread=0.01, impact=0.02, seed=22)
        lo, hi = realized_half_spread_ci(prices, 60, seed=1, draws=200)
        self.assertGreater(hi, 0.0, "underpowered: the interval still straddles zero")

    def test_the_tick_test_attenuates_the_loss_it_is_measuring(self):
        """The instrument's error mode, measured rather than cited.

        With impact large relative to the spread, ``p_t - p_{t-1}`` is driven by the *previous*
        trade's permanent move as much as by this trade's side, so the tick test misclassifies —
        worst exactly when impact is largest. The measured ``R`` is pulled toward zero, which is the
        direction that **flatters the maker**. Every real ``R`` here is therefore an upper bound on
        what a maker keeps, and a REFUTED verdict is safer than a passing one.
        """
        true_r = 0.01 - 0.02          # half-spread earned, impact paid
        measured = realized_half_spread(informed_series(100_000, half_spread=0.01, impact=0.02,
                                                        seed=31), 60)
        self.assertLess(measured, 0.0, "the sign survives")
        self.assertGreater(measured, true_r, "but the magnitude is attenuated toward zero")

    def test_a_true_zero_world_straddles_zero_rather_than_picking_a_side(self):
        """The boundary case that broke the point estimate. No verdict is the honest answer."""
        prices = informed_series(20_000, half_spread=0.01, impact=0.01, seed=23)
        lo, hi = realized_half_spread_ci(prices, 60, seed=1)
        self.assertLess(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_the_interval_narrows_as_the_series_grows(self):
        short = realized_half_spread_ci(bounce_series(2_000, value=0.5, half_spread=0.01, seed=5),
                                        5, seed=1)
        long = realized_half_spread_ci(bounce_series(40_000, value=0.5, half_spread=0.01, seed=5),
                                       5, seed=1)
        self.assertLess(long[1] - long[0], short[1] - short[0])

    def test_contributions_from_many_markets_can_be_pooled_and_bootstrapped(self):
        """The real measurement pools across markets; no single market carries 100k observations."""
        pooled: list[float] = []
        for seed in range(40):
            pooled += contributions(bounce_series(3_000, value=0.5, half_spread=0.01, seed=seed), 5)
        self.assertGreater(len(pooled), 100_000)
        lo, hi = bootstrap_ci(pooled, seed=1, draws=200)
        self.assertLess(lo, 0.01)
        self.assertGreater(hi, 0.01)
        self.assertGreater(lo, 0.0, "pooled bounce is still a profit")

    def test_pooling_too_little_yields_no_interval(self):
        self.assertIsNone(bootstrap_ci([0.1, 0.2], seed=1))

    def test_no_measurement_yields_no_interval(self):
        self.assertIsNone(realized_half_spread_ci([0.5] * 50, 1, seed=1))
        self.assertIsNone(realized_half_spread_ci([0.5, 0.6], 60, seed=1))


class TestTermStructure(unittest.TestCase):
    def test_it_reports_every_requested_horizon(self):
        prices = bounce_series(2_000, value=0.50, half_spread=0.01, seed=3)
        ts = term_structure(prices, (1, 5, 15))
        self.assertEqual(sorted(ts), [1, 5, 15])

    def test_a_horizon_longer_than_the_series_is_none_not_zero(self):
        """Zero would read as 'measured no edge'. There is no measurement at all here."""
        self.assertIsNone(realized_half_spread([0.5, 0.6, 0.7], 50))
        self.assertIsNone(term_structure([0.5, 0.6, 0.7], (1, 50))[50])

    def test_a_series_with_no_direction_yields_no_measurement(self):
        self.assertIsNone(realized_half_spread([0.5] * 100, 1))

    def test_an_empty_series_yields_no_measurement(self):
        self.assertIsNone(realized_half_spread([], 1))


if __name__ == "__main__":
    unittest.main()
