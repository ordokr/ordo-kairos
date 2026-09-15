"""Delta-neutral funding carry, and the liquidation that pays for it.

``docs/PROTOCOL.md`` Class F. The carry is not arbitrage — it is compensation for bearing the risk
that an upward move breaches the short perpetual's margin while the funding column still looks
perfect. An estimator that sums funding without modelling that breach measures the premium and
ignores the risk it is paid for, which is the whole reason Gate F exists.
"""

from __future__ import annotations

import unittest

from kairos.carry import deployed_capital, liquidation_move, naive_carry, simulate

FEE = 0.0005          # taker, per crossing
FLAT = [0.0] * 100    # price path that does not move


class TestLiquidationThreshold(unittest.TestCase):
    def test_one_times_leverage_needs_almost_a_doubling_to_breach(self):
        self.assertAlmostEqual(liquidation_move(1.0), 0.995, places=9)

    def test_five_times_leverage_breaches_on_a_twenty_percent_move(self):
        self.assertAlmostEqual(liquidation_move(5.0), 0.195, places=9)

    def test_ten_times_breaches_on_ten_percent(self):
        self.assertAlmostEqual(liquidation_move(10.0), 0.095, places=9)

    def test_more_leverage_always_breaches_sooner(self):
        moves = [liquidation_move(x) for x in (1.0, 2.0, 3.0, 5.0, 10.0)]
        self.assertEqual(moves, sorted(moves, reverse=True))

    def test_leverage_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            liquidation_move(0.5)

    def test_leverage_so_high_that_margin_is_already_gone_is_refused(self):
        with self.assertRaises(ValueError):
            liquidation_move(500.0, maintenance=0.005)


class TestDeployedCapital(unittest.TestCase):
    """Capital is spot notional PLUS perp margin. Quoting carry against notional alone is the
    single largest inflation vector in the public numbers."""

    def test_unlevered_locks_two_units_per_one_of_notional(self):
        self.assertAlmostEqual(deployed_capital(1.0), 2.0, places=9)

    def test_leverage_reduces_locked_capital(self):
        self.assertAlmostEqual(deployed_capital(5.0), 1.2, places=9)
        self.assertAlmostEqual(deployed_capital(10.0), 1.1, places=9)

    def test_it_never_falls_below_the_spot_leg(self):
        self.assertGreater(deployed_capital(1000.0), 1.0)


class TestSimulateUnbreached(unittest.TestCase):
    def test_positive_funding_on_a_flat_path_earns_funding_less_four_crossings(self):
        f = [0.0001] * 100
        r = simulate(f, FLAT, leverage=5.0, taker_fee=FEE)
        self.assertFalse(r.liquidated)
        self.assertAlmostEqual(r.pnl, sum(f) - 4 * FEE, places=12)

    def test_negative_funding_is_paid_by_the_holder(self):
        r = simulate([-0.0001] * 100, FLAT, leverage=5.0, taker_fee=FEE)
        self.assertLess(r.pnl, 0.0)

    def test_the_hedge_nets_price_moves_out_when_margin_survives(self):
        """Up then back down, never breaching: P&L must be funding less costs, not path-dependent."""
        path = [0.01] * 5 + [-0.01] * 5 + [0.0] * 90
        f = [0.0001] * 100
        r = simulate(f, path, leverage=1.0, taker_fee=FEE)
        self.assertFalse(r.liquidated)
        self.assertAlmostEqual(r.pnl, sum(f) - 4 * FEE, places=12)

    def test_leverage_raises_return_on_capital_when_nothing_breaches(self):
        f = [0.0001] * 100
        low = simulate(f, FLAT, leverage=1.0, taker_fee=FEE)
        high = simulate(f, FLAT, leverage=10.0, taker_fee=FEE)
        self.assertAlmostEqual(low.pnl, high.pnl, places=12, msg="same P&L per unit notional")
        self.assertGreater(high.return_on_capital, low.return_on_capital,
                           "but less capital locked, so a higher return on it")


