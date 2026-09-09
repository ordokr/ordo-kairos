"""Calibration tests.

The central claim under test is Le 2026's (arXiv 2602.19520) finding that prediction-market
forecasts show "persistent underconfidence... prices compress toward 50%". Compression is a
monotone distortion, so isotonic regression should undo it - and the test drives that end to end
by measuring whether the Brier score actually improves, not by inspecting the fitted knots.
"""

from __future__ import annotations

import unittest

from kairos.calibration import (
    BlendSpace,
    IsotonicCalibrator,
    blend,
    reliability,
)
from kairos.score import brier_score


def compressed_dataset(shrink: float = 0.6):
    """Deterministic dataset where reported forecasts are compressed toward 0.5."""
    true_ps = [0.1, 0.3, 0.5, 0.7, 0.9]
    reported: list[float] = []
    outcomes: list[float] = []
    per_bin = 100
    for tp in true_ps:
        rep = 0.5 + shrink * (tp - 0.5)
        n_ones = round(tp * per_bin)
        reported.extend([rep] * per_bin)
        outcomes.extend([1.0] * n_ones + [0.0] * (per_bin - n_ones))
    return reported, outcomes


class TestMarketAnchoring(unittest.TestCase):
    def test_zero_weight_returns_the_market_price_exactly(self):
        """The safe default: an unproven model gets no say whatsoever."""
        for market in (0.01, 0.25, 0.5, 0.9, 0.99):
            self.assertEqual(blend(market, model=0.99, weight=0.0), market)

    def test_full_weight_returns_the_model(self):
        self.assertAlmostEqual(blend(0.5, 0.8, weight=1.0, space=BlendSpace.LINEAR), 0.8, places=12)
        self.assertAlmostEqual(blend(0.5, 0.8, weight=1.0, space=BlendSpace.LOGIT), 0.8, places=9)

    def test_logit_blending_is_gentler_than_linear_near_the_extremes(self):
        """A confident model should not be able to yank a 0.98 market price as far in logit space."""
        market, model, w = 0.98, 0.50, 0.30
        linear = blend(market, model, w, BlendSpace.LINEAR)
        logit = blend(market, model, w, BlendSpace.LOGIT)
        self.assertLess(linear, logit)
        self.assertLess(logit, market)

    def test_out_of_range_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            blend(1.2, 0.5, 0.5)
        with self.assertRaises(ValueError):
            blend(0.5, 0.5, 1.5)


class TestIsotonicCalibration(unittest.TestCase):
    def test_unfitted_calibrator_is_the_identity(self):
        cal = IsotonicCalibrator()
        self.assertFalse(cal.fitted)
        for p in (0.0, 0.3, 0.77, 1.0):
            self.assertEqual(cal.predict(p), p)

    def test_it_undoes_compression_toward_fifty(self):
        reported, outcomes = compressed_dataset()
        cal = IsotonicCalibrator().fit(reported, outcomes)
        calibrated = [cal.predict(p) for p in reported]

        before = brier_score(reported, outcomes)
        after = brier_score(calibrated, outcomes)
        self.assertLess(after, before, "recalibration must improve the Brier score")

        # The extremes should be pushed back out toward the true rates.
        self.assertAlmostEqual(cal.predict(0.5 + 0.6 * (0.1 - 0.5)), 0.1, places=6)
        self.assertAlmostEqual(cal.predict(0.5 + 0.6 * (0.9 - 0.5)), 0.9, places=6)

    def test_it_never_reorders_two_forecasts(self):
        """Monotonicity is why calibration cannot invent discrimination it did not have."""
        reported, outcomes = compressed_dataset()
        cal = IsotonicCalibrator().fit(reported, outcomes)
        grid = [i / 200.0 for i in range(201)]
        preds = [cal.predict(p) for p in grid]
        for a, b in zip(preds, preds[1:]):
            self.assertLessEqual(a, b + 1e-12)

    def test_it_pools_violators_rather_than_fitting_noise(self):
        """Inverted input must collapse to a constant, not be fitted backwards."""
        forecasts = [0.2, 0.4, 0.6, 0.8]
        outcomes = [1.0, 1.0, 0.0, 0.0]  # perfectly anti-monotone
        cal = IsotonicCalibrator().fit(forecasts, outcomes)
        preds = [cal.predict(f) for f in forecasts]
        self.assertTrue(all(abs(p - 0.5) < 1e-9 for p in preds), preds)

    def test_mismatched_lengths_are_refused(self):
        with self.assertRaises(ValueError):
            IsotonicCalibrator().fit([0.1, 0.2], [1.0])

    def test_empty_fit_is_refused(self):
        with self.assertRaises(ValueError):
            IsotonicCalibrator().fit([], [])


class TestReliability(unittest.TestCase):
    def test_murphy_decomposition_identity_holds(self):
        reported, outcomes = compressed_dataset()
        rep = reliability(reported, outcomes, n_bins=10)
        self.assertAlmostEqual(rep.decomposition_residual, 0.0, places=9)

    def test_recalibration_cuts_reliability_but_not_resolution(self):
        """Calibration removes miscalibration; it must not manufacture information."""
        reported, outcomes = compressed_dataset()
        cal = IsotonicCalibrator().fit(reported, outcomes)
        calibrated = [cal.predict(p) for p in reported]

        before = reliability(reported, outcomes, n_bins=20)
        after = reliability(calibrated, outcomes, n_bins=20)
        self.assertLess(after.reliability, before.reliability)
        self.assertAlmostEqual(after.resolution, before.resolution, places=6)
        self.assertAlmostEqual(after.uncertainty, before.uncertainty, places=12)

    def test_a_perfectly_calibrated_forecaster_has_near_zero_ece(self):
        reported, outcomes = compressed_dataset(shrink=1.0)  # no compression
        rep = reliability(reported, outcomes, n_bins=10)
        self.assertLess(rep.ece, 1e-9)


if __name__ == "__main__":
    unittest.main()
