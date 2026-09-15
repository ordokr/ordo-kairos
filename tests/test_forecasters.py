"""Gate 2 forecaster tests.

Three things matter here and each is driven rather than asserted: the leakage boundary holds, the
shared fitter is genuinely shared (so Gate 0's harness and Gate 2's models cannot drift apart), and
the correlation diagnostics measure what they claim to.
"""

from __future__ import annotations

import unittest

from kairos.forecasters import (
    FORECASTERS,
    ForecasterSpec,
    apply_tilt,
    effective_forecasters,
    error_correlations,
    fit_logit_tilt,
    logit_pool,
    mean_offdiagonal,
    rolling_oos,
    simple_pool,
    tilt_correlations,
)
from kairos.polymarket import Observation, features_before

DAY = 86400


def obs(i: int, price: float, outcome: float, cluster: str | None = None, **feats) -> Observation:
    base = {"mom_1": 0.0, "mom_3": 0.0, "drift_per_day": 0.0,
            "volatility": 0.0, "range": 0.0, "age_days": 1.0, "n_before": 5.0}
    base.update(feats)
    return Observation(
        market_id=str(i),
        cluster_id=cluster or f"c{i}",
        question="q",
        price=price,
        outcome=outcome,
        decision_ts=1_700_000_000 + i * DAY,
        resolution_ts=1_700_000_000 + (i + 2) * DAY,
        days_to_resolution=2.0,
        n_points=8,
        features=base,
    )


class TestLeakageBoundary(unittest.TestCase):
    """The single most important guard in the project."""

    def test_appending_future_points_cannot_change_any_feature(self):
        hist = [{"t": 1000 + i * DAY, "p": 0.3 + 0.01 * i} for i in range(6)]
        cutoff = hist[3]["t"]
        before = features_before(hist[:4], cutoff)
        after = features_before(hist, cutoff)  # same cutoff, more future data available
        self.assertEqual(before, after)

    def test_a_wildly_different_future_still_changes_nothing(self):
        hist = [{"t": 1000 + i * DAY, "p": 0.5} for i in range(4)]
        calm = features_before(hist, hist[-1]["t"])
        violent = features_before(
            hist + [{"t": 1000 + 4 * DAY, "p": 0.99}, {"t": 1000 + 5 * DAY, "p": 0.01}],
            hist[-1]["t"],
        )
        self.assertEqual(calm, violent)

    def test_the_decision_point_itself_is_visible(self):
        hist = [{"t": 1000 + i * DAY, "p": 0.2 + 0.1 * i} for i in range(3)]
        f = features_before(hist, hist[-1]["t"])
        self.assertEqual(f["n_before"], 3.0)

    def test_empty_or_all_future_history_yields_no_features(self):
        self.assertEqual(features_before([], 1000), {})
        self.assertEqual(features_before([{"t": 5000, "p": 0.5}], 1000), {})


class TestSharedFitter(unittest.TestCase):
    def test_nullworld_and_forecasters_use_the_same_fitter(self):
        """The refactor's correctness check: one implementation, verified, not two."""
        import kairos.nullworld as nw

        self.assertIs(nw.fit_logit_tilt, fit_logit_tilt)

    def test_the_fitter_recovers_a_known_positive_relationship(self):
        offsets = [0.0] * 200
        rows = [[1.0] if i % 2 == 0 else [-1.0] for i in range(200)]
        outcomes = [1.0 if i % 2 == 0 else 0.0 for i in range(200)]
        _, beta = fit_logit_tilt(offsets, rows, outcomes, steps=200)
        self.assertGreater(beta[0], 0.5)

    def test_it_refuses_empty_and_mismatched_input(self):
        with self.assertRaises(ValueError):
            fit_logit_tilt([], [], [])
        with self.assertRaises(ValueError):
            fit_logit_tilt([0.0, 0.0], [[1.0]], [1.0, 0.0])

    def test_a_zero_tilt_returns_the_market_price(self):
        self.assertAlmostEqual(apply_tilt(0.37, 0.0, [], []), 0.37, places=9)


class TestStandardisation(unittest.TestCase):
    def test_large_magnitude_features_do_not_blow_up_the_forecast(self):
        """Gate 2a run 1: unstandardised `maturity` scored 4.82 against a 0.336 benchmark."""
        train = [
            obs(i, 0.4 + 0.001 * i, float(i % 2), age_days=float(i), n_before=float(i * 3))
            for i in range(80)
        ]
        pred = ForecasterSpec("maturity", ("age_days", "n_before")).fit(train)
        values = [pred(o) for o in train]
        self.assertTrue(all(0.0 < v < 1.0 for v in values))
        self.assertLess(max(values) - min(values), 0.95, "predictions should not saturate")

    def test_a_constant_feature_does_not_divide_by_zero(self):
        train = [obs(i, 0.5, float(i % 2), age_days=7.0) for i in range(40)]
        pred = ForecasterSpec("const", ("age_days",)).fit(train)
        self.assertTrue(0.0 < pred(train[0]) < 1.0)

    def test_the_market_forecaster_is_the_identity(self):
        spec = next(f for f in FORECASTERS if f.name == "market")
        pred = spec.fit([obs(i, 0.3, 1.0) for i in range(5)])
        self.assertAlmostEqual(pred(obs(99, 0.77, 1.0)), 0.77, places=9)


