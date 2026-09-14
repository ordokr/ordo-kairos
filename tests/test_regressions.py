"""Recorded corrections, re-expressed as tests that fail if the defect returns.

``docs/CORRECTIONS.md`` is append-only prose and it did **not** prevent recurrence. Pass 4 recorded
G0.2 — a power comparison run inside worlds where the best obtainable result was itself undetected —
described the fix, and shipped it as a property of one class. Pass 9 then wrote a new runner and
committed the same defect, announcing "DEAD" with every ceiling below the power floor.

A correction that is only written down is a correction that will be made again (``AXIOMS`` G8). Each
test below names the pass that recorded it, and encodes the *property* the correction established
rather than the specific line that was wrong — a test pinned to the old line would pass a rewrite of
the same mistake.
"""

from __future__ import annotations

import json
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from kairos import polymarket as pm
from kairos.nullworld import POWER_FLOOR, inject_banded_signal, stratify_by_price
from kairos.validity import assess

ROOT = Path(__file__).resolve().parent.parent


class TestPass4G02VerdictNeedsAValidityPrecondition(unittest.TestCase):
    """Pass 4 (G0.2), re-committed in Pass 9. The most expensive lesson in the project.

    A comparison run inside units where nothing could have been detected measures the units, not the
    instruments. Recorded in prose, fixed on one class, and then repeated by the next runner.
    """

    def test_no_verdict_when_every_unit_is_below_the_floor(self):
        r = assess({"a": 0.19, "b": 0.38, "c": 0.25}, POWER_FLOOR)
        self.assertFalse(r.may_conclude)
        self.assertIn("NO VERDICT", r.refusal())

    def test_a_dead_unit_may_not_hide_behind_a_healthy_one(self):
        """Pass 9's second attempt: guarding on the BEST ceiling instead of per unit."""
        r = assess({"healthy": 1.000, "dead": 0.062}, POWER_FLOOR)
        self.assertTrue(r.may_conclude, "a healthy unit should still permit a verdict")
        self.assertEqual([u.name for u in r.usable], ["healthy"])
        self.assertEqual([u.name for u in r.excluded], ["dead"])

    def test_the_refusal_is_empty_only_when_a_verdict_is_permitted(self):
        self.assertEqual(assess({"ok": 0.9}, POWER_FLOOR).refusal(), "")
        self.assertNotEqual(assess({"no": 0.1}, POWER_FLOOR).refusal(), "")

    def test_a_unit_exactly_at_the_floor_is_usable(self):
        self.assertTrue(assess({"edge": POWER_FLOOR}, POWER_FLOOR).may_conclude)


class TestPass9SwallowedErrorsBecomeFacts(unittest.TestCase):
    """Pass 9. Three quarters that return HTTP 500 were read as 'no markets resolved then'.

    An early probe returned ``[]`` on any exception, so an upstream fault and a genuinely empty
    result were the same value. The distinction between 'measured zero' and 'failed to measure' is
    the whole of ``AXIOMS`` A6/G5.
    """

    def test_a_failed_window_reports_the_failure_rather_than_looking_empty(self):
        with mock.patch.object(pm, "_get_retry",
                               side_effect=urllib.error.HTTPError("u", 500, "e", None, None)), \
             mock.patch.object(pm.time, "sleep", lambda s: None), \
             mock.patch.object(pm, "cache_dir", lambda: Path(self.tmp)):
            markets, failed = pm.fetch_window("2025-01-01", "2025-04-01")
        self.assertEqual(markets, [])
        self.assertTrue(failed, "a 500 must be reported as a failed offset, not as an empty window")

    def test_a_genuinely_empty_window_reports_no_failures(self):
        with mock.patch.object(pm, "_get_retry", return_value=[]), \
             mock.patch.object(pm.time, "sleep", lambda s: None), \
             mock.patch.object(pm, "cache_dir", lambda: Path(self.tmp)):
            markets, failed = pm.fetch_window("2025-01-01", "2025-04-01")
        self.assertEqual(markets, [])
        self.assertEqual(failed, [], "measured-empty must be distinguishable from failed-to-measure")

    def setUp(self):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.tmp = self._td.name

    def tearDown(self):
        self._td.cleanup()


class TestPass10FailedFetchesAreNeverCached(unittest.TestCase):
    """Pass 10. ``fetch_history`` cached ``[]`` on any exception.

    One transient network failure became a permanent, silent exclusion: the market counted as
    ``no_history`` in every later run, forever, with nothing recording that a fetch had failed.
    Measured exposure at the time: 618 of 14,005 cached histories empty, provenance unknown. A
    re-probe of 60 found 0 recoverable, so nothing was contaminated — but the hazard was real.
    """

    def setUp(self):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _cache_files(self):
        return list((self.tmp / "history").glob("*.json"))

    def test_a_failed_fetch_writes_nothing(self):
        with mock.patch.object(pm, "_get_retry",
                               side_effect=urllib.error.URLError("down")), \
             mock.patch.object(pm, "cache_dir", lambda: self.tmp):
            self.assertEqual(pm.fetch_history("tok"), [])
            self.assertEqual(self._cache_files(), [],
                             "a failure must not be cached - the next run has to retry")

    def test_a_successful_empty_fetch_is_cached_because_it_is_a_measurement(self):
        with mock.patch.object(pm, "_get_retry", return_value={"history": []}), \
             mock.patch.object(pm.time, "sleep", lambda s: None), \
             mock.patch.object(pm, "cache_dir", lambda: self.tmp):
            self.assertEqual(pm.fetch_history("tok"), [])
        files = self._cache_files()
        self.assertEqual(len(files), 1, "a measured-empty history IS a result and is cached")
        self.assertEqual(json.loads(files[0].read_text(encoding="utf-8")), [])

    def test_a_retry_that_recovers_is_cached_normally(self):
        calls = {"n": 0}

        def flaky(url, timeout=40):
            calls["n"] += 1
            if calls["n"] < 2:
                raise urllib.error.HTTPError(url, 500, "e", None, None)
            return {"history": [{"t": 1, "p": 0.5}]}

        with mock.patch.object(pm, "_get", flaky), \
             mock.patch.object(pm.time, "sleep", lambda s: None), \
             mock.patch.object(pm, "cache_dir", lambda: self.tmp):
            self.assertEqual(len(pm.fetch_history("tok")), 1)
        self.assertEqual(len(self._cache_files()), 1)


class TestPass9ControlsMustContainTheirHypothesis(unittest.TestCase):
    """Pass 9. ``inject_banded_signal`` banded on ``pi``; every protocol sees only ``market``.

    A control that does not contain the hypothesis it names cannot falsify it, and it fails quietly —
    every number it produces looks plausible.
    """

    def test_the_bias_is_visible_in_the_variable_the_protocols_actually_see(self):
        w = inject_banded_signal(n_events=500, contracts_per_event=2, bias=1.6,
                                 band=(0.40, 0.60), seed=21)
        assert w.truth is not None
        labels = stratify_by_price(w.market)
        leaked = [
            lab for m, t, lab in zip(w.market, w.truth, labels)
            if abs(m - t) > 1e-9 and lab != "mid"
        ]
        self.assertEqual(leaked, [], "bias outside the stated band is invisible to any protocol")


