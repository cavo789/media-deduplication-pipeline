"""Console summaries of an audit and of a clean or undo outcome."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markup import escape
from rich.table import Table
from rich.text import Text

from media_dedup.console.formatting import human_duration, human_number, human_size
from media_dedup.i18n import _, ngettext
from media_dedup.plan.pairs import folder_pairs

if TYPE_CHECKING:
    from media_dedup.actions.outcome import Outcome
    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.models import AuditFindings
    from media_dedup.plan.pairs import FolderPair

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
    table.add_row(_("Media files scanned"), human_number(findings.files_scanned))
    table.add_row(_("Groups of identical files"), human_number(len(plan.decisions)))
    table.add_row(
        _("Extra copies that can be deleted"), human_number(plan.removable_count)
    )
    table.add_row(_("Space that can be freed"), human_size(plan.reclaimable))
    table.add_row(
        _("Broken files (empty or unreadable)"), human_number(len(plan.broken))
    )
    if plan.orphans:
        table.add_row(
            _("Orphan sidecars (.xmp, .aae, .thm) to move"),
            human_number(len(plan.orphans)),
        )
    similar = findings.similar
    if similar.near_count:
        table.add_row(
            _("Near duplicates (moved only with --tier near)"),
            human_number(similar.near_count),
        )
    if similar.bursts:
        table.add_row(
            _("Burst series (listed, never cleaned)"), human_number(len(similar.bursts))
        )
    if plan.protected_broken:
        table.add_row(
            _("Broken files in protected folders"),
            human_number(len(plan.protected_broken)),
        )
    table.add_row(_("Duration"), human_duration(findings.seconds))
    return table


def folder_pairs_view(findings: AuditFindings, mapper: HostPathMapper) -> Table | None:
    """The folder pairs freeing the most space — the quickest sanity check.

    Each pair is one plain sentence: how many files, where they are kept, where the
    copies go, and how much space it frees.

    Args:
        findings: The audit findings.
        mapper: Host/container path translator.

    Returns:
        The top pairs, or None when there is no duplicate.
    """
    pairs = folder_pairs(findings.plan.decisions, findings.folder_files)[:_TOP_PAIRS]
    if not pairs:
        return None
    table = Table.grid(padding=(0, 1))
    table.title = _("Folders sharing identical files")
    table.title_justify = "left"
    table.add_column()
    table.add_column(overflow="fold")
    for pair in pairs:
        table.add_row("•", _pair_sentence(pair, mapper))
    return table


def _pair_sentence(pair: FolderPair, mapper: HostPathMapper) -> Text:
    """Describe one folder pair in a sentence.

    Args:
        pair: The two folders, the number of copies to delete and their size.
        mapper: Host/container path translator.

    Returns:
        The styled sentence.
    """
    kept_in = mapper.to_host(pair.kept_in)
    removed_from = mapper.to_host(pair.removed_from)
    values = {
        "count": human_number(pair.files),
        "kept": f"[green]{escape(kept_in)}[/green]",
        "removed": f"[red]{escape(removed_from)}[/red]",
        "size": f"[bold]{human_size(pair.size)}[/bold]",
    }
    if kept_in == removed_from:
        sentence = ngettext(
            "{count} file is present several times in {kept}: one copy is kept"
            " ({size} freed).",
            "{count} files are present several times in {kept}: one copy of each is"
            " kept ({size} freed).",
            pair.files,
        )
    else:
        sentence = ngettext(
            "{count} file is both in {kept} (kept) and in {removed} (deleted),"
            " {size} freed.",
            "{count} files are both in {kept} (kept) and in {removed} (deleted),"
            " {size} freed.",
            pair.files,
        )
    if pair.complete:
        sentence += " " + _(
            "{removed} holds nothing else: it is entirely a copy of {kept}."
        )
    return Text.from_markup(sentence.format(**values))


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
    table.add_row(_("Files processed"), human_number(outcome.done))
    table.add_row(_("Size"), human_size(outcome.bytes_done))
    if outcome.quarantined:
        table.add_row(_("Moved to the quarantine"), human_number(outcome.quarantined))
    table.add_row(_("Skipped (left untouched)"), human_number(len(outcome.skipped)))
    table.add_row(_("Failed"), human_number(len(outcome.failed)))
    table.add_row(_("Duration"), human_duration(outcome.seconds))
    return table
