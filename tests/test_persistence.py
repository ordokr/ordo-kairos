"""Subsidy persistence: cohort succession, revision direction, and a hazard that is only a bound.

``docs/PROTOCOL.md`` Class S. This module does **not** forecast whether Polymarket keeps paying. It
measures whether the venue's schedule versions are a temporal succession at all, what past revisions
did to the maker's take, and what an upper bound on the withdrawal hazard looks like when the number
of observed withdrawals is **zero**.

The trap this file exists to hold shut: a *signed* mean of revision deltas averages a randomly
churning programme to approximately zero and calls it stability. Direction and instability are
therefore separate statistics, and the churn world in ``gates.py`` fails on the second.
"""

from __future__ import annotations

import random
import unittest

from kairos.persistence import (
    annual_hazard_bound,
    detect_succession,
    maker_take,
    months_between,
    parse_schedule_version,
    rule_of_three,
    separation_auc,
    take_pair,
    weighted_direction,
    weighted_instability,
)


class TestParseScheduleVersion(unittest.TestCase):
    def test_a_version_suffix_splits_into_family_and_number(self):
        self.assertEqual(parse_schedule_version("sports_fees_v3"), ("sports_fees", 3))
        self.assertEqual(parse_schedule_version("crypto_fees_v2"), ("crypto_fees", 2))

    def test_an_unversioned_schedule_is_implicitly_version_one(self):
        """`politics_fees` has no suffix. It is the first version, not a missing one."""
        self.assertEqual(parse_schedule_version("politics_fees"), ("politics_fees", 1))
        self.assertEqual(parse_schedule_version("finance_prices_fees"), ("finance_prices_fees", 1))

    def test_a_family_with_an_underscore_v_that_is_not_a_version_is_not_split(self):
        self.assertEqual(parse_schedule_version("vote_fees"), ("vote_fees", 1))

    def test_empty_and_missing_names_are_refused_rather_than_guessed(self):
        for bad in ("", None):
            self.assertIsNone(parse_schedule_version(bad))


class TestMakerTake(unittest.TestCase):
    """The declared invariant from the registration, which must be computed and not asserted."""

    def test_the_two_sports_schedules_pay_the_maker_identically(self):
        self.assertAlmostEqual(maker_take(0.03, 0.25), maker_take(0.05, 0.15), places=12)
        self.assertAlmostEqual(maker_take(0.03, 0.25), 0.0075, places=12)

    def test_it_is_the_product_because_the_price_factor_is_common_to_both(self):
        self.assertAlmostEqual(maker_take(0.07, 0.20), 0.014, places=12)

    def test_a_fee_free_schedule_pays_no_rebate(self):
        self.assertEqual(maker_take(0.0, 0.25), 0.0)

    def test_negative_terms_are_refused(self):
        with self.assertRaises(ValueError):
            maker_take(-0.01, 0.25)


class TestTakesAreOnlyComparableAtEqualExponent(unittest.TestCase):
    """`crypto_15_min` is live at `exponent: 2`, where the fee is `rate x (p(1-p))^2`.

    Stripping the price factor is what makes two schedules' takes comparable, and it only works
    when the factor is the same. At differing exponents `rate x rebateRate` is not a smaller or
    larger take -- it is a quantity in different units, and comparing them is meaningless.
    """

    def test_equal_exponents_compare_normally(self):
        self.assertEqual(take_pair((0.03, 0.25, 1), (0.05, 0.15, 1)), (0.0075, 0.0075))

    def test_differing_exponents_are_refused_rather_than_silently_compared(self):
        with self.assertRaises(ValueError):
            take_pair((0.03, 0.25, 1), (0.25, 0.20, 2))

    def test_the_refusal_names_the_exponent_so_it_is_not_mistaken_for_a_data_error(self):
        with self.assertRaises(ValueError) as ctx:
            take_pair((0.25, 0.20, 2), (0.03, 0.25, 1))
        self.assertIn("exponent", str(ctx.exception))


