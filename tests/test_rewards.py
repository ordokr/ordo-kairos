"""Polymarket's published liquidity-rewards scoring rule.

``docs/PROTOCOL.md`` Class R. Taken from the venue's own documentation rather than a summary — the
method run that produced the registration had selected "quote at the max-spread edge", and the
published formula scores **zero** there. The whole gate turns on that, so the formula gets tests.
"""

from __future__ import annotations

import unittest

from kairos.book import Book, Level
from kairos.rewards import book_score, order_score, q_min, share_of_pool


class TestOrderScoreIsQuadraticInDistance(unittest.TestCase):
    def test_a_quote_at_the_midpoint_scores_its_full_size(self):
        self.assertAlmostEqual(order_score(0.03, 0.0, 100.0), 100.0, places=9)

    def test_a_quote_at_the_max_spread_scores_nothing(self):
        """The registration's own premise died here: the edge earns zero, not 'rewards with no fills'."""
        self.assertEqual(order_score(0.03, 0.03, 100.0), 0.0)

    def test_halfway_out_scores_a_quarter_not_a_half(self):
        self.assertAlmostEqual(order_score(0.04, 0.02, 100.0), 25.0, places=9)

    def test_beyond_the_max_spread_does_not_qualify_at_all(self):
        self.assertEqual(order_score(0.03, 0.031, 100.0), 0.0)
        self.assertEqual(order_score(0.03, 0.10, 100.0), 0.0)

    def test_score_is_linear_in_size_at_fixed_distance(self):
        self.assertAlmostEqual(order_score(0.04, 0.01, 200.0),
                               2.0 * order_score(0.04, 0.01, 100.0), places=9)

    def test_a_degenerate_max_spread_is_refused_rather_than_dividing_by_zero(self):
        for bad in (0.0, -0.01):
            with self.assertRaises(ValueError):
                order_score(bad, 0.0, 100.0)


class TestTwoSidedCombination(unittest.TestCase):
    """``Q_min`` rewards balanced quoting and only partly credits a one-sided book."""

    def test_a_balanced_book_scores_the_common_side(self):
        self.assertAlmostEqual(q_min(80.0, 80.0, midpoint=0.50), 80.0, places=9)

    def test_a_one_sided_book_is_credited_at_a_third_in_the_normal_range(self):
        """max(min(90,0), max(90/3, 0/3)) = 30."""
        self.assertAlmostEqual(q_min(90.0, 0.0, midpoint=0.50), 30.0, places=9)

    def test_the_weaker_side_governs_when_both_are_present(self):
        self.assertAlmostEqual(q_min(90.0, 60.0, midpoint=0.50), 60.0, places=9)

    def test_near_the_extremes_liquidity_must_be_genuinely_two_sided(self):
        """Below 0.10 and above 0.90 the one-third allowance is withdrawn."""
        for mid in (0.05, 0.95):
            with self.subTest(mid=mid):
                self.assertEqual(q_min(90.0, 0.0, midpoint=mid), 0.0)
                self.assertAlmostEqual(q_min(90.0, 60.0, midpoint=mid), 60.0, places=9)

    def test_the_boundary_is_inclusive_of_the_normal_range(self):
        self.assertGreater(q_min(90.0, 0.0, midpoint=0.10), 0.0)
        self.assertGreater(q_min(90.0, 0.0, midpoint=0.90), 0.0)


class TestBookScoreMeasuresTheCompetition(unittest.TestCase):
    """The competitor term is the one that could have been fudged, so it is read off the real book."""

    def book(self):
        # midpoint 0.50; bids walking down from 0.49, asks up from 0.51
        return Book(
            asks=(Level(0.51, 100.0), Level(0.53, 100.0), Level(0.60, 100.0)),
            bids=(Level(0.49, 100.0), Level(0.47, 100.0), Level(0.40, 100.0)),
        )

    def test_only_levels_inside_the_max_spread_score(self):
        """0.60 and 0.40 are 10c from the midpoint and cannot qualify at a 3c max spread."""
        scored = book_score(self.book(), midpoint=0.50, max_spread=0.03, min_size=1.0)
        self.assertGreater(scored, 0.0)
        wider = book_score(self.book(), midpoint=0.50, max_spread=0.15, min_size=1.0)
        self.assertGreater(wider, scored, "a wider qualifying band admits more resting size")

    def test_orders_below_the_minimum_size_do_not_score(self):
        thin = Book(asks=(Level(0.51, 10.0),), bids=(Level(0.49, 10.0),))
        self.assertEqual(book_score(thin, midpoint=0.50, max_spread=0.03, min_size=100.0), 0.0)
        self.assertGreater(book_score(thin, midpoint=0.50, max_spread=0.03, min_size=1.0), 0.0)

    def test_an_empty_book_has_no_competition(self):
        self.assertEqual(book_score(Book(asks=(), bids=()), midpoint=0.50,
                                    max_spread=0.03, min_size=1.0), 0.0)


class TestShareOfPool(unittest.TestCase):
    def test_share_is_own_over_own_plus_competitors(self):
        self.assertAlmostEqual(share_of_pool(50.0, 150.0), 0.25, places=9)

    def test_an_empty_book_hands_the_whole_pool_to_the_only_maker(self):
        self.assertAlmostEqual(share_of_pool(50.0, 0.0), 1.0, places=9)

    def test_scoring_nothing_earns_nothing_even_with_no_competition(self):
        """The edge-quote case: zero score is zero share, not a free pool."""
        self.assertEqual(share_of_pool(0.0, 0.0), 0.0)

    def test_share_falls_as_competitors_arrive(self):
        self.assertGreater(share_of_pool(50.0, 50.0), share_of_pool(50.0, 500.0))


if __name__ == "__main__":
    unittest.main()
