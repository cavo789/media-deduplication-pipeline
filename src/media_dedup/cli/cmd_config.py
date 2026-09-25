"""`media-dedup config`: show every effective setting, its origin, and the mounts."""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from rich.table import Table

from media_dedup.cli.context import runtime_of
from media_dedup.config.loader import Origin
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind
from media_dedup.paths.mounts import is_read_only

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.services.runtime import Runtime


def _origin_label(origin: Origin) -> str:
    labels = {
        Origin.DEFAULT: _("default"),
        Origin.FILE: _("config.toml"),
        Origin.ENV: _("environment"),
        Origin.CLI: _("command line"),
    }
    return labels[origin]


def config_command(ctx: typer.Context) -> None:
    """Explain the effective configuration and the state of each mount point.

    Args:
        ctx: Typer context holding the runtime.
    """
    runtime = runtime_of(ctx)
    settings = runtime.settings.model_dump(mode="json")
    table = Table(title=_("Effective settings"), title_justify="left")
    for header in (_("Setting"), _("Value"), _("Origin")):
        table.add_column(header, overflow="fold")
    for section, values in settings.items():
        for key, value in values.items():
            origin = _origin_label(runtime.loaded.origin_of(section, key))
            table.add_row(f"{section}.{key}", str(value), origin)
    runtime.output.show(table)
    runtime.output.blank()
    runtime.output.show(_mounts_table(runtime))
    runtime.output.blank()
    config_file = runtime.locations.config_file
    if runtime.persistent(MountKind.CONFIG):
        runtime.output.tip(
            _("Edit {path} to change these settings; command-line options win.").format(
                path=_on_host(runtime, config_file) or config_file,
            ),
        )
    else:
        runtime.output.tip(
            _(
                "To keep settings, mount a folder of yours on /config, e.g. "
                '-v "$HOME\\media-dedup\\config:/config": config.toml is created '
                "there, commented, on the first run; edit it with any text editor."
            ),
        )


def _mounts_table(runtime: Runtime) -> Table:
    """Each mount point, the folder of the user's computer behind it, and its state.

    The data mount point lists every folder mounted below it.

    Args:
        runtime: Settings, mount points and output.

    Returns:
        The table.
    """
    table = Table(title=_("Mount points"), title_justify="left")
    for header in (_("Mount"), _("Folder on your computer"), _("State")):
        table.add_column(header, overflow="fold")
    data_dir = runtime.locations.data_dir
    for kind in MountKind:
        path = runtime.locations.path_of(kind)
        paths = [path]
        if kind is MountKind.DATA:
            paths = list(runtime.mounts.data_roots(data_dir))
        for mount in paths:
            table.add_row(
                str(mount),
                _on_host(runtime, mount) or "—",
                _state(runtime, kind, mount),
            )
    return table


def _state(runtime: Runtime, kind: MountKind, path: Path) -> str:
    """Describe whether a mount point is mounted, and how.

    Args:
        runtime: Settings, mount points and output.
        kind: Which mount point.
        path: The mount point, or a folder mounted below `/data`.

    Returns:
        The translated, coloured state.
    """
    mounted = (
        path in runtime.mounts.mount_points
        if kind is MountKind.DATA
        else runtime.persistent(kind)
    )
    if not mounted and kind is MountKind.DATA:
        return _("[yellow]not mounted[/] — nothing to analyse")
    if not mounted:
        return _("[yellow]not mounted[/] — nothing kept after the run")
    if path.is_dir() and is_read_only(path):
        return _("[cyan]read-only[/]")
    return _("[green]mounted[/]")


def _on_host(runtime: Runtime, path: Path) -> str | None:
    r"""Return the folder of the user's computer behind a container path, when known.

    Args:
        runtime: Settings, mount points and output.
        path: A container path.

    Returns:
        E.g. `C:\Users\me\media-dedup\config`, or None (Docker volume, unknown).
    """
    host = runtime.mapper.to_host(path)
    return None if host == str(path) else host
