"""Gate tests, written as negative tests first.

A gate that has only ever seen good input is unverified. Every check here is fed a known-bad
value and asserted to FAIL - a clean pass on happy-path data would prove nothing about the gate.
The specific bad inputs are the ones the literature names as traps.
"""

from __future__ import annotations

import unittest

from kairos.costs import CONSERVATIVE, CostModel
from kairos.gate import GateConfig, MarketSnapshot, evaluate


def snapshot(**overrides) -> MarketSnapshot:
    base = dict(
        market_id="TEST-1",
        mid=0.50,
        days_to_resolution=30.0,
        depth_contracts=5000.0,
        settles_on_tradeable_price=False,
        dispute_prone=False,
    )
    base.update(overrides)
    return MarketSnapshot(**base)


def failed_names(decision) -> set[str]:
    return {c.name for c in decision.failures}


class TestGateAllowsOnlyCleanTrades(unittest.TestCase):
    def setUp(self):
        self.costs = CostModel()
        self.config = GateConfig()

    def test_a_clean_trade_passes_every_check(self):
        decision = evaluate(
            p=0.60,
            market=snapshot(),
            costs=self.costs,
            config=self.config,
            member_forecasts=[0.58, 0.60, 0.63],
            intended_contracts=200.0,
        )
        self.assertTrue(decision.allowed, decision.explain())
        self.assertEqual(failed_names(decision), set())

    def test_default_is_abstain_when_nothing_is_supplied(self):
        """No ensemble, no edge: the gate must refuse rather than wave it through."""
        decision = evaluate(p=0.50, market=snapshot(), costs=self.costs, config=self.config)
        self.assertFalse(decision.allowed)
        self.assertIn("ensemble_unanimity", failed_names(decision))
        self.assertIn("edge_after_costs", failed_names(decision))


