"""Rich progress bars: a bar for known totals, a running count otherwise."""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from media_dedup.console.progress import RichProgress
from media_dedup.constants import Locale
from media_dedup.i18n import install
from media_dedup.scan.progress import Step


def drawn(total: int | None, *, is_terminal: bool = True) -> str:
    """Run one step of one unit and return what was written to the console."""
    buffer = io.StringIO()
    progress = RichProgress(Console(file=buffer, force_terminal=is_terminal))
    progress.start(Step("Working", "What it does"), total)
    progress.advance()
    progress.stop()
    return buffer.getvalue()


@pytest.mark.parametrize("total", [3, None])
def test_steps_are_drawn(total: int | None) -> None:
    """Known and unknown totals both draw the step."""
    output = drawn(total)
    assert "Working" in output
    assert "What it does" in output
    assert "elapsed 0:00:00" in output
    assert ("left" in output) is (total is not None)


def test_nothing_is_drawn_for_empty_steps_or_without_terminal() -> None:
    """A step without work, or a console that is not a terminal, stays silent."""
    assert not drawn(0)
    assert not drawn(5, is_terminal=False)


def test_counts_keep_the_language_of_their_creation() -> None:
    """Counts use the separators of the language active when the bar was created."""
    install(Locale.FR)
    buffer = io.StringIO()
    progress = RichProgress(Console(file=buffer, force_terminal=True, width=120))
    progress.start(Step("Working"), 12345)
    for _step in range(1234):
        progress.advance()
    progress.stop()
    assert "1.234/12.345" in buffer.getvalue()
