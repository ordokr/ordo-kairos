"""Tests for the Gate-0 harness.

A null world that is not actually null would let the pipeline pass for the wrong reason, so these
tests verify the *worlds* as carefully as the code: the market must be exactly calibrated where it
claims to be, outcomes must resolve once per event, and no event may appear in two splits.
"""

from __future__ import annotations

import unittest

from kairos.inference import paired_deltas
from kairos.nullworld import (
    PRICE_STRATA,
    GateReport,
    World,
    WorldReport,
    _binomial_tail,
    _split_by_cluster,
    achievable_oracle,
    add_noise_features,
    candidate_forecasters,
    fair_market,
    inject_banded_signal,
    inject_signal,
    martingale_market,
    microstructure_placebo,
    run_all_protocols,
    shuffle_outcomes,
    stratify_by_price,
    time_shift_features,
)


class TestNullWorldsAreActuallyNull(unittest.TestCase):
    def test_fair_market_quotes_the_truth_exactly(self):
        """If the quote differed from the truth, a knowledgeable forecaster could beat it."""
        w = fair_market(n_events=30, seed=3)
        self.assertIsNotNone(w.truth)
        for q, t in zip(w.market, w.truth):
            self.assertAlmostEqual(q, t, places=15)
        self.assertFalse(w.has_signal)

    def test_outcomes_resolve_once_per_event(self):
        w = fair_market(n_events=30, contracts_per_event=8, seed=3)
        by_event: dict[int, set[float]] = {}
        for c, y in zip(w.cluster_ids, w.outcomes):
            by_event.setdefault(c, set()).add(y)
        for c, values in by_event.items():
            self.assertEqual(len(values), 1, f"event {c} resolved inconsistently: {values}")

    def test_no_forecaster_beats_a_fair_market_on_average_across_worlds(self):
        """Strict propriety, driven across many seeds rather than assumed."""
        total = 0.0
        n = 0
        for seed in range(25):
            w = fair_market(n_events=40, contracts_per_event=6, seed=seed)
            tilted = [min(max(q + 0.05, 1e-6), 1 - 1e-6) for q in w.market]
            deltas = paired_deltas(tilted, w.market, w.outcomes)
            total += sum(deltas)
            n += len(deltas)
        self.assertLess(total / n, 0.0, "a fixed tilt must lose against a calibrated market")

    def test_shuffling_preserves_calibration_within_price_strata(self):
        """A global shuffle would break calibration and smuggle in a real edge."""
        w = fair_market(n_events=60, contracts_per_event=8, seed=5)
        s = shuffle_outcomes(w, seed=5, n_strata=10)
        self.assertEqual(sum(w.outcomes), sum(s.outcomes))
        for stratum in range(10):
            idx = [
                i for i, q in enumerate(w.market)
                if min(int(q * 10), 9) == stratum
            ]
            if idx:
                before = sum(w.outcomes[i] for i in idx)
                after = sum(s.outcomes[i] for i in idx)
                self.assertEqual(before, after, f"stratum {stratum} base rate changed")
        self.assertFalse(s.has_signal)

    def test_event_level_noise_features_are_constant_within_an_event(self):
        """The overfitting channel that matters with clustered outcomes."""
        w = add_noise_features(
            fair_market(n_events=20, contracts_per_event=5, seed=7),
            n_event_features=4, n_contract_features=2, seed=7,
        )
        by_event: dict[int, set[tuple[float, ...]]] = {}
        for c, row in zip(w.cluster_ids, w.features):
            by_event.setdefault(c, set()).add(tuple(row[:4]))
        for c, seen in by_event.items():
            self.assertEqual(len(seen), 1, f"event-level features varied within event {c}")

    def test_contract_level_noise_features_do_vary_within_an_event(self):
        w = add_noise_features(
            fair_market(n_events=20, contracts_per_event=5, seed=7),
            n_event_features=4, n_contract_features=2, seed=7,
        )
        tails = {tuple(row[4:]) for row in w.features[:5]}
        self.assertGreater(len(tails), 1)

    def test_every_null_world_declares_no_signal(self):
        worlds = [
            add_noise_features(fair_market(n_events=12, seed=1), seed=1),
            add_noise_features(martingale_market(n_events=12, seed=1), seed=1),
            add_noise_features(shuffle_outcomes(fair_market(n_events=12, seed=1), seed=2), seed=1),
            time_shift_features(add_noise_features(fair_market(n_events=12, seed=1), seed=1)),
            add_noise_features(microstructure_placebo(n_events=12, seed=1), seed=1),
        ]
        for w in worlds:
            self.assertFalse(w.has_signal, w.name)