class TestPass8ApparatusCeilingsAreNotDataCeilings(unittest.TestCase):
    """Pass 8/9. ``--limit 900`` was read as the available sample; ``offset`` 2100 as the universe.

    Both were argument or API ceilings mistaken for properties of the data. The constants that encode
    those ceilings must stay explicit so the next reader sees a limit rather than a fact.
    """

    def test_the_pagination_ceiling_is_named_and_documented_as_an_api_limit(self):
        self.assertEqual(pm.MAX_OFFSET, 2000)
        doc = pm.__doc__ or ""
        src = (ROOT / "kairos" / "polymarket.py").read_text(encoding="utf-8")
        self.assertIn("26,143", src,
                      "the windowed reach must stay recorded next to the offset ceiling, so the "
                      "ceiling is never re-read as the size of the universe")

    def test_windows_exist_as_the_documented_escape(self):
        self.assertTrue(hasattr(pm, "fetch_window"))
        self.assertTrue(hasattr(pm, "quarterly_windows"))


class TestPass5CensusApparatusBugs(unittest.TestCase):
    """Pass 5. Four apparatus bugs in one feasibility probe, each producing a confident wrong number.

    The worst was a bare ``urllib`` request getting HTTP 403 from a host ``curl`` reached at 200 — a
    false blocker that would have killed the whole Class A programme on an apparatus artefact.
    """

    def test_requests_carry_a_browser_user_agent(self):
        """The 403: the CLOB host rejects urllib's default agent and accepts a browser one."""
        ua = pm.HEADERS.get("User-Agent", "")
        self.assertTrue(ua and "python" not in ua.lower(),
                        f"default urllib agent gets 403 from this host; got {ua!r}")

    def test_resolution_is_parsed_with_a_tolerance_not_exact_equality(self):
        """Resolved markets report near-0/near-1 floats; `== 1.0` reported 0% resolved."""
        self.assertGreater(pm.RESOLUTION_TOL, 0.0)
        self.assertEqual(pm.resolution_of({"outcomePrices": '["0.99999", "0.00001"]'}), 1.0)
        self.assertEqual(pm.resolution_of({"outcomePrices": '["0.00001", "0.99999"]'}), 0.0)
        # and an unresolved market is still refused rather than rounded into a verdict
        self.assertIsNone(pm.resolution_of({"outcomePrices": '["0.62", "0.38"]'}))

    def test_horizon_comes_from_measured_history_not_a_nominal_end_date(self):
        """Nominal endDate reported '367 days' for a market whose price history spans a week."""
        day = 86400
        hist = [{"t": 1_700_000_000 + i * day, "p": 0.5} for i in range(8)]
        o = pm.admit(
            {"id": "m", "outcomePrices": '["1","0"]', "endDate": "2099-01-01T00:00:00Z"},
            hist, lead_hours=24.0,
        )
        self.assertIsNotNone(o)
        self.assertLess(o.days_to_resolution, 10.0,
                        "horizon must be measured from the price path, not read off endDate")


class TestPass6SignificanceWithoutMateriality(unittest.TestCase):
    """Pass 6. ``B_settle`` was declared a survivor at p=0.0005 on **0.024%** of the benchmark.

    A deterministic monotone transform has almost no variance in its paired differences, so it can be
    overwhelmingly significant and worth nothing. Every runner that renders a verdict carries a
    materiality floor alongside its alpha.
    """

    def test_every_verdict_runner_declares_a_materiality_floor(self):
        for script in ("gate1.py", "gate2.py", "replicate.py"):
            src = (ROOT / script).read_text(encoding="utf-8")
            self.assertIn("MIN_RELATIVE_GAIN", src,
                          f"{script} renders a verdict without a materiality floor")

    def test_the_floor_is_a_real_threshold_in_each_runner(self):
        import importlib
        for mod in ("gate1", "gate2", "replicate"):
            m = importlib.import_module(mod)
            self.assertGreater(getattr(m, "MIN_RELATIVE_GAIN"), 0.0, mod)


class TestPass7AnchoringAndScale(unittest.TestCase):
    """Pass 7. Two defects that changed every number without changing the headline.

    Unstandardised features let ``maturity`` diverge to a log score of 4.82 against a 0.336
    benchmark, and forecast-**error** correlation read 0.97 between models built on unrelated
    features because market-anchored errors share the ``q - y`` term.
    """

    def test_forecaster_features_are_standardised_so_scale_cannot_dominate(self):
        from kairos.forecasters import ForecasterSpec
        from tests.test_forecasters import obs as make_obs

        train = [make_obs(i, 0.4 + 0.001 * i, float(i % 2),
                          age_days=float(i), n_before=float(i * 3)) for i in range(60)]
        pred = ForecasterSpec("maturity", ("age_days", "n_before")).fit(train)
        self.assertTrue(all(0.0 < pred(o) < 1.0 for o in train))

    def test_both_correlation_diagnostics_exist_so_anchoring_is_visible(self):
        from kairos import forecasters as f

        self.assertTrue(hasattr(f, "error_correlations"))
        self.assertTrue(hasattr(f, "tilt_correlations"),
                        "tilt correlation is the diagnostic that survives market anchoring")


class TestPass11CarryIsChargedOnceAndTheTwoModelsDoNotDrift(unittest.TestCase):
    """Pass 11. The repo holds two carry models and they disagree at long horizons.

    ``SettlementTerms`` discounts (``1/(1+wt)``); ``CostModel.carry`` is linear (``base*wt``). The gap
    is 0.0034 at one year and **0.0129 at two** - larger than a plausible arbitrage, at exactly the
    horizons where negRisk groups are most numerous. Gate B showed it is currently *masked* by
    spread rather than absent, so it is pinned here instead of unified: a silent widening would
    reach a scanner before anyone noticed.
    """

    def test_the_known_gap_between_the_two_carry_models_has_not_widened(self):
        from kairos.baseline import SettlementTerms
        from kairos.costs import CONSERVATIVE

        for days, known in ((7.0, 0.0000), (90.0, 0.0003), (365.0, 0.0034), (730.0, 0.0129)):
            implied = 1.0 - SettlementTerms(days_to_settlement=days).discount_factor
            linear = CONSERVATIVE.carry(1.0, days)
            gap = abs(implied - linear)
            self.assertLessEqual(
                gap, known + 5e-4,
                f"the carry models diverged further at {days:.0f}d: {gap:.5f} vs a recorded "
                f"{known:.4f}. Unify them or re-record the gap deliberately.",
            )

    def test_the_structural_scanner_charges_carry_exactly_once(self):
        """AXIOMS C7: `effective_yes_cost` already includes carry, so the payoff stays nominal."""
        from kairos.costs import CONSERVATIVE
        from kairos.structural import fair_group, scan

        g = fair_group(n_legs=4, days=730.0, seed=5)
        expected = 1.0 - sum(
            CONSERVATIVE.effective_yes_cost(leg.price, g.days_to_settlement) for leg in g.legs
        )
        self.assertAlmostEqual(scan(g).edge, expected, places=12)

    def test_a_positive_control_must_not_be_defined_by_the_detector_it_tests(self):
        """The circularity Gate B's first version shipped, and the fix."""
        from kairos.structural import fair_group, obvious_arbitrage

        g = obvious_arbitrage(fair_group(n_legs=5, days=30.0, seed=2), nominal_sum=0.70)
        self.assertAlmostEqual(g.nominal_sum, 0.70, places=9,
                               msg="the independent control is defined on quotes alone")


