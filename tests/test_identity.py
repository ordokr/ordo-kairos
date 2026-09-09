"""Tests for cross-venue event identity — the Gate C matcher and its null worlds.

The load-bearing tests here are the **kill-tests**: for each of the six pieces of evidence
``same_event`` compares, a matcher with that one comparison removed is built and shown to pair a
world it must refuse. A gate that passes is worth nothing unless a broken instrument would have
failed it (``docs/AXIOMS.md`` G7), and "every check is necessary, and this world is what makes it
necessary" is the strongest form of that available here.
"""

from __future__ import annotations

import unittest

from kairos.identity import (
    NULL_WORLDS,
    EventIdentity,
    ParsedIdentity,
    RawMarket,
    build_pair,
    parse_market,
    publish,
    same_event,
    same_event_naive,
    same_event_oracle,
    title_similarity,
)

SEED = 20260909
N = 200


def _pairs(world: str, n: int = N):
    return [build_pair(world, SEED + i * 131) for i in range(n)]


def _rate(world: str, matcher, n: int = N) -> float:
    return sum(matcher(p.left, p.right).paired for p in _pairs(world, n)) / n


def _compare(pa: ParsedIdentity, pb: ParsedIdentity, *, skip: str = "") -> bool:
    """``same_event``'s comparison with one check optionally removed. Used only by kill-tests."""
    if pa.missing or pb.missing:
        return False
    if skip != "resolution_date" and pa.instant[:10] != pb.instant[:10]:
        return False
    if skip != "settlement_time" and pa.instant[10:] != pb.instant[10:]:
        return False
    if skip != "threshold" and pa.threshold != pb.threshold:
        return False
    if skip != "source" and pa.source != pb.source:
        return False
    if skip != "scope" and pa.scope != pb.scope:
        return False
    if skip != "polarity" and pa.negated != pb.negated:
        return False
    if skip != "modality" and pa.modality != pb.modality:
        return False
    return True


def _matcher_without(field: str):
    def matcher(a: RawMarket, b: RawMarket):
        paired = _compare(parse_market(a), parse_market(b), skip=field)
        return type("V", (), {"paired": paired})()
    return matcher


#: Which null world exists to make which check necessary. This IS the gate's content.
NECESSITY = (
    ("resolution_date", "horizon_mismatch"),
    ("settlement_time", "settlement_time_mismatch"),
    ("threshold", "threshold_mismatch"),
    ("scope", "scope_mismatch"),
    ("source", "source_mismatch"),
    ("polarity", "negation_pair"),
    ("modality", "modality_mismatch"),
)


class TestPublicationAndExtraction(unittest.TestCase):
    """The matcher never sees an EventIdentity. It has to recover the evidence from text."""

    def test_the_two_venues_phrase_the_same_event_differently(self):
        ident = EventIdentity("Bitcoin", "closes above", 100000.0, "2026-12-31", "21:00",
                              "the primary spot index")
        titles = {publish(ident, v, seed=s).title for v in ("polymarket", "kalshi")
                  for s in range(6)}
        self.assertGreater(len(titles), 2, "publication must vary, or the parser is a template")

    def test_every_field_survives_the_round_trip_on_both_venues(self):
        ident = EventIdentity("Bitcoin", "closes above", 100000.0, "2026-12-31", "21:00",
                              "the primary spot index")
        for venue in ("polymarket", "kalshi"):
            for seed in range(6):
                parsed = parse_market(publish(ident, venue, seed=seed))
                with self.subTest(venue=venue, seed=seed):
                    self.assertEqual(parsed.missing, ())
                    self.assertEqual(parsed.threshold, 100000.0)
                    self.assertEqual(parsed.instant, "2026-12-31T21:00Z")
                    self.assertFalse(parsed.negated)
                    self.assertEqual(parsed.scope, frozenset({"bitcoin", "close", "above"}))

    def test_negation_is_recovered_and_does_not_disturb_the_scope(self):
        """Polarity is its own evidence. A negated title must yield the SAME scope tokens."""
        base = EventIdentity("Bitcoin", "closes above", 100000.0, "2026-12-31", "21:00",
                             "the primary spot index")
        neg = publish(base.__class__(*(*astuple_head(base), True)), "kalshi", seed=3)
        pos = publish(base, "kalshi", seed=3)
        self.assertTrue(parse_market(neg).negated)
        self.assertFalse(parse_market(pos).negated)
        self.assertEqual(parse_market(neg).scope, parse_market(pos).scope)

    def test_a_market_missing_its_evidence_fails_closed(self):
        """Unrecoverable evidence is a refusal, not an assumption of harmlessness (A6)."""
        blank = RawMarket("kalshi", "x", "", "", "")
        parsed = parse_market(blank)
        self.assertIn("settlement_instant", parsed.missing)
        self.assertIn("resolution_source", parsed.missing)
        verdict = same_event(blank, blank)
        self.assertFalse(verdict.paired)
        self.assertTrue(any(r.startswith("unrecoverable") for r in verdict.refusals))


