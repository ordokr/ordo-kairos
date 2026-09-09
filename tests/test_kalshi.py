"""Tests for the Kalshi adapter — chiefly the book mirroring, which inverts the trade if wrong.

Kalshi publishes only resting *bids*. A bid to buy NO at ``q`` is an offer to sell YES at ``1 - q``,
so the YES ask ladder is the NO bid ladder mirrored. An adapter that read ``yes_dollars`` as asks
would price every purchase at the bid and manufacture an edge equal to the whole spread on every
market — a false positive on every pair, with no symptom anywhere else in the stack.

These are offline: the mirroring is arithmetic, and arithmetic does not need the network. The
measurement that established the mirroring is recorded in ``kairos/kalshi.py``'s docstring, taken
against 14 live two-sided markets.
"""

from __future__ import annotations

import unittest

from kairos.book import cost_to_buy
from kairos.kalshi import KALSHI_FEES, books_from_orderbook

#: A book with an obvious spread: best YES bid 0.40, best YES ask 1 - 0.55 = 0.45.
RAW = {
    "orderbook_fp": {
        "yes_dollars": [["0.3800", "100.00"], ["0.4000", "50.00"], ["0.3900", "75.00"]],
        "no_dollars": [["0.5500", "30.00"], ["0.5000", "80.00"], ["0.5300", "20.00"]],
    }
}


class TestBookMirroring(unittest.TestCase):
    def setUp(self):
        self.yes, self.no = books_from_orderbook(RAW)

    def test_the_yes_ask_is_the_mirrored_no_bid(self):
        self.assertAlmostEqual(self.yes.best_ask, 0.45, places=9)

    def test_the_yes_bid_is_the_raw_yes_bid(self):
        self.assertAlmostEqual(self.yes.best_bid, 0.40, places=9)

    def test_the_no_side_is_the_mirror_image(self):
        self.assertAlmostEqual(self.no.best_ask, 0.60, places=9)   # 1 - 0.40
        self.assertAlmostEqual(self.no.best_bid, 0.55, places=9)

    def test_buying_yes_never_prices_at_the_bid(self):
        """The failure mode this whole module exists to prevent."""
        self.assertGreater(cost_to_buy(self.yes, 10.0).vwap, self.yes.best_bid)

    def test_both_books_are_sorted_best_first(self):
        for book in (self.yes, self.no):
            with self.subTest(book=book):
                self.assertEqual(list(book.asks), sorted(book.asks, key=lambda lv: lv.price))
                self.assertEqual(list(book.bids), sorted(book.bids, key=lambda lv: -lv.price))

    def test_walking_the_ask_book_crosses_the_cheapest_level_first(self):
        """30 at 0.45 then 20 at 0.47, so 50 contracts average 0.458."""
        fill = cost_to_buy(self.yes, 50.0)
        self.assertTrue(fill.complete)
        self.assertAlmostEqual(fill.vwap, (30 * 0.45 + 20 * 0.47) / 50, places=9)

    def test_a_malformed_level_is_dropped_not_guessed(self):
        raw = {"orderbook_fp": {"yes_dollars": [["x", "1"], ["0.4000", "50.00"]],
                                "no_dollars": [["0.5500", "30.00"]]}}
        yes, _ = books_from_orderbook(raw)
        self.assertEqual(len(yes.bids), 1)

    def test_an_empty_side_yields_no_ask(self):
        """A market with no resting NO bids has no YES offer at all — not a free one."""
        yes, _ = books_from_orderbook({"orderbook_fp": {"yes_dollars": [["0.4000", "5"]]}})
        self.assertIsNone(yes.best_ask)
        self.assertEqual(cost_to_buy(yes, 1.0).filled, 0.0)

    def test_zero_size_levels_are_not_depth(self):
        raw = {"orderbook_fp": {"no_dollars": [["0.5500", "0.00"], ["0.5000", "80.00"]]}}
        yes, _ = books_from_orderbook(raw)
        self.assertAlmostEqual(yes.best_ask, 0.50, places=9)


class TestFeeScheduleIsNotASilentDefault(unittest.TestCase):
    """Gate C's kill rule is terminal, so the fee coefficient may not be an unaudited constant."""

    def test_the_schedule_declares_whether_anyone_checked_it(self):
        self.assertIn("verified", KALSHI_FEES.__dataclass_fields__)
        self.assertTrue(KALSHI_FEES.source)
        self.assertTrue(KALSHI_FEES.checked_on)

    def test_an_unverified_schedule_says_why(self):
        if not KALSHI_FEES.verified:
            self.assertTrue(KALSHI_FEES.note,
                            "an unverified fee schedule must record what the attempt returned")


if __name__ == "__main__":
    unittest.main()