class TestPass12LegSetCompletenessIsVerifiedNotAsserted(unittest.TestCase):
    """Pass 12. Gate B measured that the whole Class B defence rests outside the scanner.

    Real groups assembled through offset pagination were **49% truncated**, missing 60% of their
    legs. A group missing three fifths of its legs presents as a spectacular arbitrage, so a scanner
    trusting an asserted leg set is not slightly wrong, it is wrong about half the time.
    """

    def test_the_verified_scanner_refuses_a_bare_boolean(self):
        """The old interface must fail loudly rather than be silently accepted."""
        from kairos.structural import Leg, NegRiskGroup, scan_verified

        g = NegRiskGroup("g", (Leg("a", 0.1, 500.0), Leg("b", 0.1, 500.0)), 30.0,
                         legs_are_complete=True, outcomes_are_exhaustive=True)
        with self.assertRaises(TypeError):
            scan_verified(g, True)

    def test_exhaustiveness_tolerance_scales_with_the_edge(self):
        """Failure costs the stake, not the edge, so a thin edge cannot absorb the residual risk."""
        from kairos.legset import break_even_failure_rate, residual_failure_bound

        bound = residual_failure_bound()
        # Derived from the bound, not pinned to an edge: the tolerable edge moves as the
        # exhaustiveness sample grows (0.04 at 75 trials, 0.0059 at 512), and a hard-coded
        # number would have to be edited each time - which is when a regression slips through.
        too_thin = (bound * 0.5) * 0.95 / (1.0 - bound * 0.5)
        thick = (min(bound * 5.0, 0.5)) * 0.95 / (1.0 - min(bound * 5.0, 0.5))
        self.assertGreater(bound, break_even_failure_rate(too_thin, 0.95))
        self.assertLess(bound, break_even_failure_rate(thick, 0.95))

    def test_the_residual_bound_is_never_zero_however_many_trials_pass(self):
        from kairos.legset import residual_failure_bound

        self.assertGreater(residual_failure_bound(100000, 0), 0.0)

    def test_neg_risk_request_id_is_never_read_as_a_field(self):
        """Measured per-market: 2,896 ids across 2,896 markets. Grouping on it yields singletons.

        Checked by parsing rather than by grepping. A text search matches the docstring that records
        the finding, which is how the first version of this guard failed — asserting a property it
        could not actually check (AXIOMS G7).
        """
        import ast

        src = (ROOT / "kairos" / "legset.py").read_text(encoding="utf-8")
        self.assertIn("negRiskRequestID", src,
                      "the finding must stay recorded next to the code it warns about")

        offenders = []
        for module in ("legset.py", "structural.py"):
            path = ROOT / "kairos" / module
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                # m.get("negRiskRequestID")
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "get" and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value == "negRiskRequestID"):
                    offenders.append(f"{module}: .get(...)")
                # m["negRiskRequestID"]
                if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                        and node.slice.value == "negRiskRequestID"):
                    offenders.append(f"{module}: subscript")
        self.assertEqual(offenders, [],
                         f"negRiskRequestID read as a field: {offenders}. It is per-market.")


class TestPass13ExhaustivenessConstantsAreMeasuredNotTyped(unittest.TestCase):
    """Pass 13. The bound decides which trades are allowed, so it must not be a hand-typed number.

    Extending the sample 75 -> 512 moved the tradeable floor from ~5% to ~1%. That makes
    ``EXHAUSTIVENESS_TRIALS`` a load-bearing trading parameter: a value typed in by hand is a rule
    with no evidence behind it.
    """

    def test_the_constants_have_a_reproducible_generator(self):
        script = ROOT / "exhaustiveness.py"
        self.assertTrue(script.is_file(), "the measurement must be re-runnable, not an ad-hoc probe")
        src = (ROOT / "kairos" / "legset.py").read_text(encoding="utf-8")
        self.assertIn("exhaustiveness.py", src,
                      "legset must name the script that generates its constants")

    def test_the_generator_checks_the_survivorship_channel(self):
        """A voided group would be dropped by a clean-resolution filter, hiding real failures."""
        src = (ROOT / "exhaustiveness.py").read_text(encoding="utf-8")
        self.assertIn("voided", src)

    def test_the_bound_never_reaches_zero_however_large_the_sample(self):
        from kairos.legset import residual_failure_bound

        self.assertGreater(residual_failure_bound(10**7, 0), 0.0)

    def test_tolerance_tests_derive_their_edges_from_the_bound(self):
        """Guards the fix itself: a hard-coded edge silently rots as the sample grows."""
        src = (ROOT / "tests" / "test_legset.py").read_text(encoding="utf-8")
        self.assertIn("_edges_around_the_bound", src)
        self.assertIn("residual_failure_bound()", src)

    def test_the_recorded_sample_only_ever_grows(self):
        from kairos.legset import EXHAUSTIVENESS_FAILURES, EXHAUSTIVENESS_TRIALS

        self.assertGreaterEqual(EXHAUSTIVENESS_TRIALS, 512)
        self.assertEqual(EXHAUSTIVENESS_FAILURES, 0,
                         "a failure would widen the bound - re-derive it, do not ignore it")


