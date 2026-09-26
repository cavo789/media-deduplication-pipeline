"""`media-dedup crosscheck`: compare a fresh audit with Czkawka's results."""

from __future__ import annotations

from typing import Annotated

import typer

from media_dedup.cli import options
from media_dedup.cli.context import folder_layer, runtime_of, scan_layer, user_errors
from media_dedup.cli.flows import audit_and_show, report_and_announce
from media_dedup.console.crosscheck_view import show_cross_check
from media_dedup.constants import ExitCode, RunKind
from media_dedup.errors import MountError
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.views import ReportRecord
from media_dedup.services.crosscheck import cross_check, czkawka_command


def crosscheck_command(  # pylint: disable=too-many-arguments
    ctx: typer.Context,
    *,
    prefer: Annotated[list[str] | None, options.prefer()] = None,
    protect: Annotated[list[str] | None, options.protect()] = None,
    exclude: Annotated[list[str] | None, options.exclude()] = None,
    ext: Annotated[list[str] | None, options.extensions()] = None,
) -> None:
    """Audit again (fast with the cache), then compare with Czkawka's groups.

    Args:
        ctx: Typer context holding the runtime.
        prefer: `--prefer` folders.
        protect: `--protect` folders.
        exclude: `--exclude` folders.
        ext: `--ext` extensions.

    Raises:
        MountError: No reports mount point, where Czkawka's results are read.
        typer.Exit: Czkawka has not been run yet.
    """
    runtime = runtime_of(ctx)
    output = runtime.output
    with user_errors(output):
        runtime = runtime.with_overrides(
            folder_layer(prefer, protect, exclude)
        ).with_overrides(scan_layer(ext))
        if not runtime.persistent(MountKind.REPORTS):
            raise MountError(
                _("'crosscheck' reads Czkawka's results from /reports: mount it."),
                _('Add -v "<a folder of yours>:/reports", as in the Czkawka command.'),
            )
        findings = audit_and_show(runtime)
        result = cross_check(runtime, findings)
        if result is None:
            output.error(_("No Czkawka results yet: run Czkawka first (PowerShell):"))
            output.command(czkawka_command(runtime).render())
            raise typer.Exit(ExitCode.FAILURE)
        output.title(_("Second opinion"))
        show_cross_check(output, result, runtime.mapper)
        report_and_announce(
            runtime, ReportRecord(RunKind.AUDIT, findings, crosscheck=result)
        )
