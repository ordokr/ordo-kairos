"""The safety boundary, tested by trying to violate it.

``C:/src/CLAUDE.md`` rule 1: every repo in this workspace is publish-eligible, so positions, PnL and
credentials must never be written here. A comment cannot enforce that. These tests confirm the
enforcement actually refuses, because an unenforced guard is worse than none - it invites trust.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kairos.state import (
    STATE_ENV_VAR,
    WORKSPACE_ROOT,
    StateLocationError,
    is_inside,
    state_dir,
)


class TestStateLocationGuard(unittest.TestCase):
    def test_unset_env_var_refuses_rather_than_defaulting(self):
        """A convenient default inside the repo is exactly the bug this prevents."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(StateLocationError) as ctx:
                state_dir()
        self.assertIn(STATE_ENV_VAR, str(ctx.exception))

    def test_blank_env_var_refuses(self):
        with mock.patch.dict(os.environ, {STATE_ENV_VAR: "   "}):
            with self.assertRaises(StateLocationError):
                state_dir()

    def test_a_path_inside_the_workspace_is_refused(self):
        for candidate in (
            str(WORKSPACE_ROOT / "ordo-kairos" / "state"),
            str(WORKSPACE_ROOT / "state"),
            str(WORKSPACE_ROOT),
        ):
            with self.subTest(candidate=candidate):
                with mock.patch.dict(os.environ, {STATE_ENV_VAR: candidate}):
                    with self.assertRaises(StateLocationError) as ctx:
                        state_dir(create=False)
                self.assertIn("publish-eligible", str(ctx.exception))

    def test_a_path_outside_the_workspace_is_accepted_and_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "kairos-state"
            with mock.patch.dict(os.environ, {STATE_ENV_VAR: str(target)}):
                resolved = state_dir()
            self.assertTrue(resolved.exists())
            self.assertFalse(is_inside(resolved, WORKSPACE_ROOT))

    def test_is_inside_does_not_match_sibling_prefixes(self):
        """`C:/src-scratch` is not inside `C:/src`, despite the string prefix."""
        self.assertFalse(is_inside(Path("C:/src-scratch/x"), WORKSPACE_ROOT))
        self.assertTrue(is_inside(Path("C:/src/x"), WORKSPACE_ROOT))


if __name__ == "__main__":
    unittest.main()