class TestPositiveControl(unittest.TestCase):
    def test_the_market_is_deliberately_wrong(self):
        w = inject_signal(n_events=30, compression=0.4, seed=2)
        self.assertTrue(w.has_signal)
        gaps = [abs(q - t) for q, t in zip(w.market, w.truth)]
        self.assertGreater(max(gaps), 0.05, "the injected edge must be real and sizeable")

    def test_stronger_compression_means_a_larger_market_error(self):
        strong = inject_signal(n_events=40, compression=0.35, seed=2)
        weak = inject_signal(n_events=40, compression=0.85, seed=2)
        err_strong = sum(abs(q - t) for q, t in zip(strong.market, strong.truth))
        err_weak = sum(abs(q - t) for q, t in zip(weak.market, weak.truth))
        self.assertGreater(err_strong, err_weak)


class TestSplitDiscipline(unittest.TestCase):
    def test_no_event_appears_in_two_splits(self):
        """The leak that would invalidate every Gate-0 number."""
        w = fair_market(n_events=33, contracts_per_event=4, seed=9)
        fit, select, holdout = _split_by_cluster(w, seed=9)
        cf = {w.cluster_ids[i] for i in fit}
        cs = {w.cluster_ids[i] for i in select}
        ch = {w.cluster_ids[i] for i in holdout}
        self.assertEqual(cf & cs, set())
        self.assertEqual(cf & ch, set())
        self.assertEqual(cs & ch, set())

    def test_the_splits_partition_every_observation(self):
        w = fair_market(n_events=33, contracts_per_event=4, seed=9)
        fit, select, holdout = _split_by_cluster(w, seed=9)
        self.assertEqual(sorted(fit + select + holdout), list(range(len(w))))

    def test_all_three_splits_are_non_empty(self):
        w = fair_market(n_events=33, contracts_per_event=4, seed=9)
        for part in _split_by_cluster(w, seed=9):
            self.assertGreater(len(part), 0)


class TestCandidateSearch(unittest.TestCase):
    def test_candidates_are_valid_probabilities_of_the_right_shape(self):
        w = add_noise_features(fair_market(n_events=15, seed=4), seed=4)
        cands = candidate_forecasters(w, 6, list(range(len(w))), seed=4)
        self.assertEqual(len(cands), 6)
        for c in cands:
            self.assertEqual(len(c), len(w))
            self.assertTrue(all(0.0 < p < 1.0 for p in c))

    def test_a_featureless_world_refuses_a_candidate_search(self):
        w = fair_market(n_events=10, seed=4)
        with self.assertRaises(ValueError):
            candidate_forecasters(w, 4, list(range(len(w))), seed=4)

    def test_zero_candidates_is_refused(self):
        w = add_noise_features(fair_market(n_events=10, seed=4), seed=4)
        with self.assertRaises(ValueError):
            candidate_forecasters(w, 0, list(range(len(w))), seed=4)

    def test_fitting_on_a_subset_still_predicts_every_row(self):
        w = add_noise_features(fair_market(n_events=20, seed=4), seed=4)
        fit, _, _ = _split_by_cluster(w, seed=4)
        cands = candidate_forecasters(w, 3, fit, seed=4)
        self.assertTrue(all(len(c) == len(w) for c in cands))


