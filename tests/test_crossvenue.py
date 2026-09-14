"""Tests for cross-venue descriptors and the executable deviation.

Two properties carry the measurement:

1. **A descriptor fails closed on evidence the venue did not publish.** Gate C proved the comparison
   refuses contradictory evidence; nothing there proved an adapter would refuse *absent* evidence,
   because in the null worlds every field was always present.
2. **The deviation is the payoff identity, not a price difference.** Buying YES on one venue and NO
   on the other pays $1 — so the edge is ``1 - (cost + cost)``, both legs carry, and a partial fill
   is a refusal rather than a cheaper trade.
"""

from __future__ import annotations

import unittest

from kairos.book import Book, Level
from kairos.costs import CONSERVATIVE
from kairos.crossvenue import (
    best_direction,
    date_blocks,
    days_until,
    edge_from_vwaps,
    fill_pair,
    gate_d0_verdict,
    kalshi_descriptor,
    polymarket_descriptor,
    round_trip_cost,
)
from kairos.identity import compare_identities

POLY = {
    "id": "12345",
    "question": "Will gold close above $2,000 on March 31, 2027?",
    "description": ('This market will resolve to "Yes" if gold closes above $2,000 on March 31, '
                    "2027 at 12:00 PM ET. The resolution source is the primary spot index."),
    "endDate": "2027-03-31T16:00:00Z",
    "clobTokenIds": '["tok-yes", "tok-no"]',
}

KALSHI_EVENT = {
    "title": "gold closes above",
    "settlement_sources": [{"name": "the primary spot index"}],
}
KALSHI_MARKET = {
    "ticker": "KXGOLD-27MAR31-T2000",
    "market_type": "binary",
    "strike_type": "greater",
    "floor_strike": 2000.0,
    "yes_sub_title": "$2,000 or above",
    "close_time": "2027-03-31T16:00:00Z",
    "expiration_time": "2027-04-07T16:00:00Z",
}


def book(levels, *, side="asks"):
    lv = tuple(Level(p, s) for p, s in levels)
    return Book(asks=lv, bids=()) if side == "asks" else Book(asks=(), bids=lv)


