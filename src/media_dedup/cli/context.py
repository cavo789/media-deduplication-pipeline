"""Build the runtime of a command and turn domain errors into clean exits."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import typer

from media_dedup.config.loader import load_settings, write_default_config
from media_dedup.console.logs import configure_logging
from media_dedup.console.output import Output, make_console
from media_dedup.constants import ColorMode, ExitCode
from media_dedup.errors import MediaDedupError
from media_dedup.i18n import _
from media_dedup.paths.locations import Locations
from media_dedup.paths.mount_kind import MountKind
from media_dedup.paths.mounts import MountTable
from media_dedup.services.runtime import Runtime

if TYPE_CHECKING:
    from collections.abc import Iterator

    from media_dedup.config.layers import Layer


@contextmanager
def user_errors(output: Output) -> Iterator[None]:
    """Print a domain error with its tip, then exit with a failure code.

    Args:
        output: Where to print.

    Yields:
        Control to the guarded block.

    Raises:
        typer.Exit: A domain error occurred.
    """
    try:
        yield
    except MediaDedupError as exc:
        output.error(exc.message)
        if exc.tip:
            output.tip(exc.tip)
        raise typer.Exit(ExitCode.FAILURE) from exc


def build_runtime(cli_layer: Layer) -> Runtime:
    """Load the settings, set up the output and snapshot the mount table.

    Args:
        cli_layer: Global options typed on the command line.

    Returns:
        The runtime of this invocation.
    """
    locations = Locations()
    with user_errors(Output(make_console(ColorMode.AUTO))):
        loaded = load_settings(locations, cli_layer)
    general = loaded.settings.general
    output = Output(make_console(general.color))
    configure_logging(general.verbosity, output.console)
    runtime = Runtime(loaded, locations, MountTable.current(), output, cli_layer)
    if runtime.persistent(MountKind.CONFIG) and write_default_config(
        locations.config_file
    ):
        output.tip(
            _("A commented configuration file was created: {path}.").format(
                path=locations.config_file,
            ),
        )
    return runtime


def runtime_of(ctx: typer.Context) -> Runtime:
    """Return the runtime the root callback stored in the Typer context.

    Every command calls it first: it also schedules an empty line after the
    command's last message, before the shell prompt comes back (`--help` never
    reaches a command, so its output is left as is).

    Args:
        ctx: Typer context of the running command.

    Returns:
        The runtime.

    Raises:
        TypeError: The root callback did not run (programming error).
    """
    runtime = ctx.obj
    if not isinstance(runtime, Runtime):
        raise TypeError(type(runtime).__name__)
    ctx.call_on_close(runtime.output.blank)
    return runtime


def folder_layer(
    prefer: list[str] | None,
    protect: list[str] | None,
    exclude: list[str] | None,
) -> Layer:
    """Turn the folder options of a command into a settings layer.

    Args:
        prefer: `--prefer` values.
        protect: `--protect` values.
        exclude: `--exclude` values.

    Returns:
        The `[folders]` overrides actually given.
    """
    given = {"preferred": prefer, "protected": protect, "excluded": exclude}
    folders: dict[str, object] = {key: value for key, value in given.items() if value}
    return {"folders": folders} if folders else {}


def scan_layer(extensions: list[str] | None) -> Layer:
    """Turn the `--ext` option of a command into a settings layer.

    Args:
        extensions: `--ext` values (validated and split by the settings).

    Returns:
        The `[scan]` overrides actually given.
    """
    return {"scan": {"extensions": extensions}} if extensions else {}
