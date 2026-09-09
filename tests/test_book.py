"""Order-book depth. The sort-order guard here is the whole point of the module.

The live CLOB returns both sides worst-first. Measured against Gamma's own ``bestAsk`` on 12
markets: best ask equals ``asks[-1]`` in 12/12 and ``asks[0]`` in 0/12, where ``asks[0]`` was 0.999
every single time. A consumer reading the top of the list gets a number that looks like a price and
is not one.
"""

from __future__ import annotations

import unittest

from kairos.book import Book, Fill, Level, cost_to_buy, parse_book
from kairos.costs import CONSERVATIVE

RAW = {
    # exactly as the endpoint returns it: asks descending, bids ascending
    "asks": [{"price": "0.999", "size": "231.15"}, {"price": "0.60", "size": "10"},
             {"price": "0.50", "size": "20"}, {"price": "0.40", "size": "5"}],
    "bids": [{"price": "0.10", "size": "100"}, {"price": "0.30", "size": "50"}],
    "tick_size": "0.001",
    "min_order_size": "5",
}


class TestSortOrderIsNormalised(unittest.TestCase):
    def test_the_best_ask_is_the_lowest_not_the_first_element(self):
        b = parse_book(RAW)
        self.assertEqual(b.best_ask, 0.40)
        self.assertEqual(b.asks[0].price, 0.40, "asks must be normalised ascending")
        self.assertEqual(b.asks[-1].price, 0.999)

    def test_the_best_bid_is_the_highest(self):
        b = parse_book(RAW)
        self.assertEqual(b.best_bid, 0.30)
        self.assertEqual(b.bids[0].price, 0.30)

    def test_reading_the_raw_first_element_would_have_given_the_worst_price(self):
        """States the defect explicitly so the guard cannot be mistaken for cosmetics."""
        raw_first = float(RAW["asks"][0]["price"])
        self.assertEqual(raw_first, 0.999)
        self.assertLess(parse_book(RAW).best_ask, raw_first)

    def test_malformed_levels_are_dropped_not_guessed(self):
        b = parse_book({"asks": [{"price": "x", "size": "1"}, {"price": "0.5", "size": "2"},
                                 {"size": "3"}], "bids": []})
        self.assertEqual(len(b.asks), 1)
        self.assertEqual(b.asks[0].price, 0.5)

    def test_an_empty_book_has_no_best_price_rather_than_a_default(self):
        b = parse_book({"asks": [], "bids": []})
        self.assertIsNone(b.best_ask)
        self.assertIsNone(b.best_bid)
        self.assertEqual(b.ask_depth, 0.0)

    def test_tick_and_min_size_survive_and_fall_back_safely(self):
        b = parse_book(RAW)
        self.assertEqual(b.min_order_size, 5.0)
        self.assertEqual(parse_book({"asks": [], "bids": [], "tick_size": "junk"}).tick_size, 0.001)


class TestCostToBuyWalksTheBook(unittest.TestCase):
    """An edge at the touch is not an edge at size."""

    def test_a_small_order_pays_only_the_best_level(self):
        f = cost_to_buy(parse_book(RAW), 5)
        self.assertTrue(f.complete)
        self.assertAlmostEqual(f.vwap, 0.40, places=9)
        self.assertEqual(f.levels_consumed, 1)

    def test_a_larger_order_walks_up_and_costs_more(self):
        small = cost_to_buy(parse_book(RAW), 5)
        large = cost_to_buy(parse_book(RAW), 25)
        self.assertTrue(large.complete)
        # 5@0.40 + 20@0.50 = 12.0 over 25 contracts
        self.assertAlmostEqual(large.vwap, 12.0 / 25.0, places=9)
        self.assertGreater(large.vwap, small.vwap, "depth must cost more, not less")

    def test_a_book_too_thin_reports_a_partial_fill_rather_than_a_cheap_price(self):
        f = cost_to_buy(parse_book(RAW), 10_000)
        self.assertFalse(f.complete)
        self.assertLess(f.filled, 10_000)
        self.assertAlmostEqual(f.filled, 266.15, places=6)
        self.assertAlmostEqual(f.filled, parse_book(RAW).ask_depth, places=9,
                               msg="a too-large order consumes the whole book, no more")

    def test_an_empty_book_fills_nothing(self):
        f = cost_to_buy(parse_book({"asks": [], "bids": []}), 25)
        self.assertFalse(f.complete)
        self.assertEqual(f.filled, 0.0)
        self.assertNotEqual(f.vwap, f.vwap, "vwap of nothing is NaN, not zero")

    def test_zero_or_negative_size_is_refused(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                cost_to_buy(parse_book(RAW), bad)


class TestCrossedPriceIsNotChargedSpreadTwice(unittest.TestCase):
    """AXIOMS C7, in its Class B form."""

    def test_a_traded_price_costs_less_than_the_same_number_treated_as_a_mid(self):
        vwap, days = 0.48, 30.0
        crossed = CONSERVATIVE.effective_yes_cost_at(vwap, days)
        as_mid = CONSERVATIVE.effective_yes_cost(vwap, days)
        self.assertLess(crossed, as_mid)
        self.assertAlmostEqual(as_mid - crossed, CONSERVATIVE.half_spread, delta=0.002)

    def test_the_traded_path_still_charges_taker_fee_and_carry(self):
        vwap, days = 0.50, 365.0
        c = CONSERVATIVE.effective_yes_cost_at(vwap, days)
        self.assertGreater(c, vwap, "fee and carry are still charged")
        base = vwap + CONSERVATIVE.fee(vwap, maker=False)
        self.assertAlmostEqual(c, base + CONSERVATIVE.carry(base, days), places=12)

    def test_it_is_not_the_same_as_the_maker_path(self):
        """`maker=True` would suppress the spread but also zero the fee; taking the ask is a take."""
        vwap = 0.50
        self.assertGreater(CONSERVATIVE.effective_yes_cost_at(vwap, 30.0),
                           CONSERVATIVE.effective_yes_cost(vwap, 30.0, maker=True))


if __name__ == "__main__":
    unittest.main()
