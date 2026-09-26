"""Options only `clean` has, translated once the locale is known."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import typer

from media_dedup.i18n import _

if TYPE_CHECKING:
    from typer.models import OptionInfo


def tier() -> OptionInfo:
    """`--tier`: how far `clean` goes (near duplicates only when asked).

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--tier",
            help=_(
                "exact: delete byte-for-byte copies only. near: also move near "
                "duplicates (resized or recompressed copies) to the quarantine; "
                "check them in the report first. Default: exact."
            ),
            show_default=False,
            case_sensitive=False,
        ),
    )


def decisions() -> OptionInfo:
    """`--decisions`: apply the decisions of a report or of `review`.

    Returns:
        The option definition.
    """
    return decisions_option(
        _(
            "decisions.json downloaded from an audit report (swap or leave alone "
            "some folder pairs) or written by 'review' (burst shots set aside). "
            "A relative path is read from the folder mounted on /reports. The "
            "file is refused if the folders, the pairs or the series changed."
        )
    )


def decisions_option(help_text: str) -> OptionInfo:
    """`--decisions`, shared by `clean` (reads it) and `review` (writes it).

    Args:
        help_text: The translated help of the command.

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option("--decisions", help=help_text, show_default=False),
    )
