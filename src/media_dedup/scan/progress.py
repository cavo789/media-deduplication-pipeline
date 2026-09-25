"""The progress contract the scan reports to, decoupled from Rich."""

from __future__ import annotations

from typing import Protocol


class ProgressSink(Protocol):
    """Receives progress updates of a long step."""

    def start(self, label: str, total: int) -> None:
        """Begin a step.

        Args:
            label: Translated step description.
            total: Number of units of work.
        """

    def advance(self) -> None:
        """Mark one unit of work as done."""

    def stop(self) -> None:
        """End the current step."""


class NullProgress:
    """A progress sink that shows nothing (tests, non-interactive runs)."""

    def start(self, label: str, total: int) -> None:
        """Ignore the start of a step.

        Args:
            label: Unused.
            total: Unused.
        """

    def advance(self) -> None:
        """Ignore progress."""

    def stop(self) -> None:
        """Ignore the end of a step."""
