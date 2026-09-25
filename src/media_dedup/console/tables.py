"""Console summaries of an audit and of a clean or undo outcome."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from rich.table import Table

from media_dedup.console.formatting import human_size
from media_dedup.i18n import _

if TYPE_CHECKING:
    from media_dedup.actions.outcome import Outcome
    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.models import AuditFindings

_TOP_PAIRS = 10


def findings_table(findings: AuditFindings) -> Table:
    """Headline numbers of an audit.

    Args:
        findings: The audit findings.

    Returns:
        A two-column table.
    """
    plan = findings.plan
    table = Table(title=_("Audit summary"), show_header=False, title_justify="left")
    table.add_column(style="bold")
    table.add_column(justify="right")
    table.add_row(_("Media files scanned"), str(findings.files_scanned))
    table.add_row(_("Duplicate groups"), str(len(plan.decisions)))
    table.add_row(_("Copies that can be deleted"), str(plan.removable_count))
    table.add_row(_("Space that can be freed"), human_size(plan.reclaimable))
    table.add_row(_("Broken files"), str(len(plan.broken)))
    if plan.protected_broken:
        table.add_row(
            _("Broken files in protected folders"), str(len(plan.protected_broken))
        )
    return table


def pairs_table(findings: AuditFindings, mapper: HostPathMapper) -> Table | None:
    """The folder pairs sharing the most identical files — the quickest sanity check.

    Args:
        findings: The audit findings.
        mapper: Host/container path translator.

    Returns:
        The top pairs, or None when there is no duplicate.
    """
    counts: Counter[tuple[str, str]] = Counter()
    for decision in findings.plan.decisions:
        kept_in = mapper.to_host(decision.keeper.path.parent)
        for file in decision.removable:
            counts[kept_in, mapper.to_host(file.path.parent)] += 1
    if not counts:
        return None
    table = Table(title=_("Folders sharing identical files"), title_justify="left")
    table.add_column(_("Kept in"), style="green", overflow="fold")
    table.add_column(_("Deleted from"), style="red", overflow="fold")
    table.add_column(_("Files"), justify="right")
    for (kept_in, removed_from), count in counts.most_common(_TOP_PAIRS):
        table.add_row(kept_in, removed_from, str(count))
    return table


def outcome_table(outcome: Outcome, title: str) -> Table:
    """What a clean or an undo did.

    Args:
        outcome: The outcome.
        title: Translated table title.

    Returns:
        A two-column table.
    """
    table = Table(title=title, show_header=False, title_justify="left")
    table.add_column(style="bold")
    table.add_column(justify="right")
    table.add_row(_("Files processed"), str(outcome.done))
    table.add_row(_("Size"), human_size(outcome.bytes_done))
    if outcome.quarantined:
        table.add_row(_("Moved to the quarantine"), str(outcome.quarantined))
    table.add_row(_("Skipped (left untouched)"), str(len(outcome.skipped)))
    table.add_row(_("Failed"), str(len(outcome.failed)))
    return table
