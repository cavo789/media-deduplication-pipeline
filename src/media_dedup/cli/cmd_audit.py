"""`media-dedup audit`: analyse without modifying anything."""

from __future__ import annotations

from typing import Annotated

import typer

from media_dedup.cli import options
from media_dedup.cli.context import folder_layer, runtime_of, scan_layer, user_errors
from media_dedup.cli.flows import audit_and_show, report_and_announce
from media_dedup.console.formatting import human_size
from media_dedup.constants import RunKind
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.views import ReportRecord


def audit_command(  # pylint: disable=too-many-arguments
    ctx: typer.Context,
    *,
    prefer: Annotated[list[str] | None, options.prefer()] = None,
    protect: Annotated[list[str] | None, options.protect()] = None,
    exclude: Annotated[list[str] | None, options.exclude()] = None,
    ext: Annotated[list[str] | None, options.extensions()] = None,
) -> None:
    """Find exact duplicates and broken files; never writes to `/data`.

    Args:
        ctx: Typer context holding the runtime.
        prefer: `--prefer` folders.
        protect: `--protect` folders.
        exclude: `--exclude` folders.
        ext: `--ext` extensions.
    """
    runtime = runtime_of(ctx)
    with user_errors(runtime.output):
        runtime = runtime.with_overrides(
            folder_layer(prefer, protect, exclude)
        ).with_overrides(scan_layer(ext))
        findings = audit_and_show(runtime)
        report_and_announce(runtime, ReportRecord(RunKind.AUDIT, findings))
    output, plan = runtime.output, findings.plan
    if plan.is_empty:
        output.success(_("Nothing to clean: no duplicate and no broken file."))
    else:
        output.tip(
            _("Run 'clean' (same -v options, without :ro) to free {size}.").format(
                size=human_size(plan.reclaimable),
            ),
        )
        if not runtime.settings.folders.preferred:
            output.tip(
                _(
                    "Choose which folders keep their copies: folders.preferred in "
                    "config.toml, or --prefer."
                ),
            )
    if not runtime.persistent(MountKind.CACHE):
        output.tip(
            _("Add -v media-dedup-cache:/cache: the next audits will be much faster.")
        )
