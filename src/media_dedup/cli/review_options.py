"""Options only `review` has, translated once the locale is known."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import typer

from media_dedup.cli.clean_options import decisions_option
from media_dedup.i18n import _

if TYPE_CHECKING:
    from typer.models import OptionInfo


def decisions_file() -> OptionInfo:
    """`--decisions`: where the review saves its decisions, and resumes from.

    Returns:
        The option definition.
    """
    return decisions_option(
        _(
            "File the decisions are saved in, and resumed from. A relative path "
            "lies in the folder mounted on /reports. Default: decisions.json."
        )
    )


def port() -> OptionInfo:
    """`--port`: the port of the page, inside the container.

    Returns:
        The option definition.
    """
    return cast(
        "OptionInfo",
        typer.Option(
            "--port",
            min=0,
            help=_(
                "Port of the page inside the container; publish it with "
                "-p 127.0.0.1::8080 so that Docker chooses a free one on your "
                "computer. Default: 8080."
            ),
            show_default=False,
        ),
    )
