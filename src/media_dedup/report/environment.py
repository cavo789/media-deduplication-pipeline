"""The Jinja environment of the reports: autoescaped, translated, formatting filters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.console.formatting import human_number, human_size
from media_dedup.i18n.templates import translated_environment

if TYPE_CHECKING:
    from jinja2 import Environment

_TEMPLATES_PACKAGE = "media_dedup.report"


def make_environment() -> Environment:
    """Create the environment; `_()` in templates uses the active language.

    Returns:
        The Jinja environment.
    """
    environment = translated_environment(_TEMPLATES_PACKAGE, escaped=("html", "j2"))
    environment.filters["size"] = human_size
    environment.filters["number"] = human_number
    return environment