class TestYearLikeStrikeRegression(unittest.TestCase):
    """Gate C's first run produced a FALSE PAIR, and this is it.

    ``_strip_dates`` matched ``\\b(?:19|20)\\d{2}\\b`` to remove years, which deleted any strike in
    1900-2099. Two markets quoted at 2000 and 2050 both parsed to *no strike*, agreed on every other
    field, and were declared the same event — the catastrophic case, produced by the date handling
    rather than by the comparison, in a gate that was reporting 0.000 on every null world.
    """

    #: Carries a determination instant in prose that agrees with ``close_iso`` (12:00 PM ET on
    #: 2027-03-31 is 16:00Z, EDT being in force), so these markets are fully evidenced and the test
    #: isolates the strike handling rather than tripping over Gate C2's modality check.
    RULES = ("Settles YES if gold closes above X on March 31, 2027 at 12:00 PM ET. "
             "Source: the primary spot index.")

    def _mkt(self, ident: str, title: str) -> RawMarket:
        return RawMarket("kalshi", ident, title, self.RULES, "2027-03-31T16:00:00Z")

    def test_two_different_year_like_strikes_are_not_the_same_event(self):
        a = self._mkt("A", "gold closes above 2000 - Mar 31, 2027")
        b = self._mkt("B", "gold closes above 2050 - Mar 31, 2027")
        verdict = same_event(a, b)
        self.assertFalse(verdict.paired, "2000 and 2050 are different strikes")
        self.assertIn("threshold_differs", verdict.refusals)

    def test_a_year_like_strike_still_parses(self):
        self.assertEqual(parse_market(self._mkt("A", "gold closes above 2000 - Mar 31, 2027"))
                         .threshold, 2000.0)

    def test_the_same_year_like_strike_still_pairs_across_venues(self):
        """The fix must not buy safety with power."""
        poly = RawMarket("polymarket", "P", "Will gold close above $2,000 on March 31, 2027?",
                         "This market resolves YES if gold closes above $2,000 on March 31, 2027 "
                         "at 12:00 PM ET. The resolution source is the primary spot index.",
                         "2027-03-31T16:00:00Z")
        self.assertTrue(same_event(poly, self._mkt("K", "gold closes above 2000 - Mar 31, 2027"))
                        .paired)

    def test_a_strike_equal_to_its_own_resolution_year_fails_closed(self):
        """The residual ambiguity costs power, never a false pair — and it refuses, not guesses."""
        a = self._mkt("A", "gold closes above 2027 - Mar 31, 2027")
        b = self._mkt("B", "gold closes above 2050 - Mar 31, 2027")
        verdict = same_event(a, b)
        self.assertFalse(verdict.paired)
        self.assertIn("threshold_presence_differs", verdict.refusals)