class TestProtocolsAndReporting(unittest.TestCase):
    def test_all_three_protocols_return_a_result(self):
        w = add_noise_features(fair_market(n_events=24, contracts_per_event=5, seed=6), seed=6)
        results = run_all_protocols(w, n_candidates=4, alpha=0.05, n_boot=80, seed=6)
        self.assertEqual(set(results), {"naive", "cluster", "kairos"})

    def test_the_sealed_protocol_tests_fewer_observations_than_it_saw(self):
        w = add_noise_features(fair_market(n_events=24, contracts_per_event=5, seed=6), seed=6)
        results = run_all_protocols(w, n_candidates=4, alpha=0.05, n_boot=80, seed=6)
        self.assertLess(results["kairos"].n_observations, len(w))
        self.assertEqual(results["naive"].n_observations, len(w))

    def test_binomial_tail_matches_a_hand_computation(self):
        self.assertAlmostEqual(_binomial_tail(0, 5, 0.05), 1.0, places=12)
        self.assertAlmostEqual(_binomial_tail(5, 5, 0.05), 0.05**5, places=15)
        self.assertAlmostEqual(_binomial_tail(1, 2, 0.5), 0.75, places=12)

    def test_a_null_world_over_rejecting_fails_the_gate(self):
        bad = WorldReport("fair_market", False, "kairos", 40, 20)
        self.assertTrue(bad.is_gate_condition)
        self.assertIn("FAIL", bad.verdict)

    def test_an_inert_instrument_fails_the_gate_despite_a_clean_null_record(self):
        """A test that never fires must not pass Gate 0."""
        clean_null = WorldReport("fair_market", False, "kairos", 40, 1)
        inert = WorldReport("signal_strong", True, "kairos", 40, 0)
        report = GateReport((clean_null, inert))
        self.assertEqual(clean_null.verdict, "PASS")
        self.assertIn("FAIL", inert.verdict)
        self.assertFalse(report.passed)

    def test_exhibit_protocols_do_not_gate(self):
        naive_disaster = WorldReport("fair_market", False, "naive", 40, 40)
        self.assertFalse(naive_disaster.is_gate_condition)
        self.assertEqual(naive_disaster.verdict, "exhibit")

    def test_a_report_with_no_gate_conditions_does_not_pass(self):
        self.assertFalse(GateReport(()).passed)


class TestPriceStrata(unittest.TestCase):
    """The bands are frozen; these tests are what makes 'frozen' mean something."""

    def test_the_bands_are_contiguous_and_non_overlapping(self):
        for (_, _, hi), (_, lo, _) in zip(PRICE_STRATA, PRICE_STRATA[1:]):
            self.assertEqual(hi, lo, "a gap or overlap between bands silently drops observations")

    def test_the_registered_boundaries_have_not_moved(self):
        """Guards AXIOMS A8: moving a cut point after seeing a result is a search over cut points."""
        self.assertEqual(
            PRICE_STRATA,
            (
                ("longshot", 0.02, 0.15),
                ("lowmid", 0.15, 0.40),
                ("mid", 0.40, 0.60),
                ("highmid", 0.60, 0.85),
                ("favourite", 0.85, 0.98),
            ),
        )

    def test_each_price_lands_in_exactly_one_band(self):
        labels = stratify_by_price([0.03, 0.20, 0.50, 0.70, 0.90])
        self.assertEqual(labels, ["longshot", "lowmid", "mid", "highmid", "favourite"])

    def test_prices_outside_every_band_are_marked_not_absorbed(self):
        self.assertEqual(stratify_by_price([0.001, 0.999]), ["unbanded", "unbanded"])

    def test_a_boundary_price_belongs_to_the_upper_band(self):
        self.assertEqual(stratify_by_price([0.15, 0.40, 0.60, 0.85]),
                         ["lowmid", "mid", "highmid", "favourite"])


