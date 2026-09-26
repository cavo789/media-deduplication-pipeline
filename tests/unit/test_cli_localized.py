"""Typer's built-in help strings, translated by the classes given to Typer."""

from __future__ import annotations

from typer import Context

from media_dedup.cli.localized import LocalizedCommand


def test_english_keeps_the_usual_wording() -> None:
    """Without a catalog, the usage line and `--help` read as Click writes them."""
    command = LocalizedCommand(name="bare")
    ctx = Context(command, info_name="bare")
    assert command.get_usage(ctx) == "Usage: bare [OPTIONS]"
    option = command.get_help_option(ctx)
    assert option is not None
    assert option.help == "Show this message and exit."


def test_a_command_without_help_option_has_none() -> None:
    """`add_help_option=False` still means no `--help` at all."""
    command = LocalizedCommand(name="bare", add_help_option=False)
    assert command.get_help_option(Context(command)) is None
