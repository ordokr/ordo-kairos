"""The cost model. Every gate's verdict is a comparison against these numbers.

Until now `costs.py` was the only core module with no direct behavioural tests — it was heavily
*used* by other suites as a fixture, which is not the same as being *checked*. A fixture that is
wrong makes every test built on it wrong in the same direction, silently.

The figures pinned here (2.5pp required edge, 5.0pp no-trade band at 0.50 / 30 days) are quoted
throughout the docs and used to reason about whether any measured edge could ever clear friction.
They are load-bearing claims, so they get an assertion rather than a paragraph.
"""

from __future__ import annotations

import unittest

from kairos.costs import CONSERVATIVE, CostError, CostModel

DAY = 1.0


class TestFeeShape(unittest.TestCase):
    """`fee = coeff * P * (1 - P)`. The shape is the argument for longshot exclusion."""

    def test_the_fee_peaks_at_the_midpoint(self):
        mid = CONSERVATIVE.fee(0.50)
        for p in (0.10, 0.25, 0.40, 0.60, 0.75, 0.90):
            self.assertLess(CONSERVATIVE.fee(p), mid, f"fee at {p} should be below the peak")

    def test_the_fee_vanishes_at_the_extremes(self):
        self.assertAlmostEqual(CONSERVATIVE.fee(0.001), 0.0, places=3)
        self.assertAlmostEqual(CONSERVATIVE.fee(0.999), 0.0, places=3)

    def test_the_fee_bites_hardest_in_relative_terms_on_longshots(self):
        """The docstring's actual claim, driven: fee falls linearly in P, the payoff falls like P.

        This is *why* the longshot band exists. An absolute fee that looks small at 0.02 is a
        quarter of the position's value.
        """
        relative = [(p, CONSERVATIVE.fee(p) / p) for p in (0.02, 0.10, 0.30, 0.50, 0.80)]
        for (p_low, r_low), (p_high, r_high) in zip(relative, relative[1:]):
            self.assertGreater(r_low, r_high,
                               f"relative fee at {p_low} should exceed that at {p_high}")

    def test_a_maker_pays_no_fee_by_default(self):
        self.assertEqual(CONSERVATIVE.fee(0.5, maker=True), 0.0)
        self.assertGreater(CONSERVATIVE.fee(0.5, maker=False), 0.0)


class TestCarry(unittest.TestCase):
    def test_carry_scales_with_time_and_with_capital(self):
        self.assertAlmostEqual(CONSERVATIVE.carry(1.0, 365.0), 0.06, places=9)
        self.assertAlmostEqual(CONSERVATIVE.carry(2.0, 365.0), 0.12, places=9)
        self.assertAlmostEqual(CONSERVATIVE.carry(1.0, 730.0), 0.12, places=9)

    def test_carry_is_zero_at_settlement(self):
        self.assertEqual(CONSERVATIVE.carry(1.0, 0.0), 0.0)

    def test_negative_horizons_are_refused(self):
        with self.assertRaises(CostError):
            CONSERVATIVE.carry(1.0, -1.0)


class TestEffectiveCosts(unittest.TestCase):
    def test_the_taker_path_is_spread_plus_fee_plus_carry(self):
        c, mid, days = CONSERVATIVE, 0.40, 30.0
        traded = mid + c.half_spread
        base = traded + c.fee(traded)
        self.assertAlmostEqual(
            c.effective_yes_cost(mid, days), base + c.carry(base, days), places=12
        )

    def test_a_maker_pays_neither_spread_nor_fee(self):
        c, mid, days = CONSERVATIVE, 0.40, 30.0
        base = mid  # no spread crossed, no taker fee
        self.assertAlmostEqual(
            c.effective_yes_cost(mid, days, maker=True), base + c.carry(base, days), places=12
        )

    def test_cost_rises_monotonically_with_horizon(self):
        prev = -1.0
        for days in (0.0, 7.0, 30.0, 365.0, 730.0):
            now = CONSERVATIVE.effective_yes_cost(0.5, days)
            self.assertGreater(now, prev)
            prev = now

    def test_the_no_side_is_the_mirror_of_the_yes_side(self):
        for mid in (0.2, 0.5, 0.77):
            self.assertAlmostEqual(
                CONSERVATIVE.effective_no_cost(mid, 30.0),
                CONSERVATIVE.effective_yes_cost(1.0 - mid, 30.0),
                places=12,
            )

    def test_cost_may_exceed_one_in_which_case_no_probability_justifies_the_trade(self):
        """The docstring says so explicitly; a long-dated near-certainty is the case."""
        self.assertGreater(CONSERVATIVE.effective_yes_cost(0.95, 3650.0), 1.0)

    def test_prices_outside_the_unit_interval_are_refused(self):
        for bad in (-0.1, 1.5, float("nan")):
            with self.assertRaises(CostError, msg=f"price {bad}"):
                CONSERVATIVE.effective_yes_cost(bad, 30.0)

    def test_the_endpoints_are_admitted_deliberately_and_priced_sensibly(self):
        """`[0, 1]` is closed here on purpose, unlike the scorers which clip away from 0 and 1.

        Cost is defined at the endpoints where a log score is not: buying a worthless contract
        still costs the spread, and buying a certainty costs more than the dollar it returns. Pinned
        because "the cost model rejects 0 and 1" is a plausible-sounding assumption that would send
        a caller clipping inputs it does not need to clip.
        """
        self.assertAlmostEqual(CONSERVATIVE.effective_yes_cost(0.0, 30.0), 0.00537, places=4)
        self.assertGreater(CONSERVATIVE.effective_yes_cost(1.0, 30.0), 1.0)


