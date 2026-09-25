"""`media-dedup reports`: list the HTML reports of previous audits and cleans."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table

from media_dedup.cli.context import runtime_of, user_errors
from media_dedup.console.formatting import human_number, human_size
from media_dedup.constants import RunKind
from media_dedup.errors import MountError
from media_dedup.i18n import _, ngettext
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.index_page import load_summaries, prune_reports, write_index


def reports_command(
    ctx: typer.Context,
    prune: Annotated[
        int | None,
        typer.Option(
            "--prune",
            min=0,
            help=_("Delete all reports but the N most recent ones."),
            show_default=False,
        ),
    ] = None,
) -> None:
    """List every report (newest first) and refresh `index.html`.

    Args:
        ctx: Typer context holding the runtime.
        prune: Number of reports to keep, when pruning.

    Raises:
        MountError: The reports folder is not mounted.
    """
    runtime = runtime_of(ctx)
    output = runtime.output
    reports_dir = runtime.locations.reports_dir
    with user_errors(output):
        if not runtime.persistent(MountKind.REPORTS) or not reports_dir.is_dir():
            raise MountError(
                _("No reports mount: there is no report to list."),
                _('Mount the reports folder: -v "<folder>:/reports".'),
            )
    if prune is not None:
        removed = prune_reports(reports_dir, prune)
        output.success(
            ngettext(
                "{count} report deleted.", "{count} reports deleted.", len(removed)
            ).format(
                count=human_number(len(removed)),
            ),
        )
    index = write_index(reports_dir)
    summaries = load_summaries(reports_dir)
    table = Table(title=_("Reports (newest first)"), title_justify="left")
    for header in (
        _("Folder"),
        _("Type"),
        _("Files"),
        _("Duplicates"),
        _("Space"),
        _("Broken"),
    ):
        table.add_column(header)
    for summary in summaries:
        is_clean = summary.kind is RunKind.CLEAN
        table.add_row(
            summary.folder,
            _("clean") if is_clean else _("audit"),
            human_number(summary.files_scanned),
            human_number(summary.duplicate_files),
            human_size(summary.freed_bytes if is_clean else summary.reclaimable_bytes),
            human_number(summary.broken_files),
        )
    output.show(table)
    output.tip(
        _("Double-click {name} in the folder mounted on /reports.").format(
            name=index.name
        )
    )