class TestDescriptors(unittest.TestCase):
    def test_a_polymarket_market_goes_through_the_gated_text_extractor(self):
        d = polymarket_descriptor(POLY)
        self.assertIsNotNone(d)
        self.assertEqual(d.identity.threshold, 2000.0)
        self.assertEqual(d.identity.instant, "2027-03-31T16:00Z")
        self.assertEqual(d.yes_handle, "tok-yes")
        self.assertEqual(d.no_handle, "tok-no")
        self.assertTrue(all(how in ("text", "missing") for _, how in d.provenance),
                        "Polymarket publishes identity as prose; nothing here is structured")

    def test_a_kalshi_market_uses_its_structured_fields(self):
        d = kalshi_descriptor(KALSHI_EVENT, KALSHI_MARKET)
        self.assertIsNotNone(d)
        self.assertEqual(d.identity.threshold, 2000.0)
        self.assertEqual(d.identity.instant, "2027-03-31T16:00Z")
        prov = dict(d.provenance)
        self.assertEqual(prov["threshold"], "structured")
        self.assertEqual(prov["resolution_source"], "structured")

    def test_close_time_is_the_settlement_instant_and_expiration_is_the_carry_horizon(self):
        """Measured on KXBTCD: close_time is the determination instant, expiration_time is the
        administrative settlement window seven days later."""
        d = kalshi_descriptor(KALSHI_EVENT, KALSHI_MARKET)
        self.assertTrue(d.identity.instant.startswith("2027-03-31"))
        self.assertEqual(d.settle_iso, "2027-04-07T16:00:00Z")

    def test_a_parlay_leg_is_not_a_single_event(self):
        market = dict(KALSHI_MARKET, mve_selected_legs=[{"market_ticker": "X"}])
        self.assertIsNone(kalshi_descriptor(KALSHI_EVENT, market))

    def test_a_range_market_fails_closed_rather_than_collapsing_to_one_bound(self):
        """A band is not an above-X binary, and no single number represents it."""
        market = dict(KALSHI_MARKET, cap_strike=2100.0)
        d = kalshi_descriptor(KALSHI_EVENT, market)
        self.assertIn("threshold", d.identity.missing)

    def test_a_custom_selector_becomes_scope_not_a_threshold(self):
        market = {"ticker": "KXWHO-ABC", "market_type": "binary", "strike_type": "custom",
                  "custom_strike": {"Holder": "Klaus Iohannis"}, "yes_sub_title": "Klaus Iohannis",
                  "close_time": "2027-03-31T16:00:00Z"}
        d = kalshi_descriptor({"title": "Who will be the next Secretary General?",
                               "settlement_sources": [{"name": "the organisation"}]}, market)
        self.assertNotIn("threshold", d.identity.missing)
        self.assertIn("iohanni", {t[:7] for t in d.identity.scope})

    def test_a_market_with_no_close_time_fails_closed(self):
        d = kalshi_descriptor(KALSHI_EVENT, dict(KALSHI_MARKET, close_time=""))
        self.assertIn("settlement_instant", d.identity.missing)

    def test_polymarkets_settlement_minute_is_trusted_only_when_the_prose_confirms_it(self):
        """``endDate`` is sometimes a real deadline and sometimes a placeholder.

        Measured over 788 open markets: 65% sit at exactly 00:00Z, ~95% at a day boundary, and
        nothing in the payload says which kind a given market is. The resolution prose is the second
        source that settles it — the Somaliland market says "by December 31, 2026, 11:59 PM ET" and
        its ``endDate`` is the same instant. Agreement earns trust; silence does not.
        """
        confirmed = polymarket_descriptor(POLY)
        self.assertTrue(confirmed.identity.instant_confirmed)
        self.assertNotIn("settlement_time", confirmed.identity.missing)

        silent = polymarket_descriptor(dict(POLY, description="Resolves per the primary spot index."))
        self.assertFalse(silent.identity.instant_confirmed)
        self.assertIn("settlement_time", silent.identity.missing)

    def test_a_contradiction_between_the_two_sources_is_refused_not_resolved(self):
        """A rules paragraph and a close timestamp that disagree mean the minute is UNKNOWN."""
        d = polymarket_descriptor(dict(POLY, endDate="2027-03-31T20:00:00Z"))
        self.assertFalse(d.identity.instant_confirmed)
        self.assertIn("settlement_time", d.identity.missing)

    def test_a_genuinely_identical_cross_venue_pair_verifies(self):
        """The positive control, and the whole point of the extractor.

        Polymarket states its determination instant only in prose; Kalshi publishes it as data. This
        pair agrees on all seven pieces of evidence, and before Gate C2 it could not verify at all —
        no Polymarket/Kalshi pair could, which made the measurement's zero structural rather than
        empirical (AXIOMS G12).
        """
        left = polymarket_descriptor(POLY)
        right = kalshi_descriptor(KALSHI_EVENT, KALSHI_MARKET)
        verdict = compare_identities(left.identity, right.identity)
        self.assertTrue(verdict.paired, f"refused on {verdict.refusals}")


class TestUnavailableEvidenceIsNotDisagreement(unittest.TestCase):
    """The first cross-venue run reported `resolution_source_differs` on 100% of 2.28M pairs.

    Two thirds of those were Polymarket markets whose arbiter is prose the extractor could not read.
    A field neither side supplied has not been compared, so it must not also be reported as
    disagreeing — and a reason that fires on every pair drives the sole-blocker column to zero,
    destroying the only diagnostic that names the binding constraint (AXIOMS G10).
    """

    def test_an_unrecoverable_field_is_reported_once_and_as_unrecoverable(self):
        left = polymarket_descriptor(dict(POLY, description="No arbiter is named here."))
        right = kalshi_descriptor(KALSHI_EVENT, KALSHI_MARKET)
        verdict = compare_identities(left.identity, right.identity)
        self.assertFalse(verdict.paired)
        self.assertIn("unrecoverable:left:resolution_source", verdict.refusals)
        self.assertNotIn("resolution_source_differs", verdict.refusals)

    def test_removing_the_duplicate_reason_cannot_create_a_pair(self):
        """The verdict is invariant: an unrecoverable field still refuses on its own."""
        left = polymarket_descriptor(dict(POLY, description="No arbiter is named here."))
        right = kalshi_descriptor(KALSHI_EVENT, KALSHI_MARKET)
        self.assertFalse(compare_identities(left.identity, right.identity).paired)