class TestPass14BookApparatus(unittest.TestCase):
    """Pass 14. Three apparatus facts, each of which alone produces a confidently wrong price."""

    def test_the_book_is_normalised_best_first(self):
        """Live CLOB sorts both sides worst-first; asks[0] was 0.999 on every market probed."""
        from kairos.book import parse_book

        b = parse_book({"asks": [{"price": "0.999", "size": "1"}, {"price": "0.40", "size": "1"}],
                        "bids": [{"price": "0.10", "size": "1"}, {"price": "0.30", "size": "1"}]})
        self.assertEqual(b.best_ask, 0.40)
        self.assertEqual(b.best_bid, 0.30)

    def test_a_crossed_price_is_not_charged_spread_twice(self):
        """AXIOMS C7 in its Class B form."""
        from kairos.costs import CONSERVATIVE

        vwap = 0.48
        self.assertLess(CONSERVATIVE.effective_yes_cost_at(vwap, 30.0),
                        CONSERVATIVE.effective_yes_cost(vwap, 30.0))

    def test_book_failures_carry_a_reason_rather_than_a_bare_none(self):
        """The bucket-merge that read as 'the venue is illiquid' when 0 groups were thin."""
        import inspect

        from kairos.book import fetch_book_result

        sig = inspect.signature(fetch_book_result)
        self.assertIn("token_id", sig.parameters)
        src = inspect.getsource(fetch_book_result)
        for reason in ("http_", "network", "unparseable"):
            self.assertIn(reason, src, "each failure mode must be nameable, not merged")

    def test_the_scanner_separates_thin_from_unfetchable(self):
        src = (ROOT / "scanb.py").read_text(encoding="utf-8")
        self.assertIn("book_too_thin_at_size", src)
        self.assertIn("unfetchable", src)
        self.assertIn("group_has_untradeable_legs", src)

    def test_the_untradeable_predictor_is_active_not_the_obvious_flags(self):
        """enableOrderBook and acceptingOrders were True on every 404 leg; only `active` tracked."""
        src = (ROOT / "scanb.py").read_text(encoding="utf-8")
        self.assertIn('m.get("active")', src,
                      "the scanner must filter on `active`, the only measured predictor")


class TestPass15OpenItemsStayClosed(unittest.TestCase):
    """Pass 15. A status is a claim; an unmaintained one is a false claim (G8, one level up)."""

    def test_the_withdrawn_manipulation_threshold_cannot_return(self):
        from kairos.gate import GateConfig

        self.assertFalse(hasattr(GateConfig(), "min_manipulation_cost_multiple"))

    def test_a_price_settled_market_needs_a_written_analysis_not_a_number(self):
        from kairos.costs import CONSERVATIVE
        from kairos.gate import GateConfig, MarketSnapshot, evaluate

        m = MarketSnapshot(market_id="m", mid=0.5, days_to_resolution=30.0,
                           depth_contracts=10_000.0, settles_on_tradeable_price=True,
                           settlement_manipulation_cost=1e9)
        d = evaluate(0.9, m, costs=CONSERVATIVE, config=GateConfig(),
                     member_forecasts=(0.9, 0.9, 0.9), intended_contracts=10.0)
        self.assertIn("resolution_manipulability", [c.name for c in d.failures])

    def test_the_unrelated_q_star_in_legset_was_not_swept_up_by_the_rename(self):
        """legset's q* is the break-even failure rate. A mass rename would have corrupted it."""
        src = (ROOT / "kairos" / "legset.py").read_text(encoding="utf-8")
        self.assertIn("q* = edge / (edge + stake)", src)

    def test_no_live_module_still_calls_the_benchmark_q_star(self):
        for mod in ("sizing.py", "__init__.py"):
            src = (ROOT / "kairos" / mod).read_text(encoding="utf-8")
            self.assertNotIn("(p, q*)", src, f"{mod} still uses the withdrawn symbol")

    def test_a_rejected_candidate_protocol_does_not_gate_the_incumbent(self):
        """Gate 0b rejected stratification; it must not veto the verdict on the pipeline in use."""
        from kairos.nullworld import WorldReport

        strat = WorldReport("signal_strong", True, "strat_maxt", 10, 2)
        kairos = WorldReport("signal_strong", True, "kairos", 10, 7)
        self.assertFalse(strat.is_gate_condition, "a rejected challenger must be an exhibit")
        self.assertTrue(kairos.is_gate_condition)

    def test_discovery_sweeps_both_ends_of_the_volume_distribution(self):
        """A head-only null is weakest exactly where the literature expects an edge."""
        src = (ROOT / "scanb.py").read_text(encoding="utf-8")
        self.assertIn('for ascending in ("false", "true")', src)


class TestPass16SilentOpenItems(unittest.TestCase):
    """Pass 16. The open items that do not announce themselves: no test, no caller, no status."""

    def test_every_core_module_has_a_dedicated_test_file_or_a_named_home(self):
        """`costs.py` was used by six suites as a fixture and checked by none of them."""
        homes = {"validity.py": "test_regressions.py"}  # tested, deliberately not same-named
        missing = []
        for mod in (ROOT / "kairos").glob("*.py"):
            if mod.name == "__init__.py":
                continue
            if (ROOT / "tests" / f"test_{mod.stem}.py").exists():
                continue
            if mod.name in homes and (ROOT / "tests" / homes[mod.name]).exists():
                continue
            missing.append(mod.name)
        self.assertEqual(missing, [], f"core modules with no test home: {missing}")

    def test_the_documented_no_trade_band_is_pinned(self):
        from kairos.costs import CONSERVATIVE

        self.assertAlmostEqual(CONSERVATIVE.round_trip_drag(0.50, 30.0), 0.050, places=3)

    def test_the_deleted_orphans_stay_deleted(self):
        import kairos.polymarket as pm

        for gone in ("AdapterError", "fetch_resolved_markets_windowed"):
            self.assertFalse(hasattr(pm, gone), f"{gone} was deleted as unconsumed (E1)")

    def test_the_scorer_that_only_looked_dead_is_still_wired(self):
        """`brier_score_pointwise` was flagged as an orphan and is not one."""
        from kairos.score import brier_score, brier_score_pointwise

        self.assertAlmostEqual(brier_score([0.5, 0.5], [1.0, 0.0]), 0.25, places=9)
        self.assertEqual(len(brier_score_pointwise([0.5, 0.5], [1.0, 0.0])), 2)

    def test_every_gate_declares_a_status(self):
        """A gate with no status cannot be told apart from one that was forgotten."""
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        blocks = proto.split("\n## Gate ")[1:]
        unmarked = [b.splitlines()[0] for b in blocks if "STATUS" not in b.split("\n## ")[0]]
        self.assertEqual(unmarked, [], f"gates with no STATUS line: {unmarked}")


