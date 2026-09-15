"""Leg-set verification: the thing Gate B measured as carrying the entire Class B defence.

Gate B's ``truncated_believed`` exhibit fires **1.000 at every horizon** — a truncated group whose
leg set is asserted complete. Nothing inside the scanner can prevent that, so these tests are the
guard on the only layer that can.

Everything here is offline. A verifier that needs the network to be tested cannot be tested when the
network is the thing that failed.
"""

from __future__ import annotations

import unittest
from unittest import mock

from kairos import legset
from kairos.legset import (
    EXHAUSTIVENESS_FAILURES,
    EXHAUSTIVENESS_TRIALS,
    break_even_failure_rate,
    event_leg_set,
    residual_failure_bound,
    verify_leg_set,
)
from kairos.structural import Leg, NegRiskGroup, scan_verified


def event(n_legs=5, *, other=False, nrm="0xabc", closed=True, event_id="777919"):
    markets = [
        {"id": str(1000 + i), "negRiskMarketID": nrm, "negRiskOther": False, "closed": closed}
        for i in range(n_legs)
    ]
    if other:
        markets.append({"id": "9999", "negRiskMarketID": nrm, "negRiskOther": True,
                        "closed": closed})
    return {"id": event_id, "markets": markets}


def ids(ev):
    return [m["id"] for m in ev["markets"]]


class TestTheAuthorityIsCrossCheckedNotTrusted(unittest.TestCase):
    def test_a_matching_leg_set_verifies(self):
        ev = event(6)
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev))
        self.assertTrue(v.complete)
        self.assertEqual(v.refusals, ())
        self.assertEqual(v.missing, frozenset())

    def test_a_truncated_leg_set_is_caught_and_the_missing_legs_named(self):
        """The exact failure Gate B could not defend against."""
        ev = event(8)
        held = ids(ev)[:4]
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", held)
        self.assertFalse(v.complete)
        self.assertIn("legs_missing", v.refusals)
        self.assertEqual(len(v.missing), 4)

    def test_holding_a_market_the_authority_does_not_list_refuses_the_authority(self):
        """If the event is missing a leg we hold, the event is not authoritative for this group.

        Trusting an endpoint to be complete is the assumption that created the problem.
        """
        ev = event(5)
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev) + ["intruder"])
        self.assertFalse(v.complete)
        self.assertIn("authority_incomplete", v.refusals)

    def test_an_event_spanning_two_groups_is_refused_as_ambiguous(self):
        ev = event(4)
        ev["markets"][0]["negRiskMarketID"] = "0xdifferent"
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev))
        self.assertFalse(v.complete)
        self.assertIn("event_spans_multiple_or_zero_neg_risk_groups", v.refusals)

    def test_an_unavailable_event_refuses_rather_than_assuming_completeness(self):
        with mock.patch.object(legset, "fetch_event", return_value=None):
            v = verify_leg_set("777919", ["1", "2"])
        self.assertFalse(v.complete)
        self.assertIn("event_unavailable", v.refusals)

    def test_an_event_with_no_markets_refuses(self):
        with mock.patch.object(legset, "fetch_event", return_value={"id": "1", "markets": []}):
            v = verify_leg_set("1", ["a"])
        self.assertFalse(v.complete)
        self.assertIn("event_lists_no_markets", v.refusals)

    def test_the_other_leg_is_detected_when_present(self):
        ev = event(4, other=True)
        self.assertTrue(event_leg_set(ev).has_other_leg)
        self.assertFalse(event_leg_set(event(4)).has_other_leg)