class TestDeviation(unittest.TestCase):
    def test_the_edge_is_one_minus_both_legs(self):
        edge = edge_from_vwaps(0.40, 0.55, 0.0, CONSERVATIVE)
        expected = 1.0 - (CONSERVATIVE.effective_yes_cost_at(0.40, 0.0)
                          + CONSERVATIVE.effective_yes_cost_at(0.55, 0.0))
        self.assertAlmostEqual(edge, expected, places=12)

    def test_carry_is_charged_on_both_legs(self):
        """Collateral is locked at two venues at once, so the opportunity cost is paid twice."""
        self.assertLess(edge_from_vwaps(0.40, 0.55, 365.0, CONSERVATIVE),
                        edge_from_vwaps(0.40, 0.55, 0.0, CONSERVATIVE))

    def test_a_partial_fill_is_a_refusal_not_a_cheaper_trade(self):
        thin = book([(0.40, 3.0)])
        deep = book([(0.55, 1000.0)])
        self.assertEqual(fill_pair(thin, deep, 25.0), "thin_yes_leg")
        self.assertEqual(fill_pair(deep, thin, 25.0), "thin_no_leg")

    def test_both_directions_are_tried_and_the_better_one_wins(self):
        """A deviation has a sign; checking one direction measures half the distribution."""
        poly_yes = book([(0.90, 1000.0)])   # expensive YES on Polymarket
        poly_no = book([(0.20, 1000.0)])    # cheap NO on Polymarket
        kalshi_yes = book([(0.30, 1000.0)])  # cheap YES on Kalshi
        kalshi_no = book([(0.80, 1000.0)])
        dev, why = best_direction(poly_yes, poly_no, kalshi_yes, kalshi_no,
                                  size=10.0, days=0.0, costs=CONSERVATIVE)
        self.assertEqual(why, "ok")
        self.assertEqual(dev.direction, "yes_kalshi")
        self.assertGreater(dev.edge, 0.0)

    def test_an_unfillable_pair_names_both_failed_directions(self):
        thin = book([(0.40, 1.0)])
        dev, why = best_direction(thin, thin, thin, thin, size=25.0, days=0.0, costs=CONSERVATIVE)
        self.assertIsNone(dev)
        self.assertIn("thin", why)


def two_sided(ask, ask_size, bid, bid_size):
    return Book(asks=(Level(ask, ask_size),), bids=(Level(bid, bid_size),))


#: A pair quoted 0.40/0.38 on the leg bought YES and 0.55/0.53 on the leg bought NO.
YES_LEG = two_sided(0.40, 100, 0.38, 100)
NO_LEG = two_sided(0.55, 100, 0.53, 100)


