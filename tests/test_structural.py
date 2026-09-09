"""Class B: the arbitrage-free worlds must really be arbitrage-free, and the refusals must bite.

A null world that quietly contains the thing it claims to exclude would let Gate B pass for the
wrong reason, so the *worlds* are tested as carefully as the scanner (``AXIOMS`` G6, G7).
"""

from __future__ import annotations

import unittest

from kairos.baseline import SettlementTerms
from kairos.costs import CONSERVATIVE
from kairos.structural import (
    MIN_FILL,
    Leg,
    NegRiskGroup,
    add_quote_noise,
    believed_complete,
    fair_group,
    hide_an_outcome,
    inject_arbitrage,
    marginally_unprofitable,
    obvious_arbitrage,
    scan,
    scan_naive,
    thin_the_book,
    truncate_legs,
)

HORIZONS = (7.0, 30.0, 90.0, 365.0, 730.0)


class TestFairGroupsAreActuallyFair(unittest.TestCase):
    def test_true_probabilities_sum_to_one_before_discounting(self):
        """If they did not, the group would contain an edge by construction."""
        for days in HORIZONS:
            g = fair_group(n_legs=6, days=days, seed=3)
            d = SettlementTerms(days_to_settlement=days).discount_factor
            implied = sum(leg.price for leg in g.legs) / d
            self.assertAlmostEqual(implied, 1.0, places=6, msg=f"{days}d")

    def test_the_nominal_sum_is_below_one_and_that_is_carry_not_free_money(self):
        g = fair_group(n_legs=5, days=730.0, seed=1)
        self.assertLess(g.nominal_sum, 1.0)
        self.assertFalse(scan(g).fires, "carry is not an arbitrage")

    def test_no_fair_group_yields_an_edge_at_any_horizon_or_leg_count(self):
        for days in HORIZONS:
            for n in range(2, 10):
                g = fair_group(n_legs=n, days=days, seed=n * 7)
                self.assertFalse(scan(g).fires, f"{n} legs at {days}d fired on a fair group")


class TestTheNaiveScannerIsTheExhibit(unittest.TestCase):
    """It is retained precisely because it is wrong, and the size of its wrongness is the argument."""

    def test_it_fires_on_carry_alone_at_long_horizons(self):
        g = fair_group(n_legs=5, days=730.0, seed=2)
        self.assertTrue(scan_naive(g).fires, "the naive scanner should mistake carry for edge")
        self.assertFalse(scan(g).fires)

    def test_it_fires_on_a_truncated_group(self):
        g = truncate_legs(fair_group(n_legs=8, days=30.0, seed=4), keep=4, seed=4)
        self.assertTrue(scan_naive(g).fires, "this is the 53%-arbitrage artefact")
        self.assertFalse(scan(g).fires)


class TestRefusalsBite(unittest.TestCase):
    def test_an_incomplete_leg_set_is_refused_whatever_the_prices_say(self):
        g = truncate_legs(obvious_arbitrage(fair_group(n_legs=8, days=30.0, seed=5)),
                          keep=3, seed=5)
        r = scan(g)
        self.assertFalse(r.fires)
        self.assertIn("incomplete_leg_set", r.refusals)

    def test_unverified_exhaustiveness_is_refused(self):
        r = scan(hide_an_outcome(fair_group(n_legs=6, days=30.0, seed=6)))
        self.assertFalse(r.fires)
        self.assertIn("exhaustiveness_unverified", r.refusals)

    def test_default_knowledge_is_unknown_so_a_bare_group_is_refused(self):
        """Fail closed: an unannotated group must not be scannable (AXIOMS A6)."""
        g = NegRiskGroup("bare", (Leg("a", 0.2, 999.0), Leg("b", 0.3, 999.0)), 30.0)
        r = scan(g)
        self.assertFalse(r.fires)
        self.assertIn("incomplete_leg_set", r.refusals)

    def test_an_unfillable_edge_is_not_an_edge(self):
        """AXIOMS D1. Real prices, real edge, three contracts of depth."""
        g = thin_the_book(obvious_arbitrage(fair_group(n_legs=5, days=30.0, seed=7)), depth=3.0)
        r = scan(g)
        self.assertGreater(r.edge, 0.0, "the edge is real")
        self.assertFalse(r.fires, "but it cannot be filled")
        self.assertIn("insufficient_depth", r.refusals)
        self.assertLess(r.fillable, MIN_FILL)


class TestCostArithmeticIsTheOnlyThingStandingThere(unittest.TestCase):
    """The discriminating null. Every other arbitrage-free world is rejected by a flag."""

    def test_a_marginally_unprofitable_group_does_not_fire(self):
        for days in HORIZONS:
            g = marginally_unprofitable(fair_group(n_legs=5, days=days, seed=8))
            r = scan(g)
            self.assertFalse(r.fires, f"{days}d: fired on a group unprofitable by construction")
            self.assertLess(r.edge, 0.0, f"{days}d")

    def test_carry_is_charged_once_not_twice(self):
        """AXIOMS C7. ``effective_yes_cost`` already includes carry; the payoff must stay nominal.

        Driven rather than asserted: the scanner's edge must equal 1 - sum(effective_yes_cost),
        with no second discount factor anywhere.
        """
        g = fair_group(n_legs=4, days=365.0, seed=9)
        expected = 1.0 - sum(
            CONSERVATIVE.effective_yes_cost(leg.price, g.days_to_settlement) for leg in g.legs
        )
        self.assertAlmostEqual(scan(g).edge, expected, places=12)


class TestPositiveControls(unittest.TestCase):
    def test_the_independent_control_is_detected_at_every_horizon(self):
        for days in HORIZONS:
            g = obvious_arbitrage(fair_group(n_legs=5, days=days, seed=10))
            self.assertTrue(scan(g).fires, f"{days}d: missed an unambiguous arbitrage")

    def test_the_independent_control_does_not_use_the_scanners_cost_formula(self):
        """It is defined purely on quoted prices, so detecting it is measured, not guaranteed."""
        g = obvious_arbitrage(fair_group(n_legs=5, days=30.0, seed=11), nominal_sum=0.70)
        self.assertAlmostEqual(g.nominal_sum, 0.70, places=9)

    def test_the_circular_control_is_labelled_as_such_by_construction(self):
        """`inject_arbitrage` targets the scanner's own post-cost edge - kept only as an exhibit."""
        g = inject_arbitrage(fair_group(n_legs=5, days=30.0, seed=12), edge=0.05)
        self.assertAlmostEqual(scan(g).edge, 0.05, places=3)


class TestResidualRiskIsQuantifiedNotHidden(unittest.TestCase):
    """The gate's most useful output: what the scanner structurally cannot defend against."""

    def test_truncation_asserted_complete_fires_and_nothing_inside_the_scanner_can_stop_it(self):
        g = believed_complete(truncate_legs(fair_group(n_legs=8, days=30.0, seed=13),
                                            keep=4, seed=13))
        r = scan(g)
        self.assertTrue(r.fires)
        self.assertEqual(r.refusals, ())

    def test_quote_noise_alone_never_manufactures_an_edge(self):
        fired = 0
        for i in range(300):
            g = add_quote_noise(fair_group(n_legs=5, days=30.0, seed=i), sd=0.004, seed=i)
            fired += scan(g).fires
        self.assertEqual(fired, 0, f"noise produced {fired} phantom arbitrages")


if __name__ == "__main__":
    unittest.main()
