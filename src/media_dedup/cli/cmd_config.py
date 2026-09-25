"""`media-dedup config`: show every effective setting, its origin, and the mounts."""

from __future__ import annotations

import typer
from rich.table import Table

from media_dedup.cli.context import runtime_of
from media_dedup.config.loader import Origin
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind
from media_dedup.paths.mounts import is_read_only


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

    mounts = Table(title=_("Mount points"), title_justify="left")
    for header in (_("Mount"), _("Path"), _("State")):
        mounts.add_column(header, overflow="fold")
    for kind in MountKind:
        path = runtime.locations.path_of(kind)
        if not runtime.persistent(kind):
            state = _("[yellow]not mounted[/] — nothing kept after the run")
        elif path.is_dir() and is_read_only(path):
            state = _("[cyan]read-only[/]")
        else:
            state = _("[green]mounted[/]")
        mounts.add_row(f"/{kind.value}", str(path), state)
    runtime.output.show(mounts)
    runtime.output.tip(
        _("Edit {path} to change these settings; command-line options win.").format(
            path=runtime.locations.config_file,
        ),
    )
