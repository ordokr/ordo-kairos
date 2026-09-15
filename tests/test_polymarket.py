"""Adapter tests. Pure logic only — no network.

Admission is where a dataset silently becomes wrong, so every rejection path is driven with a
fixture that must be refused. The two subtle ones are the leak guards: a decision point must never
fall inside the lead window, and resolution time must come from observed trading rather than the
stated end date.
"""

from __future__ import annotations

import json
import unittest
import urllib.error
from unittest import mock

from kairos import polymarket as pm
from pathlib import Path

from kairos.polymarket import (
    MAX_OFFSET,
    _get_retry,
    Observation,
    admit,
    cache_dir,
    decision_point,
    quarterly_windows,
    resolution_of,
)
from kairos.state import WORKSPACE_ROOT, is_inside

DAY = 86400


def market(**over) -> dict:
    base = {
        "id": "12345",
        "question": "Will X happen?",
        "outcomePrices": json.dumps(["0.00000101", "0.99999899"]),
        "clobTokenIds": json.dumps(["tok-a", "tok-b"]),
        "endDate": "2029-01-19T23:59:00Z",
        "startDate": "2026-07-31T19:10:57Z",
    }
    base.update(over)
    return base


def history(n: int, start: int = 1_700_000_000, price: float = 0.40, step: int = DAY):
    return [{"t": start + i * step, "p": price} for i in range(n)]


class TestResolutionParsing(unittest.TestCase):
    def test_near_one_float_is_read_as_yes(self):
        """The bug that made the first census report 0% resolved."""
        self.assertEqual(
            resolution_of(market(outcomePrices=json.dumps(["0.99999898", "0.00000101"]))), 1.0
        )

    def test_near_zero_float_is_read_as_no(self):
        self.assertEqual(
            resolution_of(market(outcomePrices=json.dumps(["0.00000101", "0.99999899"]))), 0.0
        )

    def test_voided_market_is_refused(self):
        self.assertIsNone(resolution_of(market(outcomePrices=json.dumps(["0", "0"]))))

    def test_a_market_settled_between_the_extremes_is_refused(self):
        self.assertIsNone(resolution_of(market(outcomePrices=json.dumps(["0.4", "0.6"]))))

    def test_malformed_fields_are_refused_not_raised(self):
        for bad in ({}, {"outcomePrices": "not json"}, {"outcomePrices": json.dumps(["1"])}):
            self.assertIsNone(resolution_of(market(**bad)) if bad else resolution_of({}))


class TestDecisionPoint(unittest.TestCase):
    def test_it_picks_the_last_point_outside_the_lead_window(self):
        h = history(5)  # daily points
        ts, price = decision_point(h, lead_hours=24.0)
        self.assertEqual(ts, h[-2]["t"])

    def test_a_longer_lead_selects_an_earlier_point(self):
        h = history(6)
        near = decision_point(h, lead_hours=24.0)[0]
        far = decision_point(h, lead_hours=72.0)[0]
        self.assertLess(far, near)

    def test_it_refuses_rather_than_leaking_when_nothing_is_far_enough_back(self):
        """Falling back to a later price would import information from nearer resolution."""
        h = history(3, step=3600)  # three hourly points
        self.assertIsNone(decision_point(h, lead_hours=48.0))

    def test_unsorted_history_is_handled(self):
        h = history(4)
        shuffled = [h[2], h[0], h[3], h[1]]
        self.assertEqual(decision_point(shuffled, 24.0)[0], h[-2]["t"])

    def test_empty_or_malformed_history_returns_none(self):
        self.assertIsNone(decision_point([], 24.0))
        self.assertIsNone(decision_point([{"bad": 1}], 24.0))


class TestAdmission(unittest.TestCase):
    def test_a_well_formed_market_is_admitted(self):
        o = admit(market(), history(8), min_points=5, lead_hours=24.0)
        self.assertIsInstance(o, Observation)
        self.assertEqual(o.outcome, 0.0)
        self.assertEqual(o.n_points, 8)
        self.assertGreater(o.days_to_resolution, 0.0)

    def test_thin_history_is_refused(self):
        self.assertIsNone(admit(market(), history(3), min_points=5))

    def test_unresolved_market_is_refused(self):
        self.assertIsNone(
            admit(market(outcomePrices=json.dumps(["0", "0"])), history(8), min_points=5)
        )

    def test_price_outside_the_band_is_refused(self):
        """A benchmark evaluated only on 0.99 contracts measures the log score's tails."""
        self.assertIsNone(admit(market(), history(8, price=0.995), min_points=5))
        self.assertIsNone(admit(market(), history(8, price=0.005), min_points=5))

    def test_resolution_time_comes_from_trading_not_the_stated_end_date(self):
        """One sampled market traded 7 days against a 2029 end date."""
        h = history(8)
        o = admit(market(endDate="2029-01-19T23:59:00Z"), h, min_points=5)
        self.assertEqual(o.resolution_ts, h[-1]["t"])
        self.assertLess(o.days_to_resolution, 10.0)

    def test_negrisk_membership_becomes_the_cluster(self):
        o = admit(market(negRiskMarketID="0xabc"), history(8), min_points=5)
        self.assertEqual(o.cluster_id, "0xabc")

    def test_a_standalone_market_clusters_to_itself(self):
        o = admit(market(id="777"), history(8), min_points=5)
        self.assertEqual(o.cluster_id, "solo:777")

    def test_two_markets_in_one_group_share_a_cluster(self):
        a = admit(market(id="1", negRiskMarketID="0xg"), history(8), min_points=5)
        b = admit(market(id="2", negRiskMarketID="0xg"), history(8), min_points=5)
        self.assertEqual(a.cluster_id, b.cluster_id)
        self.assertNotEqual(a.market_id, b.market_id)

    def test_a_market_with_no_id_is_refused(self):
        m = market()
        del m["id"]
        self.assertIsNone(admit(m, history(8), min_points=5))

    def test_admitted_rows_serialise(self):
        o = admit(market(), history(8), min_points=5)
        row = o.as_row()
        self.assertEqual(set(row) >= {"price", "outcome", "cluster_id"}, True)
        json.dumps(row)  # must not raise


