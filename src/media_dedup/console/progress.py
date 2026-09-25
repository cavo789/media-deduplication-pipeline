"""Rich progress bars implementing the scan's `ProgressSink` contract."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)

if TYPE_CHECKING:
    from rich.console import Console


class RichProgress:
    """One transient bar per step; nothing is drawn without a terminal or work to do."""

    def __init__(self, console: Console) -> None:
        """Bind the bars to a console.

        Args:
            console: Where to draw.
        """
        self._console = console
        self._progress: Progress | None = None
        self._task: TaskID | None = None

    def start(self, label: str, total: int) -> None:
        """Show a new bar.

        Args:
            label: Translated step description.
            total: Number of units of work.
        """
        self.stop()
        if total <= 0 or not self._console.is_terminal:
            return
        self._progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=self._console,
            transient=True,
        )
        self._progress.start()
        self._task = self._progress.add_task(label, total=total)

    def advance(self) -> None:
        """Advance the current bar by one unit."""
        if self._progress is not None and self._task is not None:
            self._progress.advance(self._task)

    def stop(self) -> None:
        """Remove the current bar."""
        if self._progress is not None:
            self._progress.stop()
        self._progress = None
        self._task = None
