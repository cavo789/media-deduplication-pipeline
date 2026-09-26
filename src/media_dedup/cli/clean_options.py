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
                "check them in the report first."
            ),
            case_sensitive=False,
        ),
    )