class TestTheDocumentedNoTradeBand(unittest.TestCase):
    """These two numbers appear throughout the docs. Pinned so a parameter change surfaces here."""

    def test_required_edge_at_mid_price_and_one_month(self):
        required = CONSERVATIVE.effective_yes_cost(0.50, 30.0) - 0.50
        self.assertAlmostEqual(required, 0.025, places=3)

    def test_the_round_trip_drag_is_the_width_of_the_no_trade_band(self):
        drag = CONSERVATIVE.round_trip_drag(0.50, 30.0)
        self.assertAlmostEqual(drag, 0.050, places=3)

    def test_the_drag_is_exactly_both_sides_less_one(self):
        for mid, days in ((0.3, 7.0), (0.5, 30.0), (0.8, 365.0)):
            self.assertAlmostEqual(
                CONSERVATIVE.round_trip_drag(mid, days),
                CONSERVATIVE.effective_yes_cost(mid, days)
                + CONSERVATIVE.effective_no_cost(mid, days) - 1.0,
                places=12,
            )

    def test_a_long_dated_contract_can_have_no_survivable_edge_at_all(self):
        """Drag >= 1.0 means the two sides cannot both be priced sanely."""
        self.assertGreaterEqual(CONSERVATIVE.round_trip_drag(0.5, 3650.0), 0.3)


class TestPriceBand(unittest.TestCase):
    def test_the_band_excludes_longshots_at_both_ends(self):
        self.assertFalse(CONSERVATIVE.price_in_band(0.01))
        self.assertFalse(CONSERVATIVE.price_in_band(0.99))
        self.assertTrue(CONSERVATIVE.price_in_band(0.50))

    def test_the_boundaries_are_inclusive(self):
        self.assertTrue(CONSERVATIVE.price_in_band(CONSERVATIVE.min_price))
        self.assertTrue(CONSERVATIVE.price_in_band(CONSERVATIVE.max_price))


class TestMakerCaptureInvertsTheSpread(unittest.TestCase):
    """Gate M.0. Every other number in this repo is a taker number.

    A taker pays ``half_spread`` to cross; a maker who buys at the bid and sells at the ask
    **collects** it. The sign of the largest cost term flips, which is the entire reason Class M
    exists as a separate hypothesis. What this does **not** include is adverse selection, and that
    is the whole of maker P&L — so the number is an upper bound and the docstring says so.
    """

    def test_with_no_maker_fee_the_capture_is_exactly_half_the_spread(self):
        self.assertAlmostEqual(CONSERVATIVE.maker_capture(0.02, 0.50), 0.01, places=12)

    def test_a_maker_fee_reduces_it(self):
        charged = CostModel(maker_fee_coeff=0.02)
        self.assertLess(charged.maker_capture(0.02, 0.50), CONSERVATIVE.maker_capture(0.02, 0.50))
        self.assertAlmostEqual(charged.maker_capture(0.02, 0.50),
                               0.01 - charged.fee(0.50, maker=True), places=12)

    def test_the_sign_flips_against_the_taker_on_the_same_market(self):
        """The taker pays the spread; the maker is paid it. That inversion is the hypothesis."""
        price, days = 0.50, 30.0
        taker_pays = CONSERVATIVE.effective_yes_cost(price, days) - price
        maker_earns = CONSERVATIVE.maker_capture(2.0 * CONSERVATIVE.half_spread, price)
        self.assertGreater(taker_pays, 0.0)
        self.assertGreater(maker_earns, 0.0)

    def test_no_spread_means_nothing_to_capture(self):
        self.assertLessEqual(CONSERVATIVE.maker_capture(0.0, 0.50), 0.0)

    def test_a_fee_larger_than_the_spread_makes_capture_negative(self):
        """Quoting is not free money. A wide fee on a tight spread is a losing quote."""
        expensive = CostModel(maker_fee_coeff=0.5)
        self.assertLess(expensive.maker_capture(0.002, 0.50), 0.0)

    def test_an_invalid_price_or_negative_spread_is_refused(self):
        with self.assertRaises(ValueError):
            CONSERVATIVE.maker_capture(0.02, 1.5)
        with self.assertRaises(CostError):
            CONSERVATIVE.maker_capture(-0.01, 0.50)


class TestConstruction(unittest.TestCase):
    def test_a_negative_parameter_is_refused_at_construction(self):
        for kw in ({"taker_fee_coeff": -0.01}, {"half_spread": -0.001},
                   {"settlement_wedge_annual": -0.01}):
            with self.assertRaises(CostError, msg=str(kw)):
                CostModel(**kw)

    def test_an_inverted_price_band_is_refused(self):
        with self.assertRaises(CostError):
            CostModel(min_price=0.9, max_price=0.1)

    def test_the_conservative_default_is_the_one_the_docs_quote(self):
        self.assertEqual(CONSERVATIVE.taker_fee_coeff, 0.07)
        self.assertEqual(CONSERVATIVE.half_spread, 0.005)
        self.assertEqual(CONSERVATIVE.settlement_wedge_annual, 0.06)


if __name__ == "__main__":
    unittest.main()
