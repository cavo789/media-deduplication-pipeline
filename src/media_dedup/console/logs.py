"""Route the standard `logging` module to Rich, at the configured verbosity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.logging import RichHandler

from media_dedup.constants import Verbosity

if TYPE_CHECKING:
    from rich.console import Console

_LEVELS = {
    Verbosity.ERROR: logging.ERROR,
    Verbosity.WARNING: logging.WARNING,
    Verbosity.INFO: logging.INFO,
    Verbosity.DEBUG: logging.DEBUG,
}


def configure_logging(verbosity: Verbosity, console: Console) -> None:
    """Send every log record to `console`, filtered by `verbosity`.

    Args:
        verbosity: Minimum level to show.
        console: Rich console to write to.
    """
    handler = RichHandler(
        console=console,
        show_path=verbosity is Verbosity.DEBUG,
        markup=False,
        rich_tracebacks=True,
    )
    logging.basicConfig(
        level=_LEVELS[verbosity],
        format="%(message)s",
        handlers=[handler],
        force=True,
    )