class TestNullWorlds(unittest.TestCase):
    def test_every_null_world_is_refused_for_its_own_reason(self):
        """Payload predicates, not booleans: a refusal for the wrong reason is a passing test
        sitting on top of a broken check."""
        expected = {
            "horizon_mismatch": "resolution_date_differs",
            "threshold_mismatch": "threshold_differs",
            "scope_mismatch": "scope_differs",
            "source_mismatch": "resolution_source_differs",
            "settlement_time_mismatch": "settlement_time_differs",
            "negation_pair": "polarity_differs",
            "modality_mismatch": "modality_differs",
        }
        for world, reason in expected.items():
            with self.subTest(world=world):
                verdicts = [same_event(p.left, p.right) for p in _pairs(world)]
                self.assertTrue(all(not v.paired for v in verdicts))
                self.assertTrue(all(reason in v.refusals for v in verdicts),
                                f"{world} must be refused by {reason}, not by something else")

    def test_the_control_is_paired(self):
        self.assertEqual(_rate("identical", same_event), 1.0)

    def test_random_pairing_is_refused(self):
        self.assertEqual(_rate("random_pairing", same_event), 0.0)

    def test_every_null_world_actually_contains_a_non_pair(self):
        """The validity precondition. A world whose pairs are secretly identical measures nothing."""
        for world, _ in NULL_WORLDS:
            with self.subTest(world=world):
                self.assertTrue(
                    all(not same_event_oracle(p.left_identity, p.right_identity).paired
                        for p in _pairs(world)),
                    f"{world} contains a genuinely identical pair; its FPR is uninterpretable",
                )

    def test_the_control_actually_contains_a_pair(self):
        self.assertTrue(all(same_event_oracle(p.left_identity, p.right_identity).paired
                            for p in _pairs("identical")))


class TestEveryCheckIsNecessary(unittest.TestCase):
    """The kill-tests. Remove one comparison and exactly one null world starts pairing."""

    def test_dropping_a_check_makes_its_world_pair(self):
        for field, world in NECESSITY:
            with self.subTest(dropped=field, world=world):
                broken = _rate(world, _matcher_without(field))
                self.assertGreater(broken, 0.5,
                                   f"dropping {field} should make {world} pair; if it does not, "
                                   f"{world} is being refused by some other check and proves "
                                   f"nothing about {field}")

    def test_keeping_every_check_refuses_every_world(self):
        for _, world in NECESSITY:
            with self.subTest(world=world):
                self.assertEqual(_rate(world, _matcher_without("")), 0.0)

    def test_a_date_only_comparison_would_pass_six_worlds_and_fail_the_seventh(self):
        """The settlement-time world is the discriminating null, and this is why.

        It agrees on all five pieces of evidence Gate C froze. Only comparing the settlement
        *instant* refuses it — which is how the registration's evidence list was found incomplete.
        """
        self.assertEqual(_rate("settlement_time_mismatch", same_event), 0.0)
        self.assertGreater(_rate("settlement_time_mismatch",
                                 _matcher_without("settlement_time")), 0.99)


class TestNaiveExhibit(unittest.TestCase):
    """Title similarity is not weak evidence here. For two worlds it is provably no evidence."""

    def test_two_null_worlds_are_invisible_in_the_title(self):
        control = [title_similarity(p.left, p.right) for p in _pairs("identical")]
        for world in ("source_mismatch", "settlement_time_mismatch"):
            with self.subTest(world=world):
                sims = [title_similarity(p.left, p.right) for p in _pairs(world)]
                self.assertEqual(sims, control,
                                 f"{world} must be title-identical to a true pair: the evidence "
                                 f"lives in the rules text and the timestamp, not the title")

    def test_no_similarity_threshold_separates_true_pairs_from_near_misses(self):
        control = [title_similarity(p.left, p.right) for p in _pairs("identical")]
        worlds = {w: [title_similarity(p.left, p.right) for p in _pairs(w)]
                  for w, _ in NULL_WORLDS}
        best = max(
            sum(s >= t for s in control) / len(control)
            - max(sum(s >= t for s in sims) / len(sims) for sims in worlds.values())
            for t in (0.40 + 0.01 * i for i in range(60))
        )
        self.assertLessEqual(best, 0.0,
                             "if a similarity cut ever separates them, the exhibit's claim in "
                             "gatec.py is overstated and must be corrected, not left standing")

    def test_the_exhibit_pairs_what_the_matcher_refuses(self):
        self.assertGreater(_rate("source_mismatch",
                                 lambda a, b: same_event_naive(a, b, threshold=0.70)), 0.9)
        self.assertEqual(_rate("source_mismatch", same_event), 0.0)


