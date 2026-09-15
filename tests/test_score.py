"""Scoring tests, including the two traps the SPEC is built to avoid.

1. **Accuracy is not skill.** Walsh et al. 2023 found a 70-point ROI swing between selecting on
   calibration and selecting on accuracy. The test below builds two forecasters with *identical*
   directional accuracy and shows the skill score separates them.
2. **A Sharpe of 1.0 can be worth nothing.** Bailey & Lopez de Prado: after seven configurations
   you expect a two-year backtest with Sharpe above 1.0 when the true Sharpe is zero. The test
   reproduces that number.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairos.score import (
    TrialLedger,
    brier_score,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    log_score,
    min_backtest_length,
    skill_score,
)

BASE_RATE_OUTCOMES = [1.0] * 60 + [0.0] * 40


class TestProperScores(unittest.TestCase):
    def test_perfect_forecasts_score_near_zero(self):
        outcomes = [1.0, 0.0, 1.0, 0.0]
        near_perfect = [1.0, 0.0, 1.0, 0.0]
        self.assertLess(log_score(near_perfect, outcomes), 1e-10)
        self.assertAlmostEqual(brier_score(near_perfect, outcomes), 0.0, places=12)

    def test_confident_and_wrong_is_penalised_but_finite(self):
        score = log_score([1.0], [0.0])
        self.assertGreater(score, 30.0)
        self.assertLess(score, float("inf"))

    def test_scores_are_minimised_by_telling_the_truth(self):
        """Strict propriety, driven rather than asserted."""
        outcomes = BASE_RATE_OUTCOMES
        truthful = log_score([0.6] * 100, outcomes)
        for lie in (0.3, 0.45, 0.5, 0.7, 0.8, 0.95):
            self.assertGreater(log_score([lie] * 100, outcomes), truthful)

    def test_malformed_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            log_score([0.5], [0.5])  # outcome is not 0 or 1
        with self.assertRaises(ValueError):
            log_score([1.5], [1.0])
        with self.assertRaises(ValueError):
            log_score([], [])


class TestSkillAgainstTheMarket(unittest.TestCase):
    """The go/no-go metric: did the model beat the price, or merely look confident?"""

    def test_matching_the_market_scores_exactly_zero_skill(self):
        market = [0.6] * 100
        self.assertAlmostEqual(
            skill_score(market, BASE_RATE_OUTCOMES, market), 0.0, places=12
        )

    def test_overconfidence_scores_negative_skill_at_identical_accuracy(self):
        """Both forecasters call every event YES, so directional accuracy is identical at 60%.

        Only the probability differs - and only the skill score notices.
        """
        market = [0.6] * 100
        calibrated = [0.6] * 100
        overconfident = [0.95] * 100

        self.assertAlmostEqual(
            skill_score(calibrated, BASE_RATE_OUTCOMES, market), 0.0, places=12
        )
        self.assertLess(skill_score(overconfident, BASE_RATE_OUTCOMES, market), -0.5)

    def test_genuine_discrimination_scores_positive_skill(self):
        market = [0.6] * 100
        informed = [0.8] * 60 + [0.3] * 40  # correlated with the outcome
        self.assertGreater(skill_score(informed, BASE_RATE_OUTCOMES, market), 0.5)

    def test_brier_and_log_agree_on_direction_here(self):
        market = [0.6] * 100
        informed = [0.8] * 60 + [0.3] * 40
        self.assertGreater(skill_score(informed, BASE_RATE_OUTCOMES, market), 0.0)
        self.assertGreater(
            skill_score(informed, BASE_RATE_OUTCOMES, market, scorer=brier_score), 0.0
        )

    def test_mismatched_baseline_length_is_refused(self):
        with self.assertRaises(ValueError):
            skill_score([0.5] * 10, [1.0] * 10, [0.5] * 9)


class TestMultipleTestingDeflation(unittest.TestCase):
    def test_the_hurdle_grows_with_every_configuration_tried(self):
        hurdles = [expected_max_sharpe(n) for n in (2, 5, 10, 50, 200, 1000)]
        for a, b in zip(hurdles, hurdles[1:]):
            self.assertLess(a, b)

    def test_seven_trials_already_expect_a_sharpe_above_one(self):
        """Bailey & Lopez de Prado's headline number, reproduced."""
        hurdle = expected_max_sharpe(7)
        self.assertGreater(hurdle, 1.0)
        self.assertLess(hurdle, 1.6)

    def test_a_sharpe_of_one_after_seven_trials_is_not_evidence(self):
        dsr = deflated_sharpe_ratio(1.0, n_trials=7, n_observations=504)
        self.assertLess(dsr, 0.5, "an unremarkable Sharpe must not clear the deflated test")

    def test_a_genuinely_strong_result_still_clears(self):
        dsr = deflated_sharpe_ratio(3.0, n_trials=7, n_observations=504)
        self.assertGreater(dsr, 0.95)

    def test_more_trials_lower_the_same_observed_sharpe(self):
        few = deflated_sharpe_ratio(2.0, n_trials=5, n_observations=504)
        many = deflated_sharpe_ratio(2.0, n_trials=5000, n_observations=504)
        self.assertGreater(few, many)

    def test_two_years_is_too_short_for_seven_trials(self):
        self.assertGreater(min_backtest_length(7, target_sharpe=1.0), 2.0)

    def test_single_trial_maximum_is_refused_as_meaningless(self):
        with self.assertRaises(ValueError):
            expected_max_sharpe(1)


class TestTrialLedger(unittest.TestCase):
    def test_duplicate_trial_ids_are_refused(self):
        ledger = TrialLedger()
        ledger.record("t1", {"kelly_fraction": 0.25})
        with self.assertRaises(ValueError):
            ledger.record("t1", {"kelly_fraction": 0.50})
        self.assertEqual(len(ledger), 1)

    def test_it_persists_and_reloads_so_the_count_survives_a_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.jsonl"
            first = TrialLedger(path)
            first.record("a", {"blend_weight": 0.0})
            first.record("b", {"blend_weight": 0.2})

            reloaded = TrialLedger(path)
            self.assertEqual(len(reloaded), 2)
            self.assertEqual({t.trial_id for t in reloaded.trials}, {"a", "b"})
            self.assertEqual(reloaded.trials[1].config, {"blend_weight": 0.2})

            with self.assertRaises(ValueError):
                reloaded.record("a", {})

    def test_recorded_config_is_preserved_verbatim(self):
        ledger = TrialLedger()
        config = {"kelly_fraction": 0.25, "space": "logit", "bins": 10}
        trial = ledger.record("x", config, note="baseline")
        self.assertEqual(trial.config, config)
        self.assertEqual(trial.note, "baseline")
        self.assertTrue(trial.created_at.endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