class TestFourCrossingRoundTrip(unittest.TestCase):
    """Gate D.0's arithmetic. A convergence round trip crosses **four** books, not two.

    Class B bought two legs and let settlement pay the rest. Class C buys two and sells two, so it
    pays more transaction cost and less carry — and it is only better if the carry saved exceeds the
    two extra crossings. The registration expects it does not, which is exactly why this arithmetic
    must not be allowed to flatter itself.
    """

    def test_the_gross_gap_is_one_minus_both_ask_vwaps(self):
        rt = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=7.0, costs=CONSERVATIVE)
        self.assertAlmostEqual(rt.gross_gap, 1.0 - (0.40 + 0.55), places=9)

    def test_the_cost_is_entry_all_in_less_what_the_exit_actually_receives(self):
        rt = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=7.0, costs=CONSERVATIVE)
        entry = (CONSERVATIVE.effective_yes_cost_at(0.40, 7.0)
                 + CONSERVATIVE.effective_yes_cost_at(0.55, 7.0))
        exit_ = ((0.38 - CONSERVATIVE.fee(0.38)) + (0.53 - CONSERVATIVE.fee(0.53)))
        self.assertAlmostEqual(rt.entry_cost, entry, places=12)
        self.assertAlmostEqual(rt.exit_proceeds, exit_, places=12)
        self.assertAlmostEqual(rt.cost, entry - exit_, places=12)

    def test_carry_is_charged_over_the_holding_horizon_not_to_resolution(self):
        """AXIOMS C7, in the form that decides this class.

        Class C's whole economic claim is that it holds for 7 days instead of to settlement. An
        arithmetic that charged carry to resolution would erase the only advantage the hypothesis
        has, and would refute it for the wrong reason.
        """
        short = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=7.0, costs=CONSERVATIVE)
        long = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=114.0, costs=CONSERVATIVE)
        self.assertLess(short.cost, long.cost, "a shorter hold must cost less carry")
        base_yes = 0.40 + CONSERVATIVE.fee(0.40)
        base_no = 0.55 + CONSERVATIVE.fee(0.55)
        expected = ((CONSERVATIVE.carry(base_yes, 114.0) - CONSERVATIVE.carry(base_yes, 7.0))
                    + (CONSERVATIVE.carry(base_no, 114.0) - CONSERVATIVE.carry(base_no, 7.0)))
        self.assertAlmostEqual(long.cost - short.cost, expected, places=12)

    def test_carry_is_not_charged_a_second_time_on_the_exit(self):
        """The exit is a sale, not a holding. Charging carry there would double-count it."""
        short = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=7.0, costs=CONSERVATIVE)
        long = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=114.0, costs=CONSERVATIVE)
        self.assertAlmostEqual(short.exit_proceeds, long.exit_proceeds, places=12,
                               msg="exit proceeds must not depend on how long the position was held")

    def test_a_round_trip_into_the_same_books_always_costs_money(self):
        """Buying the ask and selling the bid at the same instant is a loss, never free."""
        rt = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=7.0, costs=CONSERVATIVE)
        self.assertGreater(rt.cost, 0.0)

    def test_it_carries_the_traded_prices_so_the_longshot_exclusion_can_be_applied(self):
        """PROTOCOL's market-selection preconditions exclude longshots **at every gate**.

        ``price_in_band`` is enforced in ``kairos.gate`` and ``kairos.sizing`` and in no scanner, so
        a caller measuring cross-venue prices has to apply it itself -- which it cannot do unless the
        round trip reports what it actually traded at.
        """
        rt = round_trip_cost(YES_LEG, NO_LEG, size=25, days_held=7.0, costs=CONSERVATIVE)
        self.assertAlmostEqual(rt.yes_vwap, 0.40, places=9)
        self.assertAlmostEqual(rt.no_vwap, 0.55, places=9)
        self.assertTrue(CONSERVATIVE.price_in_band(rt.yes_vwap))

    def test_a_longshot_leg_is_reported_at_its_traded_price_not_silently_dropped(self):
        """The refusal is the caller's to make. Dropping it here would hide it from the census."""
        rt = round_trip_cost(two_sided(0.02, 100, 0.01, 100), NO_LEG,
                             size=25, days_held=7.0, costs=CONSERVATIVE)
        self.assertAlmostEqual(rt.yes_vwap, 0.02, places=9)
        self.assertFalse(CONSERVATIVE.price_in_band(rt.yes_vwap))

    def test_a_thin_leg_on_any_of_the_four_walks_is_a_named_refusal(self):
        cases = {
            "thin_yes_entry": (two_sided(0.40, 1, 0.38, 100), NO_LEG),
            "thin_no_entry": (YES_LEG, two_sided(0.55, 1, 0.53, 100)),
            "thin_yes_exit": (two_sided(0.40, 100, 0.38, 1), NO_LEG),
            "thin_no_exit": (YES_LEG, two_sided(0.55, 100, 0.53, 1)),
        }
        for expected, (yes_leg, no_leg) in cases.items():
            with self.subTest(expected):
                out = round_trip_cost(yes_leg, no_leg, size=25, days_held=7.0, costs=CONSERVATIVE)
                self.assertEqual(out, expected)

    def test_an_exit_that_cannot_be_filled_is_refused_rather_than_priced_at_the_touch(self):
        """A position that cannot be closed at size is an outright bet, not a convergence trade."""
        out = round_trip_cost(two_sided(0.40, 100, 0.38, 1), NO_LEG,
                              size=25, days_held=7.0, costs=CONSERVATIVE)
        self.assertIsInstance(out, str)


