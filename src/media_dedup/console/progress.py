"""Rich progress bars implementing the scan's `ProgressSink` contract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, override

from rich.padding import Padding
from rich.progress import Progress, ProgressColumn, TaskID
from rich.text import Text

from media_dedup.console.progress_columns import step_columns

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rich.console import Console, RenderableType

    from media_dedup.scan.progress import Step

_HINT_STYLE = "dim"
# Aligns the explanation with the step title, after the spinner and its padding.
_HINT_INDENT = (0, 0, 0, 2)


class RichProgress:
    """One transient bar per step; nothing is drawn without a terminal.

    The spinner keeps turning even while a single slow file is processed, so a long
    step never looks frozen. Use it as a context manager: the bar is removed and the
    cursor shown again even when the step is interrupted (Ctrl+C).
    """

    def __init__(self, console: Console) -> None:
        """Bind the bars to a console.

        Args:
            console: Where to draw.
        """
        self._console = console
        self._progress: Progress | None = None
        self._task: TaskID | None = None

    def __enter__(self) -> Self:
        """Enter the lifetime of the bars.

        Returns:
            This progress sink.
        """
        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Remove the current bar, whatever ended its step."""
        self.stop()

    def start(self, step: Step, total: int | None) -> None:
        """Show a new bar, with what the step really does below it.

        The bar is a running count when the total is unknown.

        Args:
            step: Translated title and explanation of the step.
            total: Number of units of work, or None when unknown in advance.
        """
        self.stop()
        if total == 0 or not self._console.is_terminal:
            return
        self._progress = HintedProgress(
            *step_columns(counting=total is None),
            console=self._console,
            hint=step.hint,
        )
        self._progress.start()
        self._task = self._progress.add_task(step.title, total=total)

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


class HintedProgress(Progress):
    """A transient progress display with a dim, one-line explanation below the bar."""

    def __init__(self, *columns: ProgressColumn, console: Console, hint: str) -> None:
        """Create the display.

        Args:
            *columns: The columns of the bar.
            console: Where to draw.
            hint: What the step really does; nothing is drawn when empty.
        """
        # Set before `Progress.__init__`, which already renders the display.
        self._hint = Padding(Text(hint, style=_HINT_STYLE), _HINT_INDENT)
        self._has_hint = bool(hint)
        super().__init__(*columns, console=console, transient=True)

    @override
    def get_renderables(self) -> Iterable[RenderableType]:
        """Yield the bars, then the explanation.

        Yields:
            What to draw.
        """
        yield self.make_tasks_table(self.tasks)
        if self._has_hint:
            yield self._hint
