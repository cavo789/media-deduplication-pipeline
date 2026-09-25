"""`media-dedup undo`: restore the files of a clean run."""

from __future__ import annotations

from typing import Annotated

import typer

from media_dedup.cli.context import runtime_of, user_errors
from media_dedup.console.progress import RichProgress
from media_dedup.console.tables import outcome_table
from media_dedup.i18n import _
from media_dedup.scan.progress import NullProgress
from media_dedup.services.clean import CleanService
from media_dedup.services.undo import resolve_run_id, undo_run


def undo_command(
    ctx: typer.Context,
    run_id: Annotated[
        str | None,
        typer.Argument(
            help=_("Run to undo (see 'history'); the latest one by default.")
        ),
    ] = None,
) -> None:
    """Restore every file deleted or quarantined by a clean run.

    Args:
        ctx: Typer context holding the runtime.
        run_id: Run identifier, or None for the latest run.
    """
    runtime = runtime_of(ctx)
    output = runtime.output
    with user_errors(output):
        run = resolve_run_id(runtime, run_id)
        CleanService(runtime, NullProgress()).ensure_ready()
        output.title(_("Undo {run_id}").format(run_id=run))
        with RichProgress(output.console) as progress:
            outcome = undo_run(runtime, run, progress)
    output.show(outcome_table(outcome, _("Undo {run_id}").format(run_id=run)))
    for incident in outcome.skipped:
        output.warning(f"{runtime.mapper.to_host(incident.path)}: {incident.reason}")
    for incident in outcome.failed:
        output.error(f"{runtime.mapper.to_host(incident.path)}: {incident.reason}")
