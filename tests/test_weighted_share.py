"""Flow-weighted share with an interval, because two point estimates are not a comparison.

``docs/PROTOCOL.md`` Class K. Gate K.0 compares Kalshi's share of flow with room to quote against
Polymarket's measured 22.6%. Comparing two bare numbers is how Gate M's null gate failed on a point
estimate (``CORRECTIONS.md`` Pass 29): medians right, single replications wrong 20-47% of the time.
The unit resampled here is the **market**, which is the independent unit -- not a time block.
"""

from __future__ import annotations

import unittest

from kairos.inference import weighted_share_ci


class TestWeightedShareCI(unittest.TestCase):
    def test_a_unanimous_sample_has_a_degenerate_interval(self):
        lo, hi = weighted_share_ci([True] * 60, [1.0] * 60, seed=1)
        self.assertAlmostEqual(lo, 1.0, places=12)
        self.assertAlmostEqual(hi, 1.0, places=12)

    def test_an_empty_sample_of_the_property_is_zero_throughout(self):
        lo, hi = weighted_share_ci([False] * 60, [1.0] * 60, seed=1)
        self.assertAlmostEqual(hi, 0.0, places=12)

    def test_the_interval_brackets_the_point_estimate(self):
        flags = [True] * 30 + [False] * 70
        w = [1.0] * 100
        lo, hi = weighted_share_ci(flags, w, seed=7)
        self.assertLess(lo, 0.30)
        self.assertGreater(hi, 0.30)

    def test_weight_decides_the_share_not_the_count(self):
        """Pass 28.1: one heavy market outvotes ninety-nine light ones."""
        flags = [True] + [False] * 99
        heavy = weighted_share_ci(flags, [999.0] + [1.0] * 99, seed=3)
        even = weighted_share_ci(flags, [1.0] * 100, seed=3)
        self.assertGreater(heavy[1], 0.9, "the heavy market must be able to carry the share")
        self.assertLess(even[1], 0.2, "with equal weight one market of a hundred cannot")

    def test_a_share_carried_by_one_unit_has_an_enormous_interval(self):
        """Not a defect -- the honest answer. A resample of 100 units omits any given one in
        (99/100)^100 ~ 37% of draws, so a share resting on a single market is barely estimated
        at all. A point estimate of 0.91 here would be a lie of precision."""
        lo, hi = weighted_share_ci([True] + [False] * 99, [999.0] + [1.0] * 99, seed=3)
        self.assertLess(lo, 0.1)
        self.assertGreater(hi - lo, 0.8, "concentration of weight must widen the interval")

    def test_a_wider_sample_gives_a_tighter_interval(self):
        small = weighted_share_ci([True] * 15 + [False] * 15, [1.0] * 30, seed=5)
        large = weighted_share_ci([True] * 500 + [False] * 500, [1.0] * 1000, seed=5)
        self.assertLess(large[1] - large[0], small[1] - small[0])

    def test_too_few_units_yields_no_interval_rather_than_a_fake_one(self):
        self.assertIsNone(weighted_share_ci([True, False], [1.0, 1.0], seed=1))

    def test_zero_total_weight_yields_no_interval(self):
        self.assertIsNone(weighted_share_ci([True] * 60, [0.0] * 60, seed=1))

    def test_mismatched_lengths_are_refused(self):
        with self.assertRaises(ValueError):
            weighted_share_ci([True, False], [1.0], seed=1)


if __name__ == "__main__":
    unittest.main()
