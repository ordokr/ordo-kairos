"""Falsifiers against the README's own claims.

The README is the artifact that travels, and it is the one document in this repository that was
never gated. Every other claim here had to survive a registration, a null world and a decision rule;
the front page asserted eleven results, six counts and a methodological virtue on nothing but the
author's word.

So it gets the same treatment. Each test below takes a claim the README makes about *itself* and
tries to break it against the tree, the git history, or the test suite. The interesting one is
:class:`TestRegistrationPrecedesImplementation` -- the claim that carries all the credibility, and
the one the artifact can only partly support.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=120).stdout.strip()


class TestCountsAreTrue(unittest.TestCase):
    """Every count the README prints must match what is actually on disk."""

    def test_the_corrections_pass_count_is_exact(self):
        claimed = int(re.search(r"(\d+) passes of recorded defects", README).group(1))
        actual = len(re.findall(r"^## Pass ", (ROOT / "docs" / "CORRECTIONS.md")
                                .read_text(encoding="utf-8"), re.M))
        self.assertEqual(claimed, actual)

    def test_the_results_document_count_is_exact(self):
        claimed = int(re.search(r"one per gate, (\d+) of them", README).group(1))
        self.assertEqual(claimed, len(list((ROOT / "docs").glob("*RESULTS*.md"))))

    def test_the_hypothesis_class_count_matches_the_results_table(self):
        claimed = re.search(r"\*\*(\w+) separate hypothesis classes\*\*", README).group(1)
        self.assertEqual(claimed.lower(), "eleven")
        # One row per class in the answer table, between its header and the next heading.
        table = README.split("## The answer")[1].split("**The two constraints")[0]
        rows = [ln for ln in table.splitlines() if ln.startswith("| **")]
        self.assertEqual(len(rows), 11, f"table has {len(rows)} rows, README claims eleven")

    def test_the_test_count_is_not_overstated(self):
        """Counted statically by AST.

        The first version of this test shelled out to `unittest discover`, which rediscovers this
        file and re-runs the suite inside itself -- unbounded recursion that hung for ten minutes
        before it was killed. A test that runs the test suite is not a test.
        """
        claimed = int(re.search(r"(\d+) tests, including the corrections meta-guard",
                                README).group(1))
        actual = 0
        for path in (ROOT / "tests").glob("test_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                    actual += 1
        self.assertGreaterEqual(actual, claimed,
                                f"README claims {claimed} tests, {actual} test methods defined")


class TestNothingEverTraded(unittest.TestCase):
    """F3, and the README's strongest promise: 'It never placed an order.'

    A single POST, a signing routine or a credential would falsify the whole document.
    """

    FORBIDDEN = (r'method\s*=\s*["\']POST', r"\.post\(", r"private_key", r"PRIVATE_KEY",
                 r"api_secret", r"eth_account", r"place_order", r"cancel_order", r"sign_typed")

    def test_no_order_placement_or_credential_handling_anywhere(self):
        offenders = []
        for py in list(ROOT.glob("*.py")) + list((ROOT / "kairos").glob("*.py")):
            src = py.read_text(encoding="utf-8")
            for pat in self.FORBIDDEN:
                if re.search(pat, src):
                    offenders.append(f"{py.name}: {pat}")
        self.assertEqual(offenders, [], f"the repository claims it never traded: {offenders}")

    def test_the_only_http_verb_is_a_plain_get(self):
        """urllib defaults to GET; a Request carrying data= would silently become a POST."""
        for py in list(ROOT.glob("*.py")) + list((ROOT / "kairos").glob("*.py")):
            src = py.read_text(encoding="utf-8")
            self.assertNotIn("urlopen(req, data", src)
            self.assertNotRegex(src, r"Request\([^)]*\bdata\s*=")


class TestZeroDependencies(unittest.TestCase):
    """'Zero third-party dependencies -- standard library only.'"""

    LOCAL = {"kairos", "gatem", "gate1", "gate3", "gated", "scanc", "inside", "gatesm", "gaten"}

    def test_every_import_is_stdlib_or_local(self):
        foreign = set()
        for py in list(ROOT.glob("*.py")) + list((ROOT / "kairos").glob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [(node.module or "").split(".")[0]] if node.level == 0 else []
                else:
                    continue
                for n in names:
                    if n and n not in self.LOCAL and n not in sys.stdlib_module_names:
                        foreign.add(f"{py.name}: {n}")
        self.assertEqual(foreign, set(), f"third-party imports found: {sorted(foreign)}")

    def test_no_dependency_manifest_contradicts_the_claim(self):
        for name in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile"):
            self.assertFalse((ROOT / name).exists(), f"{name} exists; the claim needs revisiting")


class TestRegistrationPrecedesImplementation(unittest.TestCase):
    """**The claim that carries all the credibility, and the one the artifact partly supports.**

    The README asserts every gate was registered before it was built. That is true of how the work
    was done and verifiable from git for two gates -- Class C and Class S, whose registration commit
    lands before the commit adding their runner.

    ``main`` is a single squashed commit and cannot carry that proof. The proof lives on the
    ``provenance/pre-squash`` tag, which preserves the 21-commit development history and is fetched
    by a default ``git clone``. Reachability from ``main`` was never what made the evidence
    evidence; the objects are (Pass 41). This test therefore reads the tag, not ``HEAD``.

    It asserts **equality**, not a floor: a ``>=`` assertion against a small constant is weak, and
    an unfalsifiable test inside a suite whose subject is falsifiability is worse than no test at
    all (Pass 40.3). As an equality it has teeth in both directions -- a future gate landing its
    registration in its own commit breaks this test until ``PROVABLE`` and the README are updated
    to claim the credit, and a lost or moved tag breaks it too.
    """

    #: The ref carrying the development history. ``main`` is squashed; this is the record.
    PROVENANCE = "provenance/pre-squash"

    #: Gates whose registration commit provably precedes the commit adding their runner.
    PROVABLE = 2
    TOTAL = 8

    def test_the_readme_discloses_that_the_claim_is_only_partly_provable(self):
        self.assertIn("2 of 8 gates can prove it from the artifact", README,
                      "the limit of the pre-registration claim must stay disclosed")
        self.assertIn("back-filled", README.lower())
        self.assertIn("squash", README.lower(),
                      "the README must say why main cannot carry the proof")
        self.assertIn(self.PROVENANCE, README,
                      "the README must name the ref a reader can verify against")

    def test_the_provable_ratio_has_not_got_worse(self):
        runners = {"gates.py": "Class S", "gated.py": "Class C", "gatem2.py": "Class M2",
                   "gatef.py": "Class F", "gater.py": "Class R", "gatek.py": "Class K",
                   "gatesm.py": "Class SM", "gaten.py": "Class N"}
        # main is squashed; the development history lives on the provenance tag. A default
        # `git clone` fetches it. If it is missing the claim is unverifiable and this must fail
        # loudly rather than silently reporting zero.
        self.assertTrue(
            _git("rev-parse", "--verify", "--quiet", self.PROVENANCE + "^{commit}"),
            f"{self.PROVENANCE} not found. The pre-registration proof lives on that tag, not on "
            f"main. Fetch it with: git fetch origin refs/tags/{self.PROVENANCE}",
        )
        provable = 0
        for runner in runners:
            added = _git("log", self.PROVENANCE, "--diff-filter=A",
                         "--format=%H", "--", runner).split("\n")[-1]
            if not added:
                continue
            # The commit that first introduced this class's registration heading.
            reg = _git("log", self.PROVENANCE, "--format=%H", "-S", runners[runner] + " —",
                       "--", "docs/PROTOCOL.md").split("\n")
            reg = [c for c in reg if c]
            if reg and reg[-1] != added:
                provable += 1
        self.assertEqual(
            provable, self.PROVABLE,
            f"{provable} of {self.TOTAL} gates have registration in an earlier commit than their "
            f"runner; the README discloses {self.PROVABLE}. If this fell, the disclosure is now "
            f"wrong. If it rose, raise PROVABLE and update the README to match. This is an "
            f"equality and not a floor on purpose: '>= 0' cannot fail, and an unfalsifiable test "
            f"in a suite about falsifiability is worse than no test (Pass 40.3).",
        )

    def test_expectations_were_recorded_and_sometimes_contradicted(self):
        """The check a back-filled registration cannot pass: predictions that turned out wrong."""
        protocol = (ROOT / "docs" / "PROTOCOL.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(protocol.count("Pre-committed expectation"), 5)
        corrections = (ROOT / "docs" / "CORRECTIONS.md").read_text(encoding="utf-8").lower()
        self.assertIn("directionally wrong", corrections,
                      "registrations that never fail their own predictions are not evidence")


class TestHeadlineFiguresTraceToEvidence(unittest.TestCase):
    """Every number on the front page must appear in a results document or the protocol."""

    FIGURES = ("3.9%", "96.1%", "77.4%", "73.4%", "0.11%", "$10.47", "+2.85%",
               "94.5%", "$139,450", "26.6%", "22.6%", "+4.71%", "3.25%", "1,966")

    def test_no_headline_figure_is_unsourced(self):
        corpus = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "docs").glob("*.md"))
        missing = [f for f in self.FIGURES if f in README and f not in corpus]
        self.assertEqual(missing, [], f"figures on the front page with no source in docs/: {missing}")

    def test_the_verdict_is_stated_as_a_bounded_claim_not_a_universal_one(self):
        """AXIOMS G12/A1: an instrument's ceiling is not the world's floor."""
        self.assertIn("not** a claim that no edge exists", README)
        self.assertIn("on the venues and dates measured", README)


class TestLicenceIsDeclared(unittest.TestCase):
    """A repository whose stated value is 'figures worth stealing' must permit the stealing."""

    def test_a_licence_file_exists_and_the_readme_names_it(self):
        licence = ROOT / "LICENSE"
        self.assertTrue(licence.exists(), "no LICENSE: default copyright forbids all reuse")
        self.assertIn("Apache License", licence.read_text(encoding="utf-8"))
        self.assertRegex(README, r"Apache[- ]2\.0")


if __name__ == "__main__":
    unittest.main()