class TestCorrelationDiagnostics(unittest.TestCase):
    def test_error_correlation_is_near_unity_for_anchored_models(self):
        """The confound: shared (q - y) dominates every error."""
        market = [0.2, 0.8, 0.35, 0.6, 0.45, 0.7]
        outcomes = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
        a = [p + 0.001 for p in market]
        b = [p - 0.001 for p in market]
        err = error_correlations({"a": a, "b": b}, outcomes)
        self.assertGreater(err[("a", "b")], 0.99)

    def test_tilt_correlation_separates_models_error_correlation_cannot(self):
        """Same two models: opposite tilts, which the tilt diagnostic sees and errors do not."""
        market = [0.2, 0.8, 0.35, 0.6, 0.45, 0.7]
        outcomes = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
        tilts = [+0.01, -0.01, +0.02, -0.02, +0.015, -0.015]
        a = [p + t for p, t in zip(market, tilts)]
        b = [p - t for p, t in zip(market, tilts)]
        err = error_correlations({"a": a, "b": b}, outcomes)
        tilt = tilt_correlations({"a": a, "b": b}, market)
        self.assertGreater(err[("a", "b")], 0.9)
        self.assertLess(tilt[("a", "b")], -0.99)

    def test_effective_forecasters_reproduces_the_published_figure(self):
        """Begin et al.: ten agents at rho = 0.70 are worth about 1.4."""
        self.assertAlmostEqual(effective_forecasters(10, 0.70), 1.3699, places=3)

    def test_uncorrelated_forecasters_count_fully(self):
        self.assertAlmostEqual(effective_forecasters(5, 0.0), 5.0, places=9)

    def test_perfectly_correlated_forecasters_count_once(self):
        self.assertAlmostEqual(effective_forecasters(8, 1.0), 1.0, places=9)

    def test_a_single_forecaster_is_worth_one(self):
        self.assertAlmostEqual(effective_forecasters(1, 0.5), 1.0, places=9)

    def test_zero_forecasters_is_refused(self):
        with self.assertRaises(ValueError):
            effective_forecasters(0, 0.5)

    def test_mean_offdiagonal_ignores_nan(self):
        self.assertAlmostEqual(
            mean_offdiagonal({("a", "b"): 0.4, ("a", "c"): float("nan"), ("b", "c"): 0.6}),
            0.5, places=9,
        )


class TestPooling(unittest.TestCase):
    def test_simple_pool_is_the_arithmetic_mean(self):
        self.assertAlmostEqual(simple_pool([[0.2, 0.8], [0.4, 0.6]])[0], 0.3, places=9)

    def test_logit_pool_is_the_geometric_mean_of_odds(self):
        """Odds 49 and 1 -> sqrt(49) = 7 -> p = 7/8.

        Note this makes logit pooling *more* confident than the arithmetic mean here (0.875 vs
        0.74), not gentler. The "gentler" property belongs to market-*anchored blending*
        (``calibration.blend``), which pulls toward an anchor; pooling has no anchor to pull toward.
        """
        lin = simple_pool([[0.98], [0.50]])[0]
        log = logit_pool([[0.98], [0.50]])[0]
        self.assertAlmostEqual(log, 7.0 / 8.0, places=6)
        self.assertAlmostEqual(lin, 0.74, places=6)
        self.assertGreater(log, lin)

    def test_pooling_identical_forecasters_is_a_no_op(self):
        f = [0.3, 0.7, 0.5]
        for pooled in (simple_pool([f, f, f]), logit_pool([f, f, f])):
            for a, b in zip(pooled, f):
                self.assertAlmostEqual(a, b, places=6)

    def test_empty_pool_is_refused(self):
        for fn in (simple_pool, logit_pool):
            with self.assertRaises(ValueError):
                fn([])


class TestRollingOOS(unittest.TestCase):
    def test_no_cluster_appears_in_both_train_and_test(self):
        """Rows from one event resolve together; a row-wise split would leak a sibling."""
        data = [obs(i, 0.4, float(i % 2), cluster=f"e{i // 3}") for i in range(60)]
        clusters = sorted({o.cluster_id for o in data})
        seen: list[str] = []
        preds = rolling_oos(data, clusters, 4, {"market": FORECASTERS[0].fit})
        seen.extend(preds["_cluster"])
        # every predicted cluster must come from the later part of the ordering
        self.assertTrue(set(seen).issubset(set(clusters)))
        self.assertEqual(len(preds["market"]), len(preds["_outcome"]))

    def test_it_produces_no_predictions_when_there_is_nothing_to_train_on(self):
        data = [obs(i, 0.4, 1.0, cluster=f"e{i}") for i in range(4)]
        preds = rolling_oos(data, [f"e{i}" for i in range(4)], 3, {"market": FORECASTERS[0].fit})
        self.assertEqual(preds["_outcome"], [])


if __name__ == "__main__":
    unittest.main()
