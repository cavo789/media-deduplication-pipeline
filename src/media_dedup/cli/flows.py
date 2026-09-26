"""Steps shared by several commands: audit and display, report, confirmation."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from media_dedup.console.crosscheck_view import show_cross_check
from media_dedup.console.formatting import human_number, human_size
from media_dedup.console.progress import RichProgress
from media_dedup.console.tables import findings_table, folder_pairs_view
from media_dedup.errors import CrossCheckError, MediaDedupError, MountError
from media_dedup.i18n import _, ngettext
from media_dedup.paths.mount_kind import MountKind
from media_dedup.services.audit import AuditService
from media_dedup.services.crosscheck import cross_check
from media_dedup.services.reporting import write_report
from media_dedup.services.writable import ensure_writable

if TYPE_CHECKING:
    from media_dedup.crosscheck.compare import CrossCheckResult
    from media_dedup.plan.models import AuditFindings, CleanPlan
    from media_dedup.report.views import ReportRecord
    from media_dedup.services.runtime import Runtime


def audit_and_show(runtime: Runtime) -> AuditFindings:
    """Run the audit with progress bars, then print its summary.

    Args:
        runtime: Settings, mount points and output.

    Returns:
        The findings.

    Raises:
        MountError: The index or the report could not be written (checked first).
    """
    ensure_writable(runtime, MountKind.CACHE, MountKind.REPORTS)
    output = runtime.output
    output.title(_("Audit"))
    with RichProgress(output.console) as progress:
        findings = AuditService(runtime, progress).run()
    output.show(findings_table(findings))
    output.blank()
    show_pairs(runtime, findings)
    return findings


def show_pairs(runtime: Runtime, findings: AuditFindings) -> None:
    """Print the folder pairs freeing the most space, when there are any.

    Args:
        runtime: Settings, mount points and output.
        findings: The audit, or the plan once reviewed.
    """
    pairs = folder_pairs_view(findings, runtime.mapper)
    if pairs is not None:
        runtime.output.show(pairs)
        runtime.output.blank()


def show_second_opinion(
    runtime: Runtime, findings: AuditFindings
) -> CrossCheckResult | None:
    """Show Czkawka's verdict on this audit, or say it was not cross-checked.

    Information only: unusable Czkawka results are a warning, never an error.

    Args:
        runtime: Settings, mount points and output.
        findings: The audit just run.

    Returns:
        The comparison, or None without Czkawka results.
    """
    try:
        result = cross_check(runtime, findings)
    except CrossCheckError as exc:  # information only: never blocks a clean
        runtime.output.warning(exc.message)
        return None
    if result is None:
        runtime.output.info(
            _("Not cross-checked: 'media-dedup crosscheck' compares with Czkawka.")
        )
        return None
    show_cross_check(runtime.output, result, runtime.mapper)
    runtime.output.blank()
    return result


def report_and_announce(runtime: Runtime, record: ReportRecord) -> None:
    """Write the HTML report and tell the user where it is.

    A report that cannot be written is only a warning: the results are on screen.

    Args:
        runtime: Settings, mount points and output.
        record: What to report.
    """
    output = runtime.output
    try:
        report = write_report(runtime, record)
    except MountError as exc:
        output.warning(exc.message)
        if exc.tip:
            output.tip(exc.tip)
        return
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
    question = (
        _(
            "Delete {count} duplicate copies ({size}), move {near} near duplicates "
            "to the quarantine and handle {broken} broken files?"
        )
        if plan.near_count
        else _(
            "Delete {count} duplicate copies ({size}) and handle {broken} broken files?"
        )
    )
    if plan.moved_copies:
        moved = ngettext(
            "{count} copy of another file than a media will be moved to the "
            "quarantine, not deleted.",
            "{count} copies of other files than media will be moved to the "
            "quarantine, not deleted.",
            plan.moved_copies,
        )
        runtime.output.info(moved.format(count=human_number(plan.moved_copies)))
    if plan.burst_count:
        bursts = ngettext(
            "{count} burst shot you set aside will be moved to the quarantine.",
            "{count} burst shots you set aside will be moved to the quarantine.",
            plan.burst_count,
        )
        runtime.output.info(bursts.format(count=human_number(plan.burst_count)))
    if plan.orphans:
        orphans = ngettext(
            "{count} orphan sidecar (.xmp, .aae, .thm) will be moved to the "
            "quarantine.",
            "{count} orphan sidecars (.xmp, .aae, .thm) will be moved to the "
            "quarantine.",
            len(plan.orphans),
        )
        runtime.output.info(orphans.format(count=human_number(len(plan.orphans))))
    return runtime.output.confirm(
        question.format(
            count=human_number(plan.removable_count),
            size=human_size(plan.reclaimable),
            near=human_number(plan.near_count),
            broken=human_number(len(plan.broken)),
        ),
    )
