"""`media-dedup clean`: really delete duplicates, journaled and undoable."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Annotated

import typer

from media_dedup.cli import options
from media_dedup.cli.context import folder_layer, runtime_of, scan_layer, user_errors
from media_dedup.cli.flows import (
    audit_and_show,
    confirm_clean,
    report_and_announce,
    show_second_opinion,
)
from media_dedup.console.progress import RichProgress
from media_dedup.console.tables import outcome_table
from media_dedup.constants import ExitCode, RunKind
from media_dedup.i18n import _
from media_dedup.report.views import ReportRecord
from media_dedup.services.clean import CleanService

if TYPE_CHECKING:
    from media_dedup.actions.outcome import Outcome
    from media_dedup.console.output import Output


def clean_command(  # pylint: disable=too-many-arguments
    ctx: typer.Context,
    *,
    prefer: Annotated[list[str] | None, options.prefer()] = None,
    protect: Annotated[list[str] | None, options.protect()] = None,
    exclude: Annotated[list[str] | None, options.exclude()] = None,
    ext: Annotated[list[str] | None, options.extensions()] = None,
    yes: Annotated[bool, options.yes()] = False,
) -> None:
    """Audit, confirm, then delete duplicate copies and handle broken files.

    Args:
        ctx: Typer context holding the runtime.
        prefer: `--prefer` folders.
        protect: `--protect` folders.
        exclude: `--exclude` folders.
        ext: `--ext` extensions.
        yes: `--yes`, skip the confirmation.

    Raises:
        typer.Exit: The user declined.
    """
    runtime = runtime_of(ctx)
    output = runtime.output
    with user_errors(output), RichProgress(output.console) as progress:
        runtime = runtime.with_overrides(
            folder_layer(prefer, protect, exclude)
        ).with_overrides(scan_layer(ext))
        service = CleanService(runtime, progress)
        service.ensure_ready()
        findings = audit_and_show(runtime)
        plan = service.feasible(findings.plan)
        verdict = None if plan.is_empty else show_second_opinion(runtime, findings)
        if plan.is_empty:
            output.success(_("Nothing to clean: no duplicate and no broken file."))
            return
        if not confirm_clean(runtime, plan, yes):
            output.info(_("Nothing was changed."))
            raise typer.Exit(ExitCode.OK)
        output.title(_("Clean"))
        run_id, outcome = service.execute(plan)
        output.show(outcome_table(outcome, _("Clean {run_id}").format(run_id=run_id)))
        report_and_announce(
            runtime,
            ReportRecord(
                RunKind.CLEAN,
                replace(findings, plan=plan),
                outcome,
                run_id,
                crosscheck=verdict,
            ),
        )
    _after_clean_tips(output, run_id, outcome)


def _after_clean_tips(output: Output, run_id: str, outcome: Outcome) -> None:
    """Tell how to undo the clean and how to purge the quarantine.

    Args:
        output: Where to print.
        run_id: The clean run.
        outcome: What the clean did.
    """
    undo_tip = _("Changed your mind? 'media-dedup undo {run_id}' restores everything.")
    output.tip(undo_tip.format(run_id=run_id))
    if outcome.quarantined:
        purge_tip = _("Broken files are in /quarantine/{run_id}; 'purge' deletes them.")
        output.tip(purge_tip.format(run_id=run_id))