class TestGateD0Verdict(unittest.TestCase):
    """The registered decision rule: *if the largest observed gap does not exceed the median
    round-trip cost, Class C is refuted and no convergence pipeline is built.*

    The direction of this inequality decides a hypothesis class, so it is pinned rather than
    trusted to prose.
    """

    def test_a_largest_gap_below_the_median_round_trip_refutes_the_class(self):
        v = gate_d0_verdict(gaps=[0.01, 0.02, 0.03], round_trips=[0.10, 0.13, 0.16])
        self.assertEqual(v.verdict, "REFUTED")
        self.assertAlmostEqual(v.largest_gap, 0.03, places=12)
        self.assertAlmostEqual(v.median_round_trip, 0.13, places=12)

    def test_a_largest_gap_above_the_median_round_trip_does_not_refute(self):
        v = gate_d0_verdict(gaps=[0.01, 0.20], round_trips=[0.10, 0.13, 0.16])
        self.assertEqual(v.verdict, "NOT REFUTED")

    def test_an_exactly_equal_gap_refutes_because_it_does_not_exceed(self):
        v = gate_d0_verdict(gaps=[0.13], round_trips=[0.13])
        self.assertEqual(v.verdict, "REFUTED")

    def test_the_comparison_is_the_largest_gap_not_the_median_gap(self):
        """Pinned because median-vs-median flips this case, and would be the natural slip."""
        gaps, trips = [0.001, 0.001, 0.30], [0.10, 0.13, 0.16]
        self.assertEqual(gate_d0_verdict(gaps=gaps, round_trips=trips).verdict, "NOT REFUTED")

    def test_no_pairs_is_no_verdict_rather_than_a_refutation(self):
        """AXIOMS A1. An empty measurement is 'not enough evidence', never 'no effect'."""
        v = gate_d0_verdict(gaps=[], round_trips=[])
        self.assertEqual(v.verdict, "NO VERDICT")
        self.assertIsNone(v.largest_gap)
        self.assertEqual(v.pairs, 0)

    def test_gaps_without_any_priced_round_trip_is_also_no_verdict(self):
        v = gate_d0_verdict(gaps=[0.05], round_trips=[])
        self.assertEqual(v.verdict, "NO VERDICT")


class TestBlocking(unittest.TestCase):
    def test_blocking_uses_a_key_the_comparison_already_requires(self):
        left = [polymarket_descriptor(POLY)]
        right = [kalshi_descriptor(KALSHI_EVENT, KALSHI_MARKET)]
        blocks = date_blocks(left, right)
        self.assertIn("2027-03-31", blocks)
        self.assertEqual((len(blocks["2027-03-31"][0]), len(blocks["2027-03-31"][1])), (1, 1))

    def test_a_descriptor_with_no_instant_is_dropped_from_blocking(self):
        d = kalshi_descriptor(KALSHI_EVENT, dict(KALSHI_MARKET, close_time=""))
        self.assertEqual(date_blocks([], [d]), {})

    def test_days_until_refuses_a_malformed_timestamp(self):
        self.assertIsNone(days_until("not-a-date"))
        self.assertIsNone(days_until(None))


if __name__ == "__main__":
    unittest.main()
