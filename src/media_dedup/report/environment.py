"""The Jinja environment of the reports: autoescaped, translated, with size filters."""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from media_dedup.console.formatting import human_size
from media_dedup.i18n import active

_TEMPLATES_PACKAGE = "media_dedup.report"


def make_environment() -> Environment:
    """Create the environment; `_()` in templates uses the active language.

    Returns:
        The Jinja environment.
    """
    environment = Environment(
        loader=PackageLoader(_TEMPLATES_PACKAGE, "templates"),
        autoescape=select_autoescape(enabled_extensions=("html", "j2")),
        extensions=["jinja2.ext.i18n"],
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    # pylint: disable-next=no-member
    environment.install_gettext_translations(  # type: ignore[attr-defined]
        active(),
        newstyle=True,
    )
    environment.filters["size"] = human_size
    return environment
