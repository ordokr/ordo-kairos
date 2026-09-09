"""Tests for the primary statistical test.

The central assertion is not that the code runs but that **ignoring clustering inflates
significance**, which is the empirical content of AXIOMS C3/C4. That is driven here rather than
asserted, on data whose dependence structure is known by construction.
"""

from __future__ import annotations

import random
import unittest

from kairos.inference import (
    FEW_CLUSTERS,
    MIN_STRATUM_CLUSTERS,
    InferenceError,
    cluster_bootstrap_test,
    cluster_mean_and_se,
    iid_bootstrap_test,
    max_statistic_test,
    paired_deltas,
    superiority_test,
    wild_cluster_bootstrap_test,
)


class TestPairedDeltas(unittest.TestCase):
    def test_a_better_forecaster_produces_positive_deltas(self):
        outcomes = [1.0, 0.0, 1.0, 0.0]
        good = [0.9, 0.1, 0.9, 0.1]
        poor = [0.5, 0.5, 0.5, 0.5]
        deltas = paired_deltas(good, poor, outcomes)
        self.assertTrue(all(d > 0 for d in deltas), deltas)

    def test_a_worse_forecaster_produces_negative_deltas(self):
        outcomes = [1.0, 0.0]
        deltas = paired_deltas([0.2, 0.8], [0.5, 0.5], outcomes)
        self.assertTrue(all(d < 0 for d in deltas), deltas)

    def test_identical_forecasts_produce_exactly_zero(self):
        f = [0.3, 0.7, 0.5]
        deltas = paired_deltas(f, f, [1.0, 0.0, 1.0])
        self.assertEqual(deltas, [0.0, 0.0, 0.0])

    def test_mismatched_lengths_are_refused(self):
        with self.assertRaises(InferenceError):
            paired_deltas([0.5, 0.5], [0.5], [1.0, 0.0])


class TestClusterStandardError(unittest.TestCase):
    def test_perfectly_clustered_data_has_a_much_larger_se_than_iid_assumes(self):
        """500 rows across 5 events carry 5 events' worth of information, not 500 rows' worth."""
        deltas = []
        clusters = []
        for event, value in enumerate([0.10, -0.05, 0.08, -0.02, 0.06]):
            deltas.extend([value] * 100)
            clusters.extend([event] * 100)

        _, cluster_se, g = cluster_mean_and_se(deltas, clusters)
        self.assertEqual(g, 5)

        iid = iid_bootstrap_test(deltas, n_boot=400, seed=1)
        self.assertGreater(
            cluster_se,
            5 * iid.cluster_se,
            "cluster SE must dwarf the IID SE when every cluster is internally identical",
        )

    def test_the_iid_test_declares_significance_where_the_cluster_test_does_not(self):
        """The concrete failure AXIOMS C3 exists to prevent."""
        deltas = []
        clusters = []
        for event, value in enumerate([0.10, -0.05, 0.08, -0.02, 0.06]):
            deltas.extend([value] * 100)
            clusters.extend([event] * 100)

        iid = iid_bootstrap_test(deltas, n_boot=1000, seed=1)
        clustered = wild_cluster_bootstrap_test(deltas, clusters, n_boot=1000, seed=1)
        self.assertTrue(iid.significant)
        self.assertFalse(clustered.significant)

    def test_single_cluster_is_refused(self):
        with self.assertRaises(InferenceError):
            cluster_bootstrap_test([0.1] * 10, [0] * 10, n_boot=50)

    def test_mismatched_lengths_are_refused(self):
        with self.assertRaises(InferenceError):
            cluster_mean_and_se([0.1, 0.2], [0])

    def test_empty_input_is_refused(self):
        with self.assertRaises(InferenceError):
            cluster_mean_and_se([], [])


