"""Steps shared by several commands: audit and display, report, confirmation."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from media_dedup.console.formatting import human_number, human_size
from media_dedup.console.progress import RichProgress
from media_dedup.console.tables import findings_table, folder_pairs_view
from media_dedup.errors import MediaDedupError
from media_dedup.i18n import _
from media_dedup.services.audit import AuditService
from media_dedup.services.reporting import write_report

if TYPE_CHECKING:
    from media_dedup.plan.models import AuditFindings, CleanPlan
    from media_dedup.report.views import ReportRecord
    from media_dedup.services.runtime import Runtime


def audit_and_show(runtime: Runtime) -> AuditFindings:
    """Run the audit with progress bars, then print its summary.

    Args:
        runtime: Settings, mount points and output.

    Returns:
        The findings.
    """
    output = runtime.output
    output.title(_("Audit"))
    with RichProgress(output.console) as progress:
        findings = AuditService(runtime, progress).run()
    output.show(findings_table(findings))
    output.blank()
    pairs = folder_pairs_view(findings, runtime.mapper)
    if pairs is not None:
        output.show(pairs)
        output.blank()
    return findings


def report_and_announce(runtime: Runtime, record: ReportRecord) -> None:
    """Write the HTML report and tell the user where it is.

    Args:
        runtime: Settings, mount points and output.
        record: What to report.
    """
    output = runtime.output
    report = write_report(runtime, record)
    if report is None:
        output.tip(_('Add -v "<a folder of yours>:/reports" to get HTML reports.'))
        return
    output.success(_("HTML report: {path}").format(path=report))
    output.tip(
        _("Open index.html in the folder mounted on /reports: it lists every report."),
    )


def confirm_clean(runtime: Runtime, plan: CleanPlan, yes: bool) -> bool:  # noqa: FBT001
    """Ask before cleaning, unless `--yes` or `[clean] confirm = false`.

    Args:
        runtime: Settings, mount points and output.
        plan: What would be cleaned.
        yes: `--yes` was given.

    Returns:
        True when the clean may proceed.

    Raises:
        MediaDedupError: Confirmation is required but there is no terminal to ask in.
    """
    if yes or not runtime.settings.clean.confirm:
        return True
    if not sys.stdin.isatty():
        raise MediaDedupError(
            _("Cannot ask for confirmation without an interactive terminal."),
            _("Run docker with -it, or add --yes."),
        )
    question = _(
        "Delete {count} duplicate copies ({size}) and handle {broken} broken files?"
    )
    return runtime.output.confirm(
        question.format(
            count=human_number(plan.removable_count),
            size=human_size(plan.reclaimable),
            broken=human_number(len(plan.broken)),
        ),
    )
