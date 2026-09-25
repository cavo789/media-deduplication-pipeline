"""The root callback: global options, loaded before any command runs."""

from __future__ import annotations

from importlib.metadata import version as package_version
from typing import Annotated

import typer

from media_dedup.cli import options
from media_dedup.cli.context import build_runtime
from media_dedup.constants import ColorMode, Locale, Verbosity

_DISTRIBUTION = "media-deduplication-pipeline"


def print_version(value: bool) -> None:  # noqa: FBT001 - Typer callback signature
    """Print the version and stop, when `--version` is given.

    Args:
        value: Whether `--version` was given.

    Raises:
        typer.Exit: Always, once the version is printed.
    """
    if not value:
        return
    typer.echo(f"media-dedup {package_version(_DISTRIBUTION)}")
    raise typer.Exit


def root_callback(  # pylint: disable=too-many-arguments
    ctx: typer.Context,
    *,
    locale: Annotated[Locale | None, options.locale()] = None,
    verbosity: Annotated[Verbosity | None, options.verbosity()] = None,
    color: Annotated[ColorMode | None, options.color()] = None,
    _version: Annotated[bool, options.version(print_version)] = False,
) -> None:
    """Load the settings shared by every command.

    Args:
        ctx: Typer context, receiving the runtime.
        locale: `--locale` override.
        verbosity: `--verbosity` override.
        color: `--color` override.
    """
    if ctx.resilient_parsing:
        return
    given = {"locale": locale, "verbosity": verbosity, "color": color}
    general: dict[str, object] = {key: value for key, value in given.items() if value}
    ctx.obj = build_runtime({"general": general} if general else {})
