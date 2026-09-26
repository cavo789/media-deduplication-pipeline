"""Invoke the command line in-process."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.cli.app import build_app

if TYPE_CHECKING:
    from typer.testing import CliRunner, Result


def run(runner: CliRunner, *args: str) -> Result:
    """Invoke the CLI with `args`, letting unexpected exceptions through.

    Args:
        runner: The Typer runner.
        *args: The command line.

    Returns:
        The result.
    """
    return runner.invoke(build_app(), list(args), catch_exceptions=False)
