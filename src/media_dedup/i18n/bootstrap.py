"""Pick the interface language before the CLI is built, so `--help` is translated."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.config.loader import load_settings
from media_dedup.constants import Locale
from media_dedup.errors import ConfigError
from media_dedup.paths.locations import Locations

if TYPE_CHECKING:
    from collections.abc import Sequence

_LOCALE_FLAG = "--locale"


def locale_from_argv(argv: Sequence[str]) -> Locale | None:
    """Find a valid `--locale X` or `--locale=X` anywhere on the command line.

    Args:
        argv: Command-line arguments, without the program name.

    Returns:
        The requested locale, or None when absent or invalid (Typer reports it later).
    """
    for index, argument in enumerate(argv):
        value: str | None = None
        if argument == _LOCALE_FLAG and index + 1 < len(argv):
            value = argv[index + 1]
        elif argument.startswith(f"{_LOCALE_FLAG}="):
            value = argument.partition("=")[2]
        if value is not None and value in Locale:
            return Locale(value)
    return None


def resolve_locale(argv: Sequence[str]) -> Locale:
    """Resolve the language with the usual precedence: CLI, environment, file, default.

    Args:
        argv: Command-line arguments, without the program name.

    Returns:
        The locale to install. An unreadable config falls back to English: the command
        itself reports the configuration error right after.
    """
    from_cli = locale_from_argv(argv)
    if from_cli is not None:
        return from_cli
    try:
        return load_settings(Locations()).settings.general.locale
    except ConfigError:
        return Locale.EN