class TestExhaustivenessIsArithmeticNotAFlag(unittest.TestCase):
    """0/512 resolved groups had zero winners. That bounds the risk; it does not eliminate it."""

    def test_the_residual_bound_is_never_zero(self):
        """AXIOMS A6: not having seen it is not evidence it cannot happen."""
        self.assertGreater(residual_failure_bound(), 0.0)
        self.assertAlmostEqual(residual_failure_bound(75, 0), 0.04, places=6)

    def test_the_bound_shrinks_only_by_measuring_more(self):
        self.assertGreater(residual_failure_bound(75, 0), residual_failure_bound(300, 0))
        self.assertAlmostEqual(residual_failure_bound(300, 0), 0.01, places=6)

    def test_an_observed_failure_widens_the_bound(self):
        self.assertGreater(residual_failure_bound(75, 1), residual_failure_bound(75, 0))

    def test_zero_trials_is_total_ignorance_not_safety(self):
        self.assertEqual(residual_failure_bound(0, 0), 1.0)

    def test_break_even_reflects_that_failure_costs_the_stake_not_the_edge(self):
        """A 5% edge on a 0.95 stake tolerates a 5% failure rate - and no more."""
        self.assertAlmostEqual(break_even_failure_rate(0.05, 0.95), 0.05, places=9)
        self.assertLess(break_even_failure_rate(0.02, 0.95), 0.021)

    @staticmethod
    def _edges_around_the_bound(stake=0.95):
        """An edge clearly below the current tolerance, and one clearly above it.

        Derived from the measured bound rather than hard-coded. The first version pinned 2% as
        "too thin", which was true at 75 trials and false at 512 — so it failed for the *right*
        reason when the evidence improved, and would have been silenced by editing the number.
        A test that states the mechanism survives the sample growing; one that states a constant
        has to be rewritten every time, which is when a real regression slips through.
        """
        b = residual_failure_bound()
        # break_even(e, stake) = e / (e + stake); solve e for a target break-even t.
        def edge_for(t):
            return t * stake / (1.0 - t)
        return edge_for(b * 0.5), edge_for(min(b * 5.0, 0.5))

    def test_an_edge_below_the_measured_tolerance_is_refused(self):
        too_thin, thick_enough = self._edges_around_the_bound()
        ev = event(5)  # no Other leg
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev))
        self.assertTrue(v.complete)
        self.assertFalse(v.exhaustive(edge=too_thin, stake=0.95),
                         f"edge {too_thin:.5f} should not absorb a {residual_failure_bound():.4f} "
                         f"failure bound")
        self.assertTrue(v.exhaustive(edge=thick_enough, stake=0.95))

    def test_the_current_evidence_admits_a_one_percent_edge(self):
        """Records what 512 trials bought, and fails loudly if the constants regress."""
        self.assertLess(residual_failure_bound(), break_even_failure_rate(0.01, 0.99),
                        "a 1% edge should be tradeable on the current sample")

    def test_an_explicit_other_leg_settles_exhaustiveness_at_any_edge(self):
        ev = event(5, other=True)
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev))
        self.assertTrue(v.exhaustive(edge=0.001, stake=0.95))

    def test_the_measured_sample_is_recorded_as_a_sample(self):
        self.assertEqual(EXHAUSTIVENESS_FAILURES, 0)
        self.assertGreaterEqual(EXHAUSTIVENESS_TRIALS, 75)


class TestScanVerifiedClosesTheGateBHole(unittest.TestCase):
    """`scan` trusts its flags; `scan_verified` does not. This is the difference, driven."""

    @staticmethod
    def _group(prices, days=30.0, depth=500.0):
        legs = tuple(Leg(f"o{i}", p, depth) for i, p in enumerate(prices))
        return NegRiskGroup("g", legs, days)

    @classmethod
    def _group_with_edge(cls, target_edge, *, n=5, days=30.0, depth=500.0):
        """Bisect on a uniform leg price until the post-cost edge is ``target_edge``.

        Solved rather than hard-coded so the test states the property it cares about — "an edge of
        this size" — instead of a magic price that silently means something else the moment a fee
        parameter moves.
        """
        from kairos.costs import CONSERVATIVE

        def edge_at(p):
            return 1.0 - n * CONSERVATIVE.effective_yes_cost(p, days)

        lo, hi = 1e-4, 0.999 / n
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if edge_at(mid) > target_edge:
                lo = mid
            else:
                hi = mid
        return cls._group([lo] * n, days=days, depth=depth)

    def test_a_truncated_group_cannot_fire_however_cheap_it_looks(self):
        ev = event(8)
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev)[:4])
        g = self._group([0.10] * 4)  # sums to 0.40 - a spectacular fake arbitrage
        r = scan_verified(g, v)
        self.assertFalse(r.fires)
        self.assertIn("legs_missing", r.refusals)

    def test_a_verified_group_with_a_real_edge_fires(self):
        ev = event(5, other=True)
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev))
        r = scan_verified(self._group_with_edge(0.12, n=6), v)
        self.assertTrue(r.fires, r.explain())
        self.assertGreater(r.edge, 0.0)

    def test_a_verified_group_with_a_thin_edge_is_refused_on_exhaustiveness_risk(self):
        ev = event(5)  # no Other leg -> 4% residual bound
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev))
        b = residual_failure_bound()
        thin = (b * 0.5) * 0.95 / (1.0 - b * 0.5)   # break-even below the measured bound
        r = scan_verified(self._group_with_edge(thin), v)
        self.assertGreater(r.edge, 0.0, "there is an edge")
        self.assertFalse(r.fires, "but it is too thin to absorb the exhaustiveness risk")
        self.assertIn("exhaustiveness_risk_exceeds_edge", r.refusals)

    def test_an_unfillable_verified_edge_is_still_refused(self):
        ev = event(5, other=True)
        with mock.patch.object(legset, "fetch_event", return_value=ev):
            v = verify_leg_set("777919", ids(ev))
        r = scan_verified(self._group_with_edge(0.12, n=6, depth=2.0), v)
        self.assertFalse(r.fires)
        self.assertIn("insufficient_depth", r.refusals)

    def test_it_refuses_anything_that_is_not_a_verification(self):
        with self.assertRaises(TypeError):
            scan_verified(self._group([0.2] * 5), True)  # the old boolean, rejected loudly


if __name__ == "__main__":
    unittest.main()