class TestPass17GateCRegistration(unittest.TestCase):
    """Pass 17. Gate C is registered before its data exists; the registration must stay honest."""

    def test_gate_c_is_registered_with_a_status(self):
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("## Gate C", proto)
        self.assertIn("STATUS", proto.split("## Gate C")[1][:400])

    def test_the_kill_rule_is_registered_and_terminal(self):
        """A stopping condition that says 'try another venue' is not a stopping condition."""
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("200 verified pairs", proto)
        self.assertIn("programme ends", proto)

    def test_the_semantic_null_worlds_are_all_named(self):
        """Seven kinds of near-miss pair, each of which the matcher must refuse.

        Searches the document rather than slicing a section. The first version sliced on
        ``"## Gate C"``, which matches **twice** — the h2 heading and the h3
        ``### Gate C — the semantic-identity null gate`` that contains it as a substring — so
        ``[1]`` returned the text *between* the two headings and the null worlds appeared missing
        from a registration that contained them. A brittle locator reporting a real document as
        incomplete is the same class of error as a probe reporting a live endpoint as dead (G2).
        """
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        for world in ("Horizon mismatch", "Threshold mismatch", "Scope mismatch",
                      "Resolution-source mismatch", "Settlement-time mismatch",
                      "Negation pair", "Random pairing"):
            self.assertIn(world, proto, f"null world {world!r} missing from the registration")

    def test_divergence_risk_reuses_the_measured_bound_not_a_flag(self):
        from kairos.legset import break_even_failure_rate, residual_failure_bound

        self.assertGreater(residual_failure_bound(), 0.0)
        self.assertAlmostEqual(break_even_failure_rate(0.05, 0.95), 0.05, places=9)

    def test_the_protocol_status_and_the_runner_on_disk_agree(self):
        """The protocol's claim about what has run must match what exists. Both directions.

        This guard has now gone inert **twice** by being written as a one-way conditional. Version
        one asserted ``gatec.py`` did not exist while Gate C was REGISTERED, NOT RUN; building the
        gate made its precondition false and it early-returned forever. Version two said the same
        thing about ``scanc.py`` and died the same way one step later. A guard whose precondition is
        the thing it is guarding *against* stops applying at exactly the moment it starts mattering.

        So it is stated as an invariant with no escape branch: exactly one status marker is present,
        and the runner exists if and only if the status says it ran. Whichever way the protocol
        moves, one half of this assertion is live (AXIOMS G8).
        """
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        not_run = "MEASUREMENT NOT RUN" in proto
        run = "MEASUREMENT RUN" in proto
        self.assertNotEqual(not_run, run,
                            "the protocol must say exactly one of MEASUREMENT RUN / MEASUREMENT "
                            "NOT RUN; both or neither means the status cannot be read")
        self.assertEqual((ROOT / "scanc.py").exists(), run,
                         "the protocol's status and the runner on disk disagree")


class TestPass18GateCRun(unittest.TestCase):
    """Pass 18. Gate C ran, passed, and falsified its own registration twice."""

    def test_the_registration_records_that_its_evidence_list_was_incomplete(self):
        """The five frozen fields could not refuse a null world the same document registered."""
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("all six must agree", proto)
        self.assertIn("Amended 2026-09-09 from five to six", proto)

    def test_the_false_pair_that_the_pass_column_could_not_see_stays_fixed(self):
        """Two different year-like strikes were declared the same event (CORRECTIONS Pass 18.2)."""
        from kairos.identity import RawMarket, same_event

        rules = ("Settles YES if gold closes above X. Source: the primary spot index. "
                 "Determination at 16:00 UTC on 2027-03-31.")
        left = RawMarket("kalshi", "A", "gold closes above 2000 - Mar 31, 2027", rules,
                         "2027-03-31T16:00:00Z")
        right = RawMarket("kalshi", "B", "gold closes above 2050 - Mar 31, 2027", rules,
                          "2027-03-31T16:00:00Z")
        verdict = same_event(left, right)
        self.assertFalse(verdict.paired, "2000 and 2050 are different strikes")
        self.assertIn("threshold_differs", verdict.refusals)

    def test_the_control_carries_a_year_like_strike(self):
        """The world could not have caught 18.2 because the control never carried one (G6)."""
        from kairos.identity import _THRESHOLDS

        self.assertIn(2000.0, _THRESHOLDS,
                      "a strike inside 1900-2099 must be reachable in every world, not only as "
                      "arithmetic inside threshold_mismatch")

    def test_the_gate_counts_refusal_reasons_not_only_refusals(self):
        """G10. The reason column is what exposed 18.2; a rate column could not."""
        source = (ROOT / "gatec.py").read_text(encoding="utf-8")
        self.assertIn("refusal_counts", source)
        self.assertIn("principal refusal", source,
                      "the gate's table must report WHY each world was refused (AXIOMS G10)")

    def test_every_comparison_in_the_matcher_is_load_bearing(self):
        """A gate no broken instrument would fail is decoration. Kill-tests live in
        tests/test_identity.py; this asserts the matrix has not been quietly emptied."""
        from tests.test_identity import NECESSITY

        self.assertEqual(len(NECESSITY), 7)
        worlds = {world for _, world in NECESSITY}
        self.assertEqual(len(worlds), 7, "each null world must justify a distinct check")


