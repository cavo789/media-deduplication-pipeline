"""The columns of a progress bar: a localised count and explicitly labelled times.

Rich renders from its own refresh thread, where the active language is unknown: every
column captures its translations and locale when it is created.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from rich.progress import BarColumn, ProgressColumn, SpinnerColumn, TextColumn
from rich.table import Column
from rich.text import Text

from media_dedup.console.formatting import human_number
from media_dedup.i18n import _, active_locale

if TYPE_CHECKING:
    from rich.progress import Task

_COUNT_STYLE = "progress.download"
_ELAPSED_STYLE = "progress.elapsed"
_REMAINING_STYLE = "progress.remaining"
_UNKNOWN_TIME = "…"


def step_columns(*, counting: bool) -> tuple[ProgressColumn, ...]:
    """Pick the columns of a step.

    Args:
        counting: The total is unknown: show a running count instead of a bar.

    Returns:
        The Rich columns to draw.
    """
    head = (SpinnerColumn(), TextColumn("[bold blue]{task.description}"))
    if counting:
        return (*head, CountColumn(), TimesColumn())
    return (*head, BarColumn(), CountColumn(), TimesColumn())


class CountColumn(ProgressColumn):
    """`9,150/67,947` (or `9.150/67.947` in French); the count alone without a total."""

    def __init__(self) -> None:
        """Capture the language now."""
        super().__init__(table_column=Column(no_wrap=True))
        self._locale = active_locale()

    @override
    def render(self, task: Task) -> Text:
        """Render the progress of a task.

        Args:
            task: The task to render.

        Returns:
            The completed count, followed by the total when known.
        """
        done = human_number(task.completed, locale=self._locale)
        if task.total is None:
            return Text(done, style=_COUNT_STYLE)
        total = human_number(task.total, locale=self._locale)
        return Text(f"{done}/{total}", style=_COUNT_STYLE)


class TimesColumn(ProgressColumn):
    """`elapsed 0:00:47 · about 0:02:19 left`: the times of this step, labelled."""

    def __init__(self) -> None:
        """Capture the translated labels now."""
        super().__init__(table_column=Column(no_wrap=True))
        self._elapsed = _("elapsed {time}")
        self._remaining = _("about {time} left")

    @override
    def render(self, task: Task) -> Text:
        """Render the elapsed time of the step and, with a known total, its estimate.

        Args:
            task: The task to render.

        Returns:
            The labelled times.
        """
        elapsed = task.finished_time if task.finished else task.elapsed
        text = Text(self._elapsed.format(time=_clock(elapsed)), style=_ELAPSED_STYLE)
        if task.total is not None:
            remaining = _clock(task.time_remaining)
            text.append(" · ")
            text.append(self._remaining.format(time=remaining), style=_REMAINING_STYLE)
        return text


def _clock(seconds: float | None) -> str:
    """Render a duration as `h:mm:ss`.

    Args:
        seconds: The duration, or None when not known yet.

    Returns:
        The clock, or an ellipsis while unknown.
    """
    if seconds is None:
        return _UNKNOWN_TIME
    return str(timedelta(seconds=int(seconds)))
