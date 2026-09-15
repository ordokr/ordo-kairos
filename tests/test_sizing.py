"""Sizing is the principal cause of PnL, so it gets the sharpest tests.

Each test names the failure it prevents. The optimality tests drive the actual objective rather
than asserting a formula against itself, because a Kelly formula that is merely self-consistent is
worth nothing - the claim is that it maximises log growth, so the tests maximise log growth.
"""

from __future__ import annotations

import unittest

from kairos.costs import CostModel
from kairos.sizing import (
    ClampReason,
    RiskLimits,
    Side,
    growth_rate,
    kelly_fraction,
    size_position,
)


class TestKellyOptimality(unittest.TestCase):
    """The behaviour test: Kelly must actually maximise expected log growth."""

    def test_kelly_beats_every_other_fraction_on_a_grid(self):
        belief, cost = 0.60, 0.50
        f_star = kelly_fraction(belief, cost)
        self.assertAlmostEqual(f_star, 0.2, places=12)

        best = growth_rate(f_star, belief, cost)
        for i in range(1, 200):
            f = i / 200.0
            if abs(f - f_star) < 1e-9:
                continue
            self.assertLess(
                growth_rate(f, belief, cost),
                best,
                msg=f"fraction {f} beat Kelly {f_star}; the sizing rule is wrong",
            )

    def test_overbetting_is_strictly_worse_than_underbetting_by_the_same_margin(self):
        """Asymmetry is the whole reason fractional Kelly is safe and 2x Kelly is not."""
        belief, cost = 0.60, 0.50
        f_star = kelly_fraction(belief, cost)
        over = growth_rate(2 * f_star, belief, cost)
        under = growth_rate(0.5 * f_star, belief, cost)
        self.assertLess(over, under)

    def test_double_kelly_is_worse_than_not_betting_at_all(self):
        """The sharpest statement of why over-betting is not merely aggressive but wrong."""
        belief, cost = 0.60, 0.50
        flat = growth_rate(0.0, belief, cost)
        self.assertAlmostEqual(flat, 0.0, places=12)
        self.assertLess(
            growth_rate(2 * kelly_fraction(belief, cost), belief, cost),
            flat,
            msg="double Kelly should destroy more than the edge earns",
        )

    def test_no_bet_when_belief_does_not_clear_cost(self):
        self.assertEqual(kelly_fraction(0.50, 0.50), 0.0)
        self.assertEqual(kelly_fraction(0.49, 0.50), 0.0)

    def test_cost_at_or_above_payoff_is_refused_not_silently_zeroed(self):
        with self.assertRaises(ValueError):
            kelly_fraction(0.99, 1.0)
        with self.assertRaises(ValueError):
            kelly_fraction(0.99, 1.5)


class TestCostsDestroyNaiveEdges(unittest.TestCase):
    """The headline result: a small edge over the market price is not an edge at all."""

    def setUp(self):
        self.costs = CostModel()
        self.limits = RiskLimits()

    def test_two_point_edge_over_mid_is_refused(self):
        stake = size_position(
            p=0.52, mid=0.50, costs=self.costs, limits=self.limits, days_to_resolution=30.0
        )
        self.assertTrue(stake.abstained)
        self.assertEqual(stake.side, Side.ABSTAIN)
        self.assertIn(
            ClampReason.NEGATIVE_EDGE, [c.reason for c in stake.clamps]
        )

    def test_six_point_edge_over_mid_is_sized(self):
        stake = size_position(
            p=0.56, mid=0.50, costs=self.costs, limits=self.limits, days_to_resolution=30.0
        )
        self.assertEqual(stake.side, Side.YES)
        self.assertGreater(stake.fraction, 0.0)
        self.assertLessEqual(stake.fraction, self.limits.max_position_fraction)
        # Quarter-Kelly of the raw stake, exactly.
        self.assertAlmostEqual(stake.fraction, stake.raw_kelly * 0.25, places=12)

    def test_round_trip_drag_is_the_no_trade_band_width(self):
        drag = self.costs.round_trip_drag(0.50, 30.0)
        self.assertGreater(drag, 0.04, "conservative defaults should show ~5 points of drag")
        self.assertLess(drag, 0.07)

    def test_no_side_is_taken_when_market_is_overpriced(self):
        stake = size_position(
            p=0.30, mid=0.50, costs=self.costs, limits=self.limits, days_to_resolution=30.0
        )
        self.assertEqual(stake.side, Side.NO)
        self.assertGreater(stake.fraction, 0.0)

    def test_carry_makes_a_long_horizon_edge_disappear(self):
        """Same edge, same price, only the horizon changes."""
        near = size_position(
            p=0.545, mid=0.50, costs=self.costs, limits=self.limits, days_to_resolution=5.0
        )
        far = size_position(
            p=0.545, mid=0.50, costs=self.costs, limits=self.limits, days_to_resolution=900.0
        )
        self.assertFalse(near.abstained)
        self.assertTrue(far.abstained, "settlement wedge must eventually eat a thin edge")