class TestSuperiorityTest(unittest.TestCase):
    def test_a_genuinely_better_forecaster_is_detected(self):
        forecasts, benchmark, outcomes, clusters = [], [], [], []
        for event in range(60):
            y = 1.0 if event % 2 == 0 else 0.0
            for _ in range(4):
                forecasts.append(0.8 if y else 0.2)
                benchmark.append(0.5)
                outcomes.append(y)
                clusters.append(event)
        result = superiority_test(forecasts, benchmark, outcomes, clusters, n_boot=400, seed=1)
        self.assertTrue(result.significant, result.explain())
        self.assertGreater(result.mean_delta, 0.0)

    def test_an_identical_forecaster_is_not_declared_superior(self):
        f = [0.4, 0.6] * 60
        outcomes = [1.0, 0.0] * 60
        clusters = [i // 2 for i in range(120)]
        result = superiority_test(f, f, outcomes, clusters, n_boot=400, seed=1)
        self.assertFalse(result.significant)
        self.assertAlmostEqual(result.mean_delta, 0.0, places=12)

    @staticmethod
    def _varying(n_clusters: int):
        """Non-degenerate paired data: the forecaster differs slightly, per cluster."""
        forecasts, benchmark, outcomes, clusters = [], [], [], []
        for event in range(n_clusters):
            y = 1.0 if event % 3 else 0.0
            for j in range(4):
                forecasts.append(0.50 + 0.01 * ((event + j) % 7))
                benchmark.append(0.50)
                outcomes.append(y)
                clusters.append(event)
        return forecasts, benchmark, outcomes, clusters

    def test_it_selects_the_wild_bootstrap_when_clusters_are_few(self):
        result = superiority_test(*self._varying(FEW_CLUSTERS - 10), n_boot=100, seed=1)
        self.assertEqual(result.method, "wild-cluster-bootstrap")

    def test_it_selects_the_pairs_bootstrap_when_clusters_are_many(self):
        result = superiority_test(*self._varying(FEW_CLUSTERS + 20), n_boot=100, seed=1)
        self.assertEqual(result.method, "pairs-cluster-bootstrap")

    def test_the_wild_bootstrap_refuses_degenerate_zero_variance_input(self):
        """Identical forecasts carry no information; refusing beats reporting a spurious p."""
        f = [0.5] * 40
        clusters = [i // 4 for i in range(40)]
        with self.assertRaises(InferenceError):
            wild_cluster_bootstrap_test([0.0] * 40, clusters, n_boot=50)

    def test_p_values_are_never_exactly_zero(self):
        """The +1 correction keeps a bootstrap p-value honest about its own resolution."""
        forecasts, benchmark, outcomes, clusters = [], [], [], []
        for event in range(60):
            y = 1.0 if event % 2 == 0 else 0.0
            for _ in range(4):
                forecasts.append(0.99 if y else 0.01)
                benchmark.append(0.5)
                outcomes.append(y)
                clusters.append(event)
        result = superiority_test(forecasts, benchmark, outcomes, clusters, n_boot=200, seed=1)
        self.assertGreater(result.p_value, 0.0)

    def test_significance_requires_a_positive_effect_not_just_a_small_p(self):
        result = superiority_test(
            [0.2] * 200, [0.5] * 200, [1.0] * 200, [i // 4 for i in range(200)],
            n_boot=200, seed=1,
        )
        self.assertLess(result.mean_delta, 0.0)
        self.assertFalse(result.significant)

    def test_the_iid_method_name_warns_against_its_own_use(self):
        result = iid_bootstrap_test([0.01] * 50, n_boot=100, seed=1)
        self.assertIn("INVALID", result.method)


class TestMaxStatisticTest(unittest.TestCase):
    """The correction has to be driven, not asserted.

    The claim being tested is empirical: searching five strata and reporting the winner rejects a
    true null far more often than the nominal rate, and the max-t reference distribution pulls that
    back. Both halves are measured on data built to contain no effect.
    """

    @staticmethod
    def _null_sample(seed, n_clusters=200, n_strata=5):
        """Pure noise, clustered, evenly spread over strata. No effect in any stratum."""
        rng = random.Random(seed)
        deltas, clusters, strata = [], [], []
        for c in range(n_clusters):
            shift = rng.gauss(0.0, 0.05)  # a cluster-level common component
            for _ in range(3):
                deltas.append(shift + rng.gauss(0.0, 0.2))
                clusters.append(c)
                strata.append(f"s{rng.randrange(n_strata)}")
        return deltas, clusters, strata

    def test_searching_strata_over_rejects_and_the_correction_pulls_it_back(self):
        naive_hits = corrected_hits = 0
        trials = 40
        for t in range(trials):
            d, c, s = self._null_sample(seed=5000 + t)
            r = max_statistic_test(d, c, s, n_boot=300, seed=t, min_clusters=10)
            naive_hits += r.significant_uncorrected
            corrected_hits += r.significant
        naive_rate = naive_hits / trials
        corrected_rate = corrected_hits / trials
        self.assertGreater(
            naive_rate, corrected_rate,
            f"the uncorrected search should reject more often; got naive {naive_rate:.3f} "
            f"vs corrected {corrected_rate:.3f}",
        )
        self.assertLessEqual(
            corrected_rate, 0.20,
            f"corrected rate {corrected_rate:.3f} is far above nominal 0.05 on a pure null",
        )

    def test_the_corrected_p_is_never_smaller_than_the_uncorrected_one(self):
        d, c, s = self._null_sample(seed=99)
        r = max_statistic_test(d, c, s, n_boot=400, seed=1, min_clusters=10)
        self.assertGreaterEqual(r.p_corrected, r.p_uncorrected - 1e-12)

    def test_a_real_effect_in_one_stratum_survives_the_correction(self):
        """Power check: the correction must cost something, not everything."""
        rng = random.Random(7)
        deltas, clusters, strata = [], [], []
        for c in range(300):
            band = f"s{c % 5}"
            for _ in range(3):
                lift = 0.25 if band == "s2" else 0.0
                deltas.append(lift + rng.gauss(0.0, 0.2))
                clusters.append(c)
                strata.append(band)
        r = max_statistic_test(deltas, clusters, strata, n_boot=400, seed=2, min_clusters=10)
        self.assertEqual(r.best.name, "s2")
        self.assertTrue(r.significant, r.explain())

    def test_thin_strata_are_excluded_and_reported(self):
        d, c, s = self._null_sample(seed=11, n_clusters=60, n_strata=2)
        d += [0.1] * 3
        c += [9001, 9002, 9003]
        s += ["tiny"] * 3
        r = max_statistic_test(d, c, s, n_boot=100, seed=0, min_clusters=MIN_STRATUM_CLUSTERS)
        self.assertIn("tiny", [name for name, _ in r.excluded])
        self.assertNotIn("tiny", [x.name for x in r.strata])

    def test_it_refuses_when_no_stratum_is_large_enough(self):
        with self.assertRaises(InferenceError):
            max_statistic_test([0.1, 0.2], [1, 2], ["a", "b"], n_boot=50, min_clusters=20)

    def test_it_refuses_mismatched_lengths(self):
        with self.assertRaises(InferenceError):
            max_statistic_test([0.1, 0.2], [1, 2], ["a"], n_boot=50)


if __name__ == "__main__":
    unittest.main()