class TestSimulateBreached(unittest.TestCase):
    """The discriminating case: the funding column looks perfect right up until the breach."""

    def test_an_upward_move_past_the_threshold_liquidates_the_short_leg(self):
        path = [0.03] * 10 + [0.0] * 90      # +30% cumulative, well past 5x's 19.5%
        r = simulate([0.0001] * 100, path, leverage=5.0, taker_fee=FEE)
        self.assertTrue(r.liquidated)
        self.assertLess(r.periods_held, 100)

    def test_the_same_path_survives_at_lower_leverage(self):
        path = [0.03] * 10 + [0.0] * 90
        self.assertTrue(simulate([0.0001] * 100, path, leverage=5.0, taker_fee=FEE).liquidated)
        self.assertFalse(simulate([0.0001] * 100, path, leverage=1.0, taker_fee=FEE).liquidated)

    def test_liquidation_costs_the_penalty_and_stops_the_carry(self):
        """Spot gain offsets the lost margin; what is not recovered is penalty, fees, and the
        carry never earned after the breach."""
        path = [0.03] * 10 + [0.0] * 90
        f = [0.0001] * 100
        live = simulate(f, path, leverage=5.0, taker_fee=FEE, penalty=0.01)
        survived = simulate(f, FLAT, leverage=5.0, taker_fee=FEE, penalty=0.01)
        self.assertLess(live.pnl, survived.pnl,
                        "being liquidated must cost more than never being liquidated")

    def test_the_overshoot_past_the_trigger_is_not_credited(self):
        """The defect that failed Gate F's first null gate.

        A discrete period can jump far past the liquidation trigger. Crediting the spot leg at that
        overshot price paid the whole jump while losing only the fixed margin, manufacturing a
        profit out of a liquidation. Exchanges liquidate continuously; nobody keeps the overshoot,
        so a violent breach must not pay better than a marginal one.
        """
        f = [0.0001] * 100
        marginal = [0.20] + [0.0] * 99      # just past 5x's 19.5% trigger
        violent = [0.80] + [0.0] * 99       # far past it
        a = simulate(f, marginal, leverage=5.0, taker_fee=FEE, penalty=0.01)
        b = simulate(f, violent, leverage=5.0, taker_fee=FEE, penalty=0.01)
        self.assertTrue(a.liquidated and b.liquidated)
        self.assertAlmostEqual(a.pnl, b.pnl, places=12,
                               msg="a bigger breach must not pay more than a smaller one")

    def test_a_breach_is_always_a_loss_on_the_position(self):
        """Residue is maintenance + penalty + a crossing, never a gain."""
        r = simulate([0.0] * 100, [0.30] + [0.0] * 99, leverage=5.0, taker_fee=FEE, penalty=0.01)
        self.assertTrue(r.liquidated)
        self.assertLess(r.pnl, 0.0)

    def test_a_larger_penalty_costs_more(self):
        path = [0.03] * 10 + [0.0] * 90
        cheap = simulate([0.0001] * 100, path, leverage=5.0, taker_fee=FEE, penalty=0.001)
        dear = simulate([0.0001] * 100, path, leverage=5.0, taker_fee=FEE, penalty=0.05)
        self.assertGreater(cheap.pnl, dear.pnl)


class TestTheNaiveExhibit(unittest.TestCase):
    """Why the gate exists at all."""

    def test_the_naive_sum_reports_the_same_number_whether_or_not_you_were_liquidated(self):
        f = [0.0001] * 100
        crash = [0.03] * 10 + [0.0] * 90
        self.assertAlmostEqual(naive_carry(f, taker_fee=FEE), naive_carry(f, taker_fee=FEE),
                               places=12)
        real_crash = simulate(f, crash, leverage=5.0, taker_fee=FEE, penalty=0.01)
        self.assertTrue(real_crash.liquidated)
        self.assertGreater(naive_carry(f, taker_fee=FEE), real_crash.pnl,
                           "the naive sum is blind to the breach that decides the trade")

    def test_it_matches_the_real_simulation_only_when_nothing_breaches(self):
        f = [0.0001] * 100
        self.assertAlmostEqual(naive_carry(f, taker_fee=FEE),
                               simulate(f, FLAT, leverage=5.0, taker_fee=FEE).pnl, places=12)


if __name__ == "__main__":
    unittest.main()
