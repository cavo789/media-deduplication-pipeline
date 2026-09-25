"""The undo use case: pick a run, check the mounts, restore its files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.actions.journal import JournalWriter, journal_file, read_journal
from media_dedup.actions.runs import list_run_ids
from media_dedup.actions.undo import UndoExecutor
from media_dedup.errors import JournalError, MountError
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind

if TYPE_CHECKING:
    from media_dedup.actions.outcome import Outcome
    from media_dedup.scan.progress import ProgressSink
    from media_dedup.services.runtime import Runtime


def resolve_run_id(runtime: Runtime, run_id: str | None) -> str:
    """Return the requested run, or the latest one.

    Args:
        runtime: Settings, mount points and output.
        run_id: Explicit run identifier, or None for the latest.

    Returns:
        An existing run identifier.

    Raises:
        MountError: The journal is not mounted.
        JournalError: No run exists, or the requested one is unknown.
    """
    if not runtime.persistent(MountKind.JOURNAL):
        raise MountError(
            _("No journal mount: there is nothing to undo."),
            _('Mount the same journal folder as for clean: -v "<folder>:/journal".'),
        )
    runs = list_run_ids(runtime.locations.journal_dir)
    if not runs:
        raise JournalError(_("No clean run found in the journal."))
    if run_id is None:
        return runs[0]
    if run_id not in runs:
        raise JournalError(
            _("Unknown run {run_id}.").format(run_id=run_id),
            _("Run 'media-dedup history' to list the runs."),
        )
    return run_id


def undo_run(runtime: Runtime, run_id: str, progress: ProgressSink) -> Outcome:
    """Restore every file of a run.

    Args:
        runtime: Settings, mount points and output.
        run_id: Run to reverse.
        progress: Where to report progress.

    Returns:
        What was restored, skipped and why.
    """
    file = journal_file(runtime.locations.journal_dir, run_id)
    entries = read_journal(file)
    with JournalWriter.open(file) as journal:
        return UndoExecutor(journal, progress).run(entries)
