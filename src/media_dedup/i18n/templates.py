"""Jinja environments whose `_()` uses the active language (reports, config.toml)."""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from media_dedup.i18n import active


def translated_environment(package: str, escaped: tuple[str, ...]) -> Environment:
    """Create a Jinja environment loading `<package>/templates`, translated.

    Args:
        package: The package holding a `templates` directory.
        escaped: Template extensions to HTML-escape (none for plain text such as TOML).

    Returns:
        The environment.
    """
    environment = Environment(
        loader=PackageLoader(package, "templates"),
        autoescape=select_autoescape(enabled_extensions=escaped),
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
    return environment
