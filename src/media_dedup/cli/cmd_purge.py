"""`media-dedup purge`: permanently delete quarantined broken files."""

from __future__ import annotations

from typing import Annotated

import typer

from media_dedup.actions.purge import folder_size, purge_run, quarantine_runs
from media_dedup.cli import options
from media_dedup.cli.context import runtime_of, user_errors
from media_dedup.console.formatting import human_size
from media_dedup.constants import ExitCode
from media_dedup.errors import MediaDedupError
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind
from media_dedup.services.writable import ensure_writable


def purge_command(
    ctx: typer.Context,
    run_id: Annotated[
        str | None,
        typer.Argument(
            help=_("Run whose quarantine is deleted; every run by default.")
        ),
    ] = None,
    *,
    yes: Annotated[bool, options.yes()] = False,
) -> None:
    """Free the space held by the quarantine — this cannot be undone.

    Args:
        ctx: Typer context holding the runtime.
        run_id: Run to purge, or None for every run.
        yes: `--yes`, skip the confirmation.

    Raises:
        MediaDedupError: The requested run has no quarantine, or the quarantine is
            not writable.
        typer.Exit: The user declined.
    """
    runtime = runtime_of(ctx)
    output = runtime.output
    quarantine_dir = runtime.locations.quarantine_dir
    with user_errors(output):
        ensure_writable(runtime, MountKind.QUARANTINE)
        runs = quarantine_runs(quarantine_dir)
        if run_id is not None:
            if run_id not in runs:
                raise MediaDedupError(
                    _("Run {run_id} has no quarantine.").format(run_id=run_id)
                )
            runs = [run_id]
    if not runs:
        output.info(_("The quarantine is empty."))
        return
    size = human_size(sum(folder_size(quarantine_dir / run) for run in runs))
    question = _("Permanently delete the quarantine of {runs} ({size})?")
    if not yes and not output.confirm(question.format(runs=", ".join(runs), size=size)):
        output.info(_("Nothing was changed."))
        raise typer.Exit(ExitCode.OK)
    freed = sum(purge_run(quarantine_dir, run) for run in runs)
    output.success(_("Quarantine purged: {size} freed.").format(size=human_size(freed)))
    output.tip(_("'undo' can no longer restore these broken files."))