class TestCacheLocation(unittest.TestCase):
    def test_cache_never_lands_inside_the_publish_eligible_workspace(self):
        self.assertFalse(is_inside(cache_dir(), WORKSPACE_ROOT))

    def test_cache_directory_exists_after_resolution(self):
        self.assertTrue(Path(cache_dir()).is_dir())


class TestWindowedRetrieval(unittest.TestCase):
    """Date windows are the only way past Gamma's offset ceiling, so the window grid is load-bearing.

    Measured against the live API 2026-09-08: `offset` >= 2100 returns HTTP 422 for every ordering
    and `limit` silently caps at 100, but the same query inside an end-date window gets its own
    budget. A gap in this grid would silently drop every market that resolved in it, and an overlap
    would double-count events -- both invisible in the output, both fatal to an event count.
    """

    def test_windows_tile_the_range_with_no_gap_and_no_overlap(self):
        w = sorted(quarterly_windows())
        for (_, hi), (lo, _) in zip(w, w[1:]):
            self.assertEqual(hi, lo, f"discontinuity at {hi}: markets resolving there are lost")

    def test_the_sweep_runs_newest_first(self):
        """The registered collection order for Look 3."""
        w = quarterly_windows()
        self.assertEqual(w, sorted(w, reverse=True))

    def test_the_grid_covers_whole_years_with_four_quarters_each(self):
        w = quarterly_windows(2021, 2026)
        self.assertEqual(len(w), 24)
        self.assertEqual(min(lo for lo, _ in w), "2021-01-01")
        self.assertEqual(max(hi for _, hi in w), "2027-01-01")

    def test_year_boundaries_roll_over_rather_than_stopping_at_december(self):
        """A naive '10-01'..'12-31' would drop everything resolving on 31 December."""
        w = quarterly_windows(2023, 2023)
        self.assertIn(("2023-10-01", "2024-01-01"), w)

    def test_the_offset_ceiling_is_recorded_below_the_422_boundary(self):
        """2100 is where the API refuses; the last usable page starts at 2000."""
        self.assertEqual(MAX_OFFSET, 2000)
        self.assertLess(MAX_OFFSET, 2100)


class TestTransientFailureHandling(unittest.TestCase):
    """A single HTTP 500 killed a 909-event sweep partway through its fourth window.

    Retrying is the fix; swallowing is not. A window fetched short is a window with markets silently
    missing, which biases an event count in a way nothing downstream can see.
    """

    @staticmethod
    def _err(code):
        return urllib.error.HTTPError("http://x", code, "err", None, None)

    def test_a_transient_server_error_is_retried_and_recovers(self):
        calls = {"n": 0}

        def flaky(url, timeout=40):
            calls["n"] += 1
            if calls["n"] < 3:
                raise self._err(500)
            return [{"id": "ok"}]

        with mock.patch.object(pm, "_get", flaky), mock.patch.object(pm.time, "sleep", lambda s: None):
            self.assertEqual(_get_retry("u"), [{"id": "ok"}])
        self.assertEqual(calls["n"], 3)

    def test_422_is_never_retried_because_it_is_the_stop_condition(self):
        """422 is Gamma's honest 'past the end'. Retrying it turns a stop into a stall."""
        calls = {"n": 0}

        def gone(url, timeout=40):
            calls["n"] += 1
            raise self._err(422)

        with mock.patch.object(pm, "_get", gone), mock.patch.object(pm.time, "sleep", lambda s: None):
            with self.assertRaises(urllib.error.HTTPError):
                _get_retry("u")
        self.assertEqual(calls["n"], 1, "422 must not be retried")

    def test_a_persistent_failure_raises_rather_than_returning_a_short_page(self):
        calls = {"n": 0}

        def dead(url, timeout=40):
            calls["n"] += 1
            raise self._err(503)

        with mock.patch.object(pm, "_get", dead), mock.patch.object(pm.time, "sleep", lambda s: None):
            with self.assertRaises(urllib.error.HTTPError):
                _get_retry("u", attempts=4)
        self.assertEqual(calls["n"], 4)

    def test_a_network_error_is_also_retried(self):
        calls = {"n": 0}

        def flaky(url, timeout=40):
            calls["n"] += 1
            if calls["n"] < 2:
                raise TimeoutError("slow")
            return []

        with mock.patch.object(pm, "_get", flaky), mock.patch.object(pm.time, "sleep", lambda s: None):
            self.assertEqual(_get_retry("u"), [])
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
