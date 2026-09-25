"""`media-dedup history`: list the clean runs recorded in the journal."""

from __future__ import annotations

import typer
from rich.table import Table

from media_dedup.actions.runs import list_run_ids, summarize
from media_dedup.cli.context import runtime_of, user_errors
from media_dedup.console.formatting import human_size
from media_dedup.errors import MountError
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind


def history_command(ctx: typer.Context) -> None:
    """Show every clean run: files deleted, space freed, quarantine, restores.

    Args:
        ctx: Typer context holding the runtime.

    Raises:
        MountError: The journal is not mounted.
    """
    runtime = runtime_of(ctx)
    output = runtime.output
    with user_errors(output):
        if not runtime.persistent(MountKind.JOURNAL):
            raise MountError(
                _("No journal mount: no history to show."),
                _('Mount the journal folder used by clean: -v "<folder>:/journal".'),
            )
        runs = list_run_ids(runtime.locations.journal_dir)
        summaries = [summarize(runtime.locations.journal_dir, run) for run in runs]
    if not summaries:
        output.info(_("No clean run yet."))
        return
    table = Table(title=_("Clean runs (newest first)"), title_justify="left")
    for header in (_("Run"), _("Deleted"), _("Freed"), _("Quarantined"), _("Restored")):
        table.add_column(header, justify="left" if header == _("Run") else "right")
    for run in summaries:
        table.add_row(
            run.run_id,
            str(run.deleted),
            human_size(run.freed),
            str(run.quarantined),
            str(run.restored),
        )
    output.show(table)
    output.tip(_("'media-dedup undo <run>' restores the files of a run."))
