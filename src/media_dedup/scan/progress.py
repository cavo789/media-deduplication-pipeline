"""The progress contract the scan reports to, decoupled from Rich."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Step:
    """A long step as the user sees it: a short title and what it really does."""

    title: str
    hint: str = ""


class ProgressSink(Protocol):
    """Receives progress updates of a long step."""

    def start(self, step: Step, total: int | None) -> None:
        """Begin a step.

        Args:
            step: Translated title and explanation of the step.
            total: Number of units of work, or None when unknown in advance (the
                step then shows a running count instead of a bar).
        """

    def advance(self) -> None:
        """Mark one unit of work as done."""

    def stop(self) -> None:
        """End the current step."""


class NullProgress:
    """A progress sink that shows nothing (tests, non-interactive runs)."""

    def start(self, step: Step, total: int | None) -> None:
        """Ignore the start of a step.

        Args:
            step: Unused.
            total: Unused.
        """

    def advance(self) -> None:
        """Ignore progress."""

    def stop(self) -> None:
        """Ignore the end of a step."""