class TestSeparationAUC(unittest.TestCase):
    """Non-parametric: the probability that a later-version market was created after an earlier one.

    1.0 is clean succession, 0.5 is full interleaving, and the second is the confound that voids
    the whole measurement — so the statistic must be able to say 0.5.
    """

    def test_fully_separated_cohorts_score_one(self):
        self.assertAlmostEqual(separation_auc([1.0, 2.0, 3.0], [4.0, 5.0]), 1.0, places=12)

    def test_fully_reversed_cohorts_score_zero(self):
        self.assertAlmostEqual(separation_auc([4.0, 5.0], [1.0, 2.0, 3.0]), 0.0, places=12)

    def test_identical_cohorts_score_one_half_because_every_pair_is_a_tie(self):
        self.assertAlmostEqual(separation_auc([1.0, 1.0], [1.0, 1.0]), 0.5, places=12)

    def test_perfectly_interleaved_cohorts_sit_near_one_half(self):
        self.assertAlmostEqual(separation_auc([1.0, 3.0, 5.0], [2.0, 4.0, 6.0]), 2 / 3, places=12)

    def test_an_empty_cohort_has_no_statistic_rather_than_a_default(self):
        for a, b in (([], [1.0]), ([1.0], []), ([], [])):
            self.assertIsNone(separation_auc(a, b))


class TestRuleOfThree(unittest.TestCase):
    """Zero observed withdrawals bounds the hazard; it does not estimate it."""

    def test_the_bound_is_three_over_n(self):
        self.assertAlmostEqual(rule_of_three(30), 0.1, places=12)
        self.assertAlmostEqual(rule_of_three(300), 0.01, places=12)

    def test_more_observation_tightens_the_bound(self):
        self.assertLess(rule_of_three(120), rule_of_three(12))

    def test_too_little_observation_cannot_bound_a_probability_below_one(self):
        """With n < 3 the rule returns 1.0: the data excludes nothing."""
        self.assertEqual(rule_of_three(1), 1.0)
        self.assertEqual(rule_of_three(3), 1.0)

    def test_zero_observation_is_refused(self):
        with self.assertRaises(ValueError):
            rule_of_three(0)

    def test_a_monthly_bound_compounds_into_a_wider_annual_one(self):
        monthly = rule_of_three(120)          # 0.025
        self.assertGreater(annual_hazard_bound(monthly), monthly)
        self.assertAlmostEqual(annual_hazard_bound(monthly), 1 - (1 - 0.025) ** 12, places=12)

    def test_a_certain_monthly_bound_stays_certain_annually(self):
        self.assertAlmostEqual(annual_hazard_bound(1.0), 1.0, places=12)


class TestDirectionAndInstabilityAreSeparateStatistics(unittest.TestCase):
    """The trap. A signed mean averages churn to zero and reports stability.

    Direction answers "did revisions cut the maker's take?"; instability answers "did the terms move
    at all?". A programme that alternates +50% and -50% has a direction of ~0 and is not stable.
    """

    def test_a_flat_revision_has_neither_direction_nor_instability(self):
        deltas = [(0.0075, 0.0075)]
        self.assertAlmostEqual(weighted_direction(deltas, [1.0]), 0.0, places=12)
        self.assertAlmostEqual(weighted_instability(deltas, [1.0]), 0.0, places=12)

    def test_a_cut_shows_a_negative_direction(self):
        self.assertLess(weighted_direction([(0.010, 0.005)], [1.0]), 0.0)

    def test_churn_averages_to_no_direction_but_stays_unstable(self):
        churn = [(0.010, 0.015), (0.010, 0.005)]     # +50%, -50%
        self.assertAlmostEqual(weighted_direction(churn, [1.0, 1.0]), 0.0, places=12)
        self.assertAlmostEqual(weighted_instability(churn, [1.0, 1.0]), 0.5, places=12)

    def test_weighting_is_by_dollars_at_risk_not_by_pair_count(self):
        """Pass 28.1: weighting by the wrong unit passes a condition the exposure fails."""
        pairs = [(0.010, 0.010), (0.010, 0.005)]     # flat, then a halving
        by_count = weighted_direction(pairs, [1.0, 1.0])
        by_dollars = weighted_direction(pairs, [1.0, 99.0])
        self.assertLess(by_dollars, by_count, "the halving carries the exposure and must dominate")

    def test_zero_total_weight_yields_no_statistic(self):
        self.assertIsNone(weighted_direction([(0.01, 0.01)], [0.0]))
        self.assertIsNone(weighted_instability([(0.01, 0.01)], [0.0]))

    def test_mismatched_lengths_are_refused(self):
        with self.assertRaises(ValueError):
            weighted_direction([(0.01, 0.01)], [1.0, 1.0])

    def test_instability_is_undefined_where_there_was_no_subsidy_to_destabilise(self):
        """A relative change needs something to be relative to. Refused, not defaulted to zero."""
        with self.assertRaises(ValueError):
            weighted_instability([(0.0, 0.01)], [1.0])