class TestProseInstantExtractor(unittest.TestCase):
    """Gate C2. The determination instant lives in prose on one venue and as data on the other."""

    def test_a_deadline_and_an_instant_are_told_apart(self):
        from kairos.identity import extract_prose_instant

        self.assertEqual(extract_prose_instant("... by December 31, 2026, 11:59 PM ET."),
                         ("2027-01-01T04:59Z", "deadline"))
        self.assertEqual(extract_prose_instant("... on Dec 31, 2026 at 12 PM ET."),
                         ("2026-12-31T17:00Z", "instant"))

    def test_the_real_somaliland_market_reconstructs_its_own_close_timestamp(self):
        """The measurement's blocker, on the actual market that exposed it.

        Polymarket's prose says "by December 31, 2026, 11:59 PM ET" and its ``endDate`` is
        ``2027-01-01T04:59Z``. Two independent published sources, the same instant.
        """
        from kairos.identity import extract_prose_instant

        instant, modality = extract_prose_instant(
            "This market will resolve to \"Yes\" if the United States formally recognizes the "
            "Republic of Somaliland as a sovereign state by December 31, 2026, 11:59 PM ET.")
        self.assertEqual(instant, "2027-01-01T04:59Z")
        self.assertEqual(modality, "deadline")

    def test_daylight_saving_is_computed_not_assumed(self):
        """A fixed -5 offset is wrong for eight months of the year, and an hour is enough to make
        a 12pm market look like a 1pm one."""
        from kairos.identity import extract_prose_instant

        winter, _ = extract_prose_instant("... on January 15, 2027 at 12:00 PM ET.")
        summer, _ = extract_prose_instant("... on July 15, 2027 at 12:00 PM ET.")
        self.assertEqual(winter, "2027-01-15T17:00Z")   # EST, UTC-5
        self.assertEqual(summer, "2027-07-15T16:00Z")   # EDT, UTC-4

    def test_the_two_ambiguous_hours_a_year_are_refused_not_guessed(self):
        from kairos.identity import extract_prose_instant

        # 2:30 AM on the spring-forward Sunday never happens; 1:30 AM on the fall-back Sunday
        # happens twice. Either would be an hour out if resolved by picking one.
        self.assertEqual(extract_prose_instant("... on March 14, 2027 at 2:30 AM ET."), (None, None))
        self.assertEqual(extract_prose_instant("... on November 7, 2027 at 1:30 AM ET."),
                         (None, None))

    def test_an_unrecognised_timezone_is_refused_rather_than_assumed_utc(self):
        from kairos.identity import extract_prose_instant

        self.assertEqual(extract_prose_instant("... by December 31, 2026, 11:59 PM CET."),
                         (None, None))

    def test_a_contradiction_between_prose_and_timestamp_is_unrecoverable(self):
        market = RawMarket("polymarket", "x", "Will gold close above $2,000 on March 31, 2027?",
                           "Resolves YES on March 31, 2027 at 12:00 PM ET. Source: the index.",
                           "2027-03-31T20:00:00Z")
        parsed = parse_market(market)
        self.assertIn("settlement_time", parsed.missing)
        self.assertFalse(parsed.instant_confirmed)


def astuple_head(ident: EventIdentity):
    """The identity's fields except ``negated`` — used to build its negated twin in one line."""
    return (ident.subject, ident.claim, ident.threshold, ident.resolution_date,
            ident.settlement_time, ident.source)


if __name__ == "__main__":
    unittest.main()
