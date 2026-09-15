"""Where runtime state is allowed to live.

Every repository under ``C:/src`` is publish-eligible (``C:/src/CLAUDE.md`` rule 1): visibility is a
one-click change and history does not follow it back. Positions, PnL, API keys, and account
identifiers must therefore never be written inside this tree.

That rule is enforced here in code rather than left to a comment, because a comment does not fail a
build. :func:`state_dir` refuses to hand back a path inside the workspace, so the ledger and any
future runtime artifact cannot be written somewhere that a later ``git init`` would sweep up.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["StateLocationError", "WORKSPACE_ROOT", "STATE_ENV_VAR", "state_dir", "is_inside"]

STATE_ENV_VAR = "ORDO_KAIROS_STATE"

#: The publish-eligible tree that runtime state must stay out of.
WORKSPACE_ROOT = Path("C:/src")


class StateLocationError(RuntimeError):
    """Raised when runtime state would land somewhere publish-eligible."""


def is_inside(candidate: Path, parent: Path) -> bool:
    """Whether ``candidate`` resolves to ``parent`` or somewhere beneath it."""
    try:
        candidate.resolve().relative_to(parent.resolve())
    except (ValueError, OSError):
        return False
    return True


def state_dir(create: bool = True) -> Path:
    """Resolve the runtime state directory, or refuse.

    Reads ``$ORDO_KAIROS_STATE``. Raises :class:`StateLocationError` if it is unset or if it
    resolves inside :data:`WORKSPACE_ROOT`.

    The refusal is deliberate: defaulting to a path inside the repo would be convenient and would
    be exactly the failure this module exists to prevent.
    """
    raw = os.environ.get(STATE_ENV_VAR, "").strip()
    if not raw:
        raise StateLocationError(
            f"{STATE_ENV_VAR} is not set. Point it at a directory outside {WORKSPACE_ROOT} - "
            f"positions, PnL and credentials must not be written into a publish-eligible repo."
        )
    path = Path(raw).expanduser()
    if is_inside(path, WORKSPACE_ROOT):
        raise StateLocationError(
            f"{STATE_ENV_VAR}={path} resolves inside {WORKSPACE_ROOT}, which is publish-eligible. "
            f"Choose a location outside the workspace."
        )
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