class TestPass19CrossVenueMeasurement(unittest.TestCase):
    """Pass 19. The measurement ran; all three withdrawn claims were apparatus, none inference."""

    def test_unavailable_evidence_is_not_reported_as_disagreement(self):
        """19.1. A reason that fires on every pair drives the sole-blocker column to zero."""
        from kairos.identity import ParsedIdentity, compare_identities

        blank = ParsedIdentity(frozenset({"a"}), None, "2027-01-01T00:00Z", frozenset(), False,
                               ("resolution_source",))
        known = ParsedIdentity(frozenset({"a"}), None, "2027-01-01T00:00Z",
                               frozenset({"x"}), False, ())
        refusals = compare_identities(blank, known).refusals
        self.assertIn("unrecoverable:left:resolution_source", refusals)
        self.assertNotIn("resolution_source_differs", refusals)

    def test_a_nominal_day_boundary_is_not_a_determination_instant(self):
        """19.2. Polymarket's endDate was being fed to a settlement-instant check."""
        from kairos.crossvenue import polymarket_descriptor

        d = polymarket_descriptor({
            "id": "1", "question": "Will X happen?", "description": "Rules.",
            "endDate": "2027-01-01T00:00:00Z", "clobTokenIds": '["y", "n"]',
        })
        self.assertIn("settlement_time", d.identity.missing)

    def test_the_kalshi_book_is_mirrored_not_read_directly(self):
        """The apparatus fact that would have produced a false positive on every pair."""
        from kairos.kalshi import books_from_orderbook

        yes, _ = books_from_orderbook({"orderbook_fp": {
            "yes_dollars": [["0.4000", "50.00"]], "no_dollars": [["0.5500", "30.00"]]}})
        self.assertAlmostEqual(yes.best_ask, 0.45, places=9)
        self.assertAlmostEqual(yes.best_bid, 0.40, places=9)
        self.assertGreater(yes.best_ask, yes.best_bid, "reading yes_dollars as asks inverts the buy")

    def test_the_provisional_pairs_are_counted_and_not_priced(self):
        """Knowing the answer before the gate is how Look 1 spent its alpha."""
        source = (ROOT / "scanc.py").read_text(encoding="utf-8")
        self.assertIn("provisional", source)
        self.assertIn("left unpriced", source)
        priced = source.split("[4/4]")[1] if "[4/4]" in source else source
        self.assertNotIn("for p, k, kinds in provisional", priced.split("RESULT")[0],
                         "provisional pairs must not enter the pricing loop")

    def test_the_structural_zero_is_labelled_as_structural(self):
        """AXIOMS G12: a count fixed by an apparatus limit is not a measurement."""
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("The zero is structural", proto)
        self.assertIn("scanc.py", (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8"))


class TestPass20GateC2Extractor(unittest.TestCase):
    """Pass 20. The instrument was built, and it falsified the diagnosis that motivated it."""

    def test_the_extractor_reconstructs_a_real_markets_own_timestamp(self):
        """Polymarket's prose and its `endDate` are two independent sources for one instant."""
        from kairos.identity import extract_prose_instant

        instant, modality = extract_prose_instant(
            "...recognizes the Republic of Somaliland as a sovereign state by December 31, 2026, "
            "11:59 PM ET.")
        self.assertEqual(instant, "2027-01-01T04:59Z")
        self.assertEqual(modality, "deadline")

    def test_modality_is_evidence_not_a_footnote(self):
        """A barrier and a digital carry the same timestamp and different payoffs."""
        from kairos.identity import ParsedIdentity, compare_identities

        def ident(modality):
            return ParsedIdentity(frozenset({"a"}), None, "2027-01-01T00:00Z", frozenset({"s"}),
                                  False, (), modality=modality)

        self.assertIn("modality_differs",
                      compare_identities(ident("deadline"), ident("instant")).refusals)
        self.assertTrue(compare_identities(ident("deadline"), ident("deadline")).paired)

    def test_the_two_ambiguous_hours_a_year_are_refused(self):
        """An hour of error makes a 12pm market look like a 1pm one (AXIOMS A6)."""
        from kairos.identity import extract_prose_instant

        self.assertEqual(extract_prose_instant("... on March 14, 2027 at 2:30 AM ET."), (None, None))
        self.assertEqual(extract_prose_instant("... on November 7, 2027 at 1:30 AM ET."),
                         (None, None))

    def test_the_withdrawn_pass_19_claim_is_not_still_asserted(self):
        """20.1: "a missing instrument, not a missing market" was refuted by building it."""
        for doc in ("PROTOCOL.md", "CORRECTIONS.md"):
            text = (ROOT / "docs" / doc).read_text(encoding="utf-8")
            for para in text.split("\n\n"):
                if "binding constraint is a missing" in para:
                    self.assertTrue(
                        "refuted" in para or "Withdrawn" in para or "wrong" in para,
                        f"{doc} still asserts the withdrawn Pass-19 diagnosis unqualified")

    def test_the_gate_covers_the_extractor_it_licenses(self):
        """An instrument used by the measurement must have a null world exercising it (A7)."""
        from kairos.identity import NULL_WORLDS

        names = {name for name, _ in NULL_WORLDS}
        self.assertIn("modality_mismatch", names)
        self.assertIn("prose_contradiction", names)


class TestPass21VenueBranchExhausted(unittest.TestCase):
    """Pass 21. The stopping rule's next move was taken and it terminated."""

    def test_the_three_requirements_are_stated_where_a_venue_is_rejected(self):
        """A rejected venue must stay rejected for a stated reason, not a vague one (C9a)."""
        source = (ROOT / "venues.py").read_text(encoding="utf-8")
        for requirement in ("Resolution rules", "determination instant", "Order-book depth"):
            self.assertIn(requirement, source)

    def test_the_probe_precedes_the_adapter(self):
        """Building an adapter and then finding the venue publishes no rules is the same error as
        scanning before gating."""
        source = (ROOT / "venues.py").read_text(encoding="utf-8")
        self.assertIn("feasibility probe before an adapter", source)
        for gone in ("predictit_descriptor", "smarkets_descriptor"):
            self.assertNotIn(gone, (ROOT / "kairos" / "crossvenue.py").read_text(encoding="utf-8"),
                             "no adapter may be built for a venue the probe rejected")

    def test_untestable_is_not_recorded_as_rejected(self):
        """A1. 'Cannot be measured' and 'measured and found absent' are different verdicts.

        This guard originally pinned Pass 21's NOT TESTABLE verdict. **Pass 22 withdrew that
        verdict** — it rested on a matcher whose recall had never been measured and turned out to be
        ~0 — so the guard now pins the distinction itself rather than the conclusion that used it.
        A guard tied to a specific verdict dies with the verdict; one tied to the principle does not.
        """
        log = (ROOT / "docs" / "CORRECTIONS.md").read_text(encoding="utf-8")
        self.assertIn("NOT TESTABLE", log)
        self.assertIn("has not been tried and found wanting", log)

    def test_the_deadlock_is_recorded_rather_than_resolved(self):
        """The remaining step needs the permission that passing the protocol was meant to earn."""
        log = (ROOT / "docs" / "CORRECTIONS.md").read_text(encoding="utf-8")
        self.assertIn("F3", log)
        self.assertIn("deadlock", log.lower())


class TestPass22RecallIsTheBindingConstraint(unittest.TestCase):
    """Pass 22. Recall measured at 0/26; three passes of conclusions withdrawn."""

    def test_a_gate_must_not_claim_power_it_measured_against_its_own_dialect(self):
        """G14. Precision transfers out of a null world; power does not."""
        axioms = (ROOT / "docs" / "AXIOMS.md").read_text(encoding="utf-8")
        self.assertIn("G14", axioms)
        self.assertIn("Precision transfers out of a null world", axioms)

    def test_the_recall_probe_selects_candidates_the_matcher_cannot_influence(self):
        """A gold set screened by the instrument under test measures the instrument against
        itself - which is exactly the defect it exists to detect."""
        source = (ROOT / "recall.py").read_text(encoding="utf-8")
        self.assertIn("took no part in selection", source.lower())
        selection = source.split("scored.sort")[0]
        self.assertNotIn("verdict.paired", selection,
                         "candidate selection must not consult the matcher under test")

    def test_the_withdrawn_claims_are_not_still_asserted(self):
        """22.1-22.3: 'few fungible events', 'NOT TESTABLE', and the F3 'deadlock'."""
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("withdrew the conclusion drawn here", proto)
        self.assertIn("was a misreading", proto)
        for para in proto.split(chr(10) + chr(10)):
            if "very few mutually fungible events" in para:
                self.assertIn("withdrew", para,
                              "PROTOCOL still asserts the falsified claim unqualified")

    def test_f3_forbids_execution_not_reading(self):
        """The constraint was quoted for three passes without being read."""
        axioms = (ROOT / "docs" / "AXIOMS.md").read_text(encoding="utf-8")
        f3 = axioms.split("**F3.")[1].split("**F")[0]
        for forbidden in ("broker integration", "live capital", "production executor"):
            self.assertIn(forbidden, f3)
        self.assertNotIn("market data", f3, "F3 says nothing about reading market data")


class TestPass23AlignmentTable(unittest.TestCase):
    """Pass 23. The recall floor, the adjudicated table, and the first completed measurement."""

    def _table(self):
        import json
        return json.loads((ROOT / "docs" / "ALIGNMENT.json").read_text(encoding="utf-8"))

    def test_the_recall_floor_is_the_repos_existing_constant(self):
        """A floor invented after seeing the instrument score zero is a floor chosen to clear."""
        proto = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("RECALL_FLOOR = POWER_FLOOR = 0.50", proto)

    def test_every_surfaced_candidate_is_adjudicated(self):
        """A pool with unlabelled members lets the adjudicator skip the awkward ones."""
        table = self._table()
        labels = {p["label"] for p in table["pairs"]}
        self.assertTrue(labels <= {"IDENTICAL", "FUNGIBLE-WITH-BASIS", "DISTINCT"})
        self.assertTrue(all(p.get("reason") for p in table["pairs"]),
                        "every label must carry its reason - an unexplained label is an assertion")

    def test_no_pair_is_certified_riskless(self):
        """IDENTICAL is empty: resolution criteria could not be verified equal from published text."""
        table = self._table()
        self.assertEqual(table["identical_count"], 0)
        self.assertEqual([p for p in table["pairs"] if p["label"] == "IDENTICAL"], [])

    def test_the_table_was_adjudicated_before_prices(self):
        """The one protection that matters, and it is a property of the program, not a promise."""
        source = (ROOT / "align.py").read_text(encoding="utf-8")
        self.assertIn("Fetches no prices", source)
        for pricing in ("cost_to_buy", "fetch_book_result", "best_direction"):
            self.assertNotIn(f"from kairos.book import {pricing}", source)
        self.assertIn("no price data fetched", self._table()["adjudicated"])

    def test_the_measurement_reports_fee_sensitivity(self):
        """A negative median must say whether its sign turns on an unverified fee schedule."""
        source = (ROOT / "scanc.py").read_text(encoding="utf-8")
        self.assertIn("FEE SENSITIVITY", source)
        self.assertIn("zero_fee", source)


class TestPass24AlignmentGuards(unittest.TestCase):
    """Pass 24. Group labels produced 40% false pairs; the guards are what makes the table usable."""

    def test_subject_containment_rejects_a_different_organisation(self):
        """BRICS paired with OPEC and claimed a +0.169 edge."""
        import adjudicate

        self.assertTrue(adjudicate.tokens("Will another country leave OPEC in 2026?")
                        - adjudicate.tokens("Will a country leave BRICS in 2026?"),
                        "the Kalshi event must carry a token the Polymarket title lacks")

    def test_subject_containment_rejects_a_different_person(self):
        """Trump paired with Gianni Infantino and claimed a +0.106 edge."""
        import adjudicate

        absent = (adjudicate.tokens("Gianni Infantino out as President of FIFA in 2026")
                  - adjudicate.tokens("Trump out as President by September 30?"))
        self.assertIn("infantino", absent)

    def test_a_group_whose_outcomes_cannot_be_checked_is_refused_whole(self):
        """'R Senate, D House' against 'R-House, D-Senate' is an inversion in single letters."""
        import adjudicate

        self.assertIn("2026 Midterms: Congress Balance of Power?", adjudicate.UNVERIFIABLE)
        self.assertEqual(adjudicate.tokens("R Senate, D House"),
                         adjudicate.tokens("R-House, D-Senate"),
                         "no token rule separates these - which is why the group is refused")

    def test_every_aligned_pair_passes_both_guards(self):
        import json

        import adjudicate

        table = json.loads((ROOT / "docs" / "ALIGNMENT.json").read_text(encoding="utf-8"))
        for pair in table["pairs"]:
            if pair["label"] == "DISTINCT":
                continue
            key = adjudicate.ascii_safe(pair["kx_title"]).split(" / ")[0].strip()
            pm = adjudicate.tokens(pair["pm_title"])
            self.assertEqual(adjudicate.tokens(key) - pm, set(),
                             f"aligned pair fails subject containment: {pair['pm_title']}")

    def test_the_runner_can_announce_a_pass_not_only_a_withhold(self):
        """A runner that structurally cannot report success is not a measurement."""
        source = (ROOT / "scanc.py").read_text(encoding="utf-8")
        block = source.split("def run_alignment")[1]
        self.assertIn("TERMINAL branch applies", block)
        self.assertIn("CLEARS both venues", block)


class TestPass25ClassCRegistration(unittest.TestCase):
    """Pass 25. Class C is registered before it is built, and argues against itself."""

    def _proto(self):
        return (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")

    def test_class_c_declares_a_status(self):
        self.assertIn("## Class C", self._proto())
        self.assertIn("STATUS: GATE D.0 RUN", self._proto().split("## Class C")[1][:400])

    def test_nothing_is_built_while_it_is_marked_not_run(self):
        """Registration precedes the build, and this fails the moment that stops being true.

        Gate D.0 has run (Pass 26), so ``gated.py`` is licensed and the clause no longer names it.
        ``scand.py`` is still governed: **Gate D.0 licenses Gate D at most, never the measurement**,
        and Gate D has not been run. A convergence pipeline standing here before its null gate is
        the A7 violation the whole protocol is built to prevent.
        """
        self.assertFalse((ROOT / "scand.py").exists(),
                         "scand.py exists but Gate D (the convergence null gate) has not passed")

    def test_the_dead_on_arrival_check_precedes_the_build(self):
        """Four crossings against two: the arithmetic that could refute the class for free."""
        proto = self._proto()
        self.assertIn("Gate D.0", proto)
        self.assertIn("crosses four books", proto)
        self.assertIn("refuted before it is built", proto)

    def test_the_hedged_variant_is_the_registered_one(self):
        """The unhedged variant is cheaper and cannot fail cleanly."""
        proto = self._proto()
        self.assertIn("The hedged variant is registered", proto)

    def test_convergence_is_never_called_riskless(self):
        proto = self._proto()
        self.assertIn("Convergence is not arbitrage", proto)

    def test_the_null_worlds_name_bid_ask_bounce(self):
        """The false-positive generator must be named, not left as 'noise'."""
        self.assertIn("bid-ask bounce", self._proto().lower())


class TestPass26RegisteredExclusionsMustBeEnforcedOrReported(unittest.TestCase):
    """Pass 26. Gate D.0's verdict flipped on a precondition no scanner in this repo enforces.

    ``PROTOCOL.md`` excludes longshots *at every gate* and ``CostModel.price_in_band`` implements it,
    but it is called only in ``kairos.gate`` and ``kairos.sizing``. 52 of 81 priced pairs were out of
    band and the widest gap in the table sat on a market quoted at 3.8 cents, so the class is NOT
    REFUTED unbanded and REFUTED banded.

    The property this encodes is not "apply the band" — it is **a runner that renders a verdict a
    registered exclusion would change must report both readings** rather than pick one silently.
    """

    def test_the_round_trip_reports_what_it_traded_at_so_the_band_can_be_applied(self):
        from kairos.book import Book, Level
        from kairos.costs import CONSERVATIVE
        from kairos.crossvenue import round_trip_cost

        def leg(ask, bid):
            return Book(asks=(Level(ask, 100),), bids=(Level(bid, 100),))

        longshot = round_trip_cost(leg(0.02, 0.01), leg(0.96, 0.95),
                                   size=25, days_held=7.0, costs=CONSERVATIVE)
        self.assertFalse(CONSERVATIVE.price_in_band(longshot.yes_vwap),
                         "a caller cannot apply the exclusion it cannot see")

    def test_the_gate_d0_runner_applies_the_band_and_reports_the_disagreement(self):
        src = (ROOT / "gated.py").read_text(encoding="utf-8")
        self.assertIn("price_in_band", src, "gated.py renders a verdict without the exclusion")
        self.assertIn("THE TWO DISAGREE", src,
                      "gated.py must surface a banded/unbanded split rather than pick one")

    def test_the_scanners_that_do_not_enforce_it_are_still_the_ones_recorded(self):
        """Anti-drift in the awkward direction: enforcing it later is fine, *silently* is not.

        Pass 26 records that ``scanb.py`` and ``scanc.py`` measured their nulls without this
        exclusion. If a later session adds it, their recorded results no longer describe the code
        that produced them — so this fails and forces the record to be updated with the re-run.
        """
        for scanner in ("scanb.py", "scanc.py"):
            self.assertNotIn("price_in_band", (ROOT / scanner).read_text(encoding="utf-8"),
                             f"{scanner} now enforces the longshot band, but CORRECTIONS.md Pass "
                             f"26.1 still records that it does not - update the record and say "
                             f"whether the recorded null was re-measured")


class TestPass27ARateHurdleCannotMeasureAScaleConstraint(unittest.TestCase):
    """Pass 27. Gate 4.0's registered floor was cleared and the clearing meant nothing.

    The floor was "beat 6%/yr on capital locked" — an *existing* constant, chosen so it could not be
    a threshold invented to be clearable. Guarding a constant against being chosen is not the same as
    checking it is the right **dimension**. Throughput is dollars; the floor tested a rate.
    """

    def test_the_measured_strategy_clears_a_rate_floor_while_earning_ten_dollars(self):
        """The defect, in the numbers that produced it."""
        from kairos.economics import StrategyEconomics

        measured = StrategyEconomics(
            name="Class C convergence @ 25",
            edge_per_contract=0.00803,      # the one in-band opportunity, 2026-09-14
            fillable_contracts=25.0,
            opportunities_per_year=52.0,    # horizon-limited maximum at a 7-day hold
            capital_required=24.40,         # deployable capital across the whole universe
        )
        self.assertTrue(measured.worth_building(0.06 * 24.40),
                        "it does clear the registered rate floor")
        self.assertLess(measured.net_annual_value, 11.0,
                        "and a rate hurdle cannot see that this is ten dollars a year")

    def test_a_capacity_runner_reports_an_absolute_magnitude_not_only_a_rate(self):
        """A verdict about whether something is a business must be stated in dollars."""
        src = (ROOT / "gate4.py").read_text(encoding="utf-8").lower()
        self.assertIn("deployable capital", src,
                      "gate4.py must report the absolute capital the universe can absorb")
        self.assertIn("necessary, never sufficient", src,
                      "clearing the rate floor must be labelled insufficient wherever it is printed")

    def test_no_recurrence_rescues_a_non_positive_edge(self):
        """Infinity is an impossibility, not a large number, and must not render as one."""
        from kairos.economics import StrategyEconomics

        recorded_class_b = StrategyEconomics(
            name="Class B negRisk @ 25 (recorded)",
            edge_per_contract=-0.00597,     # SCANB-RESULTS.md, the *best* of 78 priced groups
            fillable_contracts=25.0,
            opportunities_per_year=4067.0,
            capital_required=25.0,
        )
        self.assertEqual(recorded_class_b.required_opportunities_for(1.50), float("inf"))
        self.assertLess(recorded_class_b.net_annual_value, 0.0)


class TestPass28ADecisionRuleMustStateItsWeighting(unittest.TestCase):
    """Pass 28. Three gates, three decision-rule defects, zero measurement defects.

    26.1 omitted a standing precondition, 27.1 tested a rate against a magnitude, 28.1 weighted
    markets when the hypothesis was about flow. Every apparatus worked; every error was in the
    sentence deciding what the number meant. The protocol's discipline is aimed almost entirely at
    the measurement and inspects none of this.
    """

    def test_an_unweighted_median_can_say_room_while_the_flow_says_stuck(self):
        """The defect as a property: it survives a rewrite of the specific statistic."""
        import gatem

        # Wide spreads in markets nobody trades; the flow is in one-tick markets. This is the
        # measured shape -- 37.2% of markets at one tick carrying 77.4% of the volume.
        rows = [
            (0.001, 0.001, 0.50, 1_000_000.0),   # 1 tick, enormous flow
            (0.001, 0.001, 0.50, 1_000_000.0),   # 1 tick, enormous flow
            (0.020, 0.001, 0.50, 1.0),           # 20 ticks, no flow
            (0.020, 0.001, 0.50, 1.0),           # 20 ticks, no flow
            (0.020, 0.001, 0.50, 1.0),           # 20 ticks, no flow
        ]
        ticks = sorted(s / t for s, t, _, _ in rows)
        self.assertGreater(ticks[len(ticks) // 2], 1.0,
                           "unweighted, the median market has room to quote")
        self.assertGreater(gatem.flow_share_at_one_tick(rows), 0.99,
                           "and essentially all of the money is where it does not")

    def test_the_runner_reports_the_flow_weighted_reading_beside_the_registered_one(self):
        src = (ROOT / "gatem.py").read_text(encoding="utf-8").lower()
        self.assertIn("share of flow", src,
                      "gatem.py must report the flow-weighted statistic, not only the median")

    def test_the_maker_capture_is_labelled_an_upper_bound_wherever_it_is_defined(self):
        """Adverse selection is the whole of maker P&L and is excluded. That must not go quiet."""
        from kairos.costs import CostModel

        doc = (CostModel.maker_capture.__doc__ or "").lower()
        self.assertIn("adverse selection", doc)
        self.assertIn("upper bound", doc)


class TestCorrectionsLogStaysExecutable(unittest.TestCase):
    """The meta-guard: this file must keep pace with the corrections log.

    Not a count check — a reminder with teeth. If a pass is added to CORRECTIONS.md and nothing here
    references it, the newest lesson is prose again, which is the condition that produced the G0.2
    recurrence in the first place.
    """

    def test_every_execution_pass_recorded_has_a_guard_or_a_stated_reason(self):
        log = (ROOT / "docs" / "CORRECTIONS.md").read_text(encoding="utf-8")
        passes = {ln.split("—")[0].strip().removeprefix("## ").strip()
                  for ln in log.splitlines() if ln.startswith("## Pass ")}
        here = (ROOT / "tests" / "test_regressions.py").read_text(encoding="utf-8")
        # Passes 1-3 are design corrections from contrarian review, not execution defects; they
        # have no runnable surface to guard. Passes 4+ are execution defects.
        execution = {p for p in passes if p.split()[-1].isdigit() and int(p.split()[-1]) >= 4}
        unguarded = {p for p in execution if p.replace(" ", "") not in here.replace(" ", "")}
        self.assertEqual(
            unguarded, set(),
            f"execution passes with no regression guard in this file: {sorted(unguarded)}. "
            f"Add a test encoding the property, or add the pass to the documented exemptions.",
        )


if __name__ == "__main__":
    unittest.main()
