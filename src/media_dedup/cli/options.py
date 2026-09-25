"""Shared, translated option definitions, evaluated once the locale is known."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import typer

from media_dedup.config.settings import supported_extensions
from media_dedup.i18n import _

if TYPE_CHECKING:
    from collections.abc import Callable

    from typer.models import OptionInfo


def _panel_folders() -> str:
    return _("Folders (override folders.* of config.toml)")


def _panel_scan() -> str:
    return _("Scan (override scan.* of config.toml)")


def _panel_output() -> str:
    return _("Output (override general.* of config.toml)")


def locale() -> OptionInfo:
    """`--locale`: interface language.

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--locale",
            help=_("Interface language."),
            rich_help_panel=_panel_output(),
            show_default=False,
        ),
    )


def verbosity() -> OptionInfo:
    """`--verbosity`: log level.

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--verbosity",
            help=_("How much to log."),
            rich_help_panel=_panel_output(),
            show_default=False,
        ),
    )


def color() -> OptionInfo:
    """`--color`: ANSI colours.

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--color",
            help=_("When to use colours (NO_COLOR is honoured too)."),
            rich_help_panel=_panel_output(),
            show_default=False,
        ),
    )


def version(callback: Callable[[bool], None]) -> OptionInfo:
    """`--version`: print the version and exit.

    Args:
        callback: Eager callback printing the version.

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--version",
            help=_("Show the version and exit."),
            callback=callback,
            is_eager=True,
        ),
    )


def prefer() -> OptionInfo:
    """`--prefer`: folder whose copies are kept first (repeatable, ordered).

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--prefer",
            help=_("Folder whose copies are kept first. Repeat it; the order matters."),
            rich_help_panel=_panel_folders(),
            show_default=False,
        ),
    )


def protect() -> OptionInfo:
    """`--protect`: folder never modified (repeatable).

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--protect",
            help=_("Folder never modified; its files are the copies kept. Repeatable."),
            rich_help_panel=_panel_folders(),
            show_default=False,
        ),
    )


def exclude() -> OptionInfo:
    """`--exclude`: folder never analysed (repeatable).

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--exclude",
            help=_("Folder never analysed, e.g. a real backup to keep. Repeatable."),
            rich_help_panel=_panel_folders(),
            show_default=False,
        ),
    )


def extensions() -> OptionInfo:
    """`--ext`: only analyse some extensions (repeatable or comma-separated).

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--ext",
            help=_(
                "Only analyse files with these extensions, e.g. --ext png,webp "
                "(repeatable). Default: every supported extension: {extensions}."
            ).format(extensions=supported_extensions()),
            rich_help_panel=_panel_scan(),
            show_default=False,
        ),
    )


def yes() -> OptionInfo:
    """`--yes`: do not ask for confirmation.

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--yes",
            "-y",
            help=_("Do not ask for confirmation (overrides clean.confirm)."),
        ),
    )
