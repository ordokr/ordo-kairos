"""Instrument validity: may this run announce a verdict at all?

This module exists because one defect was committed **twice, five passes apart**, in the same repo,
with the fix written down in between.

``docs/CORRECTIONS.md`` Pass 4 (G0.2) recorded it: Gate 0's power comparison was meaningless because
the *oracle* — a forecaster built from the world's own parameters, therefore unbeatable — was also
undetected at that sample size. The ceiling was zero, so the pipeline's zero said nothing about the
pipeline. The fix landed as ``GateReport.harness_valid``, a property of one class.

Pass 9 then wrote a new runner, ``gate0b.py``, which computed its own ceilings and announced
**"DEAD"** with every ceiling below the power floor. Same defect. The correction had been recorded
in prose and the fix had been implemented in a place a new runner could not inherit
(``docs/AXIOMS.md`` G3, G8).

So the rule lives here, once, callable, and tested — including against the two shapes that actually
occurred: no unit valid, and one broken unit hiding behind a healthy one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

__all__ = ["UnitValidity", "ValidityReport", "assess"]


@dataclass(frozen=True)
class UnitValidity:
    """One experimental unit — a world, a stratum, a market slice — and its detection ceiling."""

    name: str
    ceiling: float
    floor: float

    @property
    def usable(self) -> bool:
        """Whether anything measured in this unit can rank two instruments against each other."""
        return self.ceiling >= self.floor

    def explain(self) -> str:
        verdict = "usable" if self.usable else "CANNOT RANK"
        return f"{self.name}: ceiling {self.ceiling:.3f} vs floor {self.floor:.3f} - {verdict}"


@dataclass(frozen=True)
class ValidityReport:
    units: tuple[UnitValidity, ...]
    floor: float

    @property
    def usable(self) -> tuple[UnitValidity, ...]:
        return tuple(u for u in self.units if u.usable)

    @property
    def excluded(self) -> tuple[UnitValidity, ...]:
        return tuple(u for u in self.units if not u.usable)

    @property
    def may_conclude(self) -> bool:
        """False when no unit could have detected anything, whatever the instruments scored."""
        return bool(self.usable)

    def refusal(self) -> str:
        """The message to print *instead of* a verdict. Empty when a verdict is permitted."""
        if self.may_conclude:
            return ""
        best = max((u.ceiling for u in self.units), default=0.0)
        return (
            f"NO VERDICT. Every unit's ceiling is below the {self.floor} floor (best {best:.3f}): "
            f"the best result obtainable was itself mostly undetected, so these units cannot rank "
            f"the instruments. This is a statement about the UNITS, not about what was tested. "
            f"Strengthen the signal or enlarge the sample and re-run; do not read the ordering as "
            f"evidence either way."
        )

    def explain(self) -> str:
        lines = [u.explain() for u in self.units]
        if self.excluded and self.may_conclude:
            names = ", ".join(u.name for u in self.excluded)
            lines.append(
                f"EXCLUDED from the comparison: {names} - nothing could succeed there, so they "
                f"cannot rank instruments. Judging on the BEST ceiling instead of per unit is how "
                f"a dead unit hides behind a healthy one (AXIOMS G4)."
            )
        return "\n".join(lines)


def assess(ceilings: Mapping[str, float] | Sequence[tuple[str, float]], floor: float
           ) -> ValidityReport:
    """Build a :class:`ValidityReport` from per-unit ceilings.

    ``ceilings`` maps a unit name to the detection rate of the **best result obtainable** in it —
    an oracle, an achievable upper bound, whatever ceiling the experiment defines. ``floor`` is the
    power floor below which a unit cannot discriminate.

    **Per unit, never in aggregate.** ``gate0b.py`` first guarded on the maximum ceiling across
    worlds, which let ``banded:lowmid`` (ceiling 0.062, nothing detectable) contribute its ordering
    to a verdict because ``banded:highmid`` (1.000) was healthy.
    """
    items = ceilings.items() if isinstance(ceilings, Mapping) else ceilings
    return ValidityReport(
        units=tuple(UnitValidity(str(n), float(c), floor) for n, c in items),
        floor=floor,
    )