class TestBandedSignal(unittest.TestCase):
    """The concentrated-signal control. If it is not actually concentrated it proves nothing."""

    def test_every_mispriced_contract_is_observably_inside_the_band(self):
        """The defect that made the first Gate 0b comparison meaningless.

        Banding on ``pi`` rather than on the quote put a pi=0.5 contract at a quote of 0.83, next to
        honest contracts genuinely worth 0.83. The signal was concentrated in a band no protocol
        could condition on, so the comparison measured the world's opacity, not the protocols. The
        band must be visible in ``market``, which is all anything downstream ever sees.
        """
        w = inject_banded_signal(n_events=600, contracts_per_event=2, bias=1.6,
                                 band=(0.40, 0.60), seed=3)
        assert w.truth is not None
        mispriced = [(m, t) for m, t in zip(w.market, w.truth) if abs(m - t) > 1e-9]
        honest = [(m, t) for m, t in zip(w.market, w.truth) if abs(m - t) <= 1e-9]
        self.assertTrue(mispriced and honest)
        for m, _ in mispriced:
            self.assertTrue(0.40 <= m < 0.60,
                            f"a mispriced contract quoted at {m:.3f}, outside the stated band")
        for m, t in mispriced:
            self.assertGreater(m, t, "market must be shifted upward where it is biased")

    def test_the_band_label_alone_separates_biased_from_honest_contracts(self):
        """What a protocol can actually condition on: `stratify_by_price(market)`."""
        w = inject_banded_signal(n_events=600, contracts_per_event=2, bias=1.6,
                                 band=(0.40, 0.60), seed=11)
        assert w.truth is not None
        labels = stratify_by_price(w.market)
        biased_in_mid = [
            abs(m - t) > 1e-9 for m, t, lab in zip(w.market, w.truth, labels) if lab == "mid"
        ]
        biased_elsewhere = [
            abs(m - t) > 1e-9 for m, t, lab in zip(w.market, w.truth, labels) if lab != "mid"
        ]
        self.assertTrue(biased_in_mid, "the mid band must be populated")
        self.assertFalse(any(biased_elsewhere), "no bias may leak outside the mid band")

    def test_a_zero_bias_banded_world_is_a_fair_market(self):
        """The null control for this world shape: no bias means no mispricing anywhere."""
        w = inject_banded_signal(n_events=200, contracts_per_event=2, bias=0.0, seed=5)
        assert w.truth is not None
        for m, t in zip(w.market, w.truth):
            self.assertAlmostEqual(m, t, places=9)

    def test_every_contract_on_an_event_shares_one_outcome(self):
        w = inject_banded_signal(n_events=50, contracts_per_event=4, seed=1)
        by_event = {}
        for c, y in zip(w.cluster_ids, w.outcomes):
            by_event.setdefault(c, set()).add(y)
        self.assertTrue(all(len(v) == 1 for v in by_event.values()))

    def test_the_signal_really_is_concentrated_not_diffuse(self):
        """Contrast with inject_signal, which misprices at every price."""
        banded = inject_banded_signal(n_events=400, contracts_per_event=2, seed=7)
        diffuse = inject_signal(n_events=400, contracts_per_event=2, seed=7)
        for w, expect_clean in ((banded, True), (diffuse, False)):
            assert w.truth is not None
            off = [abs(m - t) > 1e-9 for m, t in zip(w.market, w.truth)]
            frac = sum(off) / len(off)
            if expect_clean:
                self.assertLess(frac, 0.5, "banded world misprices most of the range")
            else:
                self.assertGreater(frac, 0.95, "diffuse world should misprice nearly everywhere")


class TestAchievableOracle(unittest.TestCase):
    def test_it_reads_the_informative_feature_straight_off(self):
        w = inject_banded_signal(n_events=30, contracts_per_event=2, seed=2)
        orc = achievable_oracle(w)
        self.assertEqual(len(orc), len(w))
        self.assertTrue(all(0.0 < p < 1.0 for p in orc))

    def test_it_beats_the_market_where_the_market_is_wrong(self):
        w = inject_banded_signal(n_events=600, contracts_per_event=2, bias=1.2, seed=4)
        assert w.truth is not None
        orc = achievable_oracle(w)
        deltas = paired_deltas(orc, w.market, w.outcomes)
        self.assertGreater(sum(deltas) / len(deltas), 0.0)


if __name__ == "__main__":
    unittest.main()