class TestRefusals(unittest.TestCase):
    def setUp(self):
        self.costs = CostModel()
        self.limits = RiskLimits()

    def test_longshot_is_refused_by_price_band(self):
        stake = size_position(
            p=0.90, mid=0.02, costs=self.costs, limits=self.limits, days_to_resolution=30.0
        )
        self.assertTrue(stake.abstained)
        self.assertEqual([c.reason for c in stake.clamps], [ClampReason.PRICE_OUT_OF_BAND])

    def test_drawdown_halt_refuses_even_a_huge_edge(self):
        stake = size_position(
            p=0.99,
            mid=0.50,
            costs=self.costs,
            limits=self.limits,
            days_to_resolution=30.0,
            drawdown=0.25,
        )
        self.assertTrue(stake.abstained)
        self.assertEqual([c.reason for c in stake.clamps], [ClampReason.DRAWDOWN_HALT])

    def test_exhausted_gross_exposure_refuses(self):
        stake = size_position(
            p=0.99,
            mid=0.50,
            costs=self.costs,
            limits=self.limits,
            days_to_resolution=30.0,
            gross_exposure_used=0.50,
        )
        self.assertTrue(stake.abstained)
        self.assertEqual([c.reason for c in stake.clamps], [ClampReason.GROSS_EXPOSURE])

    def test_uncertainty_shrinkage_can_flip_a_trade_to_abstain(self):
        kwargs = dict(
            p=0.56, mid=0.50, costs=self.costs, limits=self.limits, days_to_resolution=30.0
        )
        self.assertFalse(size_position(**kwargs, p_stderr=0.0).abstained)
        self.assertTrue(
            size_position(**kwargs, p_stderr=0.05).abstained,
            "a forecast with real uncertainty must not be sized as if it were exact",
        )


class TestClampInvariants(unittest.TestCase):
    def test_clamps_only_ever_reduce(self):
        costs = CostModel()
        limits = RiskLimits()
        for p_i in range(1, 100):
            for mid_i in range(5, 96, 5):
                stake = size_position(
                    p=p_i / 100.0,
                    mid=mid_i / 100.0,
                    costs=costs,
                    limits=limits,
                    days_to_resolution=14.0,
                )
                for clamp in stake.clamps:
                    self.assertLessEqual(clamp.after, clamp.before + 1e-12)
                self.assertLessEqual(stake.fraction, limits.max_position_fraction + 1e-12)
                self.assertGreaterEqual(stake.fraction, 0.0)

    def test_never_takes_both_sides(self):
        costs = CostModel()
        limits = RiskLimits()
        for p_i in range(1, 100):
            stake = size_position(
                p=p_i / 100.0, mid=0.50, costs=costs, limits=limits, days_to_resolution=14.0
            )
            self.assertIn(stake.side, (Side.YES, Side.NO, Side.ABSTAIN))


class TestRiskLimitValidation(unittest.TestCase):
    def test_overbetting_kelly_is_refused_at_construction(self):
        with self.assertRaises(ValueError):
            RiskLimits(kelly_fraction=1.5)

    def test_position_cap_may_not_exceed_gross_cap(self):
        with self.assertRaises(ValueError):
            RiskLimits(max_position_fraction=0.6, max_gross_exposure=0.5)


if __name__ == "__main__":
    unittest.main()