class TestKnownBadInputsMustFail(unittest.TestCase):
    """Each case is a documented way to lose money."""

    def setUp(self):
        self.costs = CostModel()
        self.config = GateConfig()
        self.members = [0.58, 0.60, 0.63]

    def test_five_minute_price_settled_contract_is_refused(self):
        """Dai et al. 2026: retail is the counterparty to settlement manipulators here."""
        decision = evaluate(
            p=0.60,
            market=snapshot(
                days_to_resolution=5.0 / (24 * 60), settles_on_tradeable_price=True
            ),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("settlement_manipulation", failed_names(decision))

    def test_fifteen_minute_contract_clears_the_horizon_specific_manipulation_check(self):
        """The same study finds the effect absent at 15 minutes - so the check must be specific."""
        decision = evaluate(
            p=0.60,
            market=snapshot(
                days_to_resolution=20.0 / (24 * 60),
                settles_on_tradeable_price=True,
                settlement_manipulation_cost=10_000_000.0,
            ),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
        )
        self.assertNotIn("settlement_manipulation", failed_names(decision))

    def test_unmeasured_manipulation_cost_fails_closed(self):
        """'We did not check' is not evidence of safety."""
        decision = evaluate(
            p=0.60,
            market=snapshot(days_to_resolution=30.0, settles_on_tradeable_price=True),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("resolution_manipulability", failed_names(decision))

    def test_cheaply_manipulable_settlement_is_refused_at_any_horizon(self):
        """Generalises past the 5-minute case: the horizon is a symptom, not the disease."""
        decision = evaluate(
            p=0.60,
            market=snapshot(
                days_to_resolution=90.0,
                settles_on_tradeable_price=True,
                settlement_manipulation_cost=5_000.0,
            ),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
            intended_contracts=1_000.0,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("resolution_manipulability", failed_names(decision))

    def test_non_price_settled_markets_pass_the_manipulability_check(self):
        decision = evaluate(
            p=0.60,
            market=snapshot(),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
        )
        self.assertNotIn("resolution_manipulability", failed_names(decision))

    def test_longshot_is_refused(self):
        """Whelan 2023: fees make post-fee loss rates worse as probability falls."""
        decision = evaluate(
            p=0.10,
            market=snapshot(mid=0.02),
            costs=self.costs,
            config=self.config,
            member_forecasts=[0.05, 0.08, 0.10],
        )
        self.assertFalse(decision.allowed)
        self.assertIn("price_band", failed_names(decision))

    def test_thin_depth_is_refused(self):
        """Cheng et al. 2026: 76.9% of opportunities capped near 15 shares."""
        decision = evaluate(
            p=0.60,
            market=snapshot(depth_contracts=14.8),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
            intended_contracts=500.0,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("depth", failed_names(decision))

    def test_split_ensemble_is_refused(self):
        """Unanimity, not majority. Kota 2026 puts the accuracy in the unanimous subset."""
        decision = evaluate(
            p=0.60,
            market=snapshot(),
            costs=self.costs,
            config=self.config,
            member_forecasts=[0.58, 0.61, 0.42],  # one member disagrees with the direction
        )
        self.assertFalse(decision.allowed)
        self.assertIn("ensemble_unanimity", failed_names(decision))

    def test_too_few_members_is_refused(self):
        decision = evaluate(
            p=0.60,
            market=snapshot(),
            costs=self.costs,
            config=self.config,
            member_forecasts=[0.60, 0.61],
        )
        self.assertFalse(decision.allowed)
        self.assertIn("ensemble_unanimity", failed_names(decision))

    def test_dispute_prone_rule_set_is_refused(self):
        """Wen et al. 2026: $972M of Polymarket volume sat in disputed events."""
        decision = evaluate(
            p=0.60,
            market=snapshot(dispute_prone=True),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("resolution_risk", failed_names(decision))

    def test_thin_edge_is_refused_after_costs(self):
        """A two-point edge over the market is inside the cost band."""
        decision = evaluate(
            p=0.52,
            market=snapshot(),
            costs=self.costs,
            config=self.config,
            member_forecasts=[0.51, 0.52, 0.53],
        )
        self.assertFalse(decision.allowed)
        self.assertIn("edge_after_costs", failed_names(decision))

    def test_forecast_uncertainty_can_close_the_gate(self):
        kwargs = dict(
            p=0.60,
            market=snapshot(),
            costs=self.costs,
            config=self.config,
            member_forecasts=self.members,
        )
        self.assertTrue(evaluate(**kwargs, p_stderr=0.0).allowed)
        self.assertFalse(evaluate(**kwargs, p_stderr=0.06).allowed)


class TestExplainIsUsable(unittest.TestCase):
    def test_explanation_names_every_check_and_the_verdict(self):
        decision = evaluate(
            p=0.52,
            market=snapshot(dispute_prone=True),
            costs=CostModel(),
            config=GateConfig(),
            member_forecasts=[0.51, 0.52, 0.53],
        )
        text = decision.explain()
        lines = text.splitlines()
        self.assertIn("ABSTAIN", lines[0])
        self.assertIn("resolution_risk", text)
        self.assertIn("edge_after_costs", text)

        # One line per check, each carrying an explicit ok/FAIL marker.
        check_lines = [ln for ln in lines[1:] if ln.startswith("  [")]
        self.assertEqual(len(check_lines), len(decision.checks))
        self.assertEqual(
            sum(1 for ln in check_lines if "[FAIL]" in ln), len(decision.failures)
        )
        for check in decision.checks:
            self.assertTrue(
                any(check.name in ln for ln in check_lines),
                msg=f"check {check.name!r} missing from the explanation",
            )


class TestManipulabilityIsUnconditionalFailClosed(unittest.TestCase):
    """CORRECTIONS item 11, resolved. The arithmetic that used to grant a pass was withdrawn.

    A manipulator's payoff is not bounded by our position — it can include other venues, the
    underlying, and parties we cannot see. So no measured cost, however large, buys a pass; only a
    human-written externally grounded analysis does.
    """

    @staticmethod
    def _price_settled(**kw):
        base = dict(
            market_id="m", mid=0.5, days_to_resolution=30.0, depth_contracts=10_000.0,
            settles_on_tradeable_price=True,
        )
        base.update(kw)
        return MarketSnapshot(**base)

    def _decide(self, market):
        return evaluate(
            0.9, market, costs=CONSERVATIVE, config=GateConfig(),
            member_forecasts=(0.9, 0.9, 0.9), intended_contracts=10.0,
        )

    def test_an_enormous_measured_cost_no_longer_buys_a_pass(self):
        """The heart of the correction: $1bn to move it is still a refusal without an analysis."""
        d = self._decide(self._price_settled(settlement_manipulation_cost=1e9))
        self.assertIn("resolution_manipulability", failed_names(d))

    def test_an_externally_grounded_analysis_is_the_only_way_through(self):
        d = self._decide(self._price_settled(
            external_manipulation_analysis="CME settlement window, 3 independent venues, reviewed",
        ))
        self.assertNotIn("resolution_manipulability", failed_names(d))

    def test_a_blank_analysis_is_not_an_analysis(self):
        for blank in ("", "   ", None):
            d = self._decide(self._price_settled(external_manipulation_analysis=blank))
            self.assertIn("resolution_manipulability", failed_names(d), repr(blank))

    def test_the_observed_cost_is_still_reported_but_labelled_as_not_a_pass_condition(self):
        d = self._decide(self._price_settled(settlement_manipulation_cost=5e8))
        detail = next(c.detail for c in d.checks if c.name == "resolution_manipulability")
        self.assertIn("NOT a pass condition", detail)

    def test_markets_that_do_not_read_a_tradeable_price_are_unaffected(self):
        d = self._decide(self._price_settled(settles_on_tradeable_price=False))
        self.assertNotIn("resolution_manipulability", failed_names(d))

    def test_the_withdrawn_threshold_is_gone_from_the_config(self):
        """C9: the knob that encoded the refuted model does not linger."""
        self.assertFalse(hasattr(GateConfig(), "min_manipulation_cost_multiple"))


if __name__ == "__main__":
    unittest.main()