class TestMonthsBetween(unittest.TestCase):
    """The unit of the whole gate (Pass 27.1: both sides of the comparison in months)."""

    def test_a_year_of_seconds_is_twelve_months(self):
        self.assertAlmostEqual(months_between(0.0, 365.2425 * 86400.0), 12.0, places=6)

    def test_it_is_never_negative(self):
        self.assertEqual(months_between(100.0, 0.0), 0.0)


class TestDetectSuccession(unittest.TestCase):
    """Cohorts must be separated *and* the separation must survive a label permutation."""

    def setUp(self):
        self.rng = random.Random(20260914)

    def test_a_clean_succession_is_detected(self):
        cohorts = {("sports_fees", 1): [float(i) for i in range(60)],
                   ("sports_fees", 2): [float(i) for i in range(100, 160)]}
        pairs = detect_succession(cohorts, auc_floor=0.90, alpha=0.05, rng=self.rng)
        self.assertEqual(len(pairs), 1)
        self.assertEqual((pairs[0].family, pairs[0].older, pairs[0].newer), ("sports_fees", 1, 2))
        self.assertAlmostEqual(pairs[0].auc, 1.0, places=12)

    def test_interleaved_cohorts_are_not_a_succession(self):
        """The confound the real data may contain. It must fail here, not be explained away."""
        a = [float(i) for i in range(0, 120, 2)]
        b = [float(i) for i in range(1, 120, 2)]
        cohorts = {("sports_fees", 1): a, ("sports_fees", 2): b}
        self.assertEqual(detect_succession(cohorts, auc_floor=0.90, alpha=0.05, rng=self.rng), [])

    def test_different_families_are_never_paired(self):
        cohorts = {("sports_fees", 1): [float(i) for i in range(60)],
                   ("crypto_fees", 2): [float(i) for i in range(100, 160)]}
        self.assertEqual(detect_succession(cohorts, auc_floor=0.90, alpha=0.05, rng=self.rng), [])

    def test_a_single_version_family_yields_no_pair(self):
        cohorts = {("politics_fees", 1): [float(i) for i in range(60)]}
        self.assertEqual(detect_succession(cohorts, auc_floor=0.90, alpha=0.05, rng=self.rng), [])

    def test_a_backwards_cohort_is_not_a_succession(self):
        """Version 2 markets older than version 1 markets: whatever that is, it is not succession."""
        cohorts = {("sports_fees", 1): [float(i) for i in range(100, 160)],
                   ("sports_fees", 2): [float(i) for i in range(60)]}
        self.assertEqual(detect_succession(cohorts, auc_floor=0.90, alpha=0.05, rng=self.rng), [])

    def test_cohorts_too_small_to_permute_are_refused_rather_than_asserted(self):
        cohorts = {("sports_fees", 1): [1.0], ("sports_fees", 2): [9.0]}
        self.assertEqual(detect_succession(cohorts, auc_floor=0.90, alpha=0.05, rng=self.rng), [])

    def test_consecutive_versions_only_so_v1_to_v3_is_not_invented(self):
        cohorts = {("sports_fees", 1): [float(i) for i in range(60)],
                   ("sports_fees", 2): [float(i) for i in range(100, 160)],
                   ("sports_fees", 3): [float(i) for i in range(200, 260)]}
        pairs = detect_succession(cohorts, auc_floor=0.90, alpha=0.05, rng=self.rng)
        self.assertEqual([(p.older, p.newer) for p in pairs], [(1, 2), (2, 3)])


if __name__ == "__main__":
    unittest.main()
