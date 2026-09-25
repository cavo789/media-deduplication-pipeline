"""Reverse a clean run: rebuild deleted copies from their keeper, unquarantine."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.actions.journal import latest_states
from media_dedup.actions.outcome import Incident, Outcome, Tally
from media_dedup.constants import ActionKind, Phase, Status
from media_dedup.i18n import _
from media_dedup.scan.hashing import full_digest
from media_dedup.scan.progress import Step

if TYPE_CHECKING:
    from media_dedup.actions.journal import JournalEntry, JournalWriter
    from media_dedup.scan.progress import ProgressSink

_LOGGER = logging.getLogger(__name__)


class UndoExecutor:
    """Restores every file of a run that is not restored yet, newest action first."""

    def __init__(self, journal: JournalWriter, progress: ProgressSink) -> None:
        """Prepare the undo of one run.

        Args:
            journal: The run's journal, opened for appending `undo` entries.
            progress: Where to report progress.
        """
        self._journal = journal
        self._progress = progress
        self._tally = Tally()

    def run(self, entries: list[JournalEntry]) -> Outcome:
        """Restore the files acted upon by the run.

        Args:
            entries: Every entry of the run's journal.

        Returns:
            What was restored, skipped and why.
        """
        restored = {
            seq
            for seq, entry in latest_states(entries, Phase.UNDO).items()
            if entry.status is Status.DONE
        }
        todo = [
            entry
            for seq, entry in sorted(latest_states(entries, Phase.CLEAN).items())
            if seq not in restored
        ]
        step = Step(
            _("Restoring"),
            _(
                "Rebuilds each deleted copy from the kept one, and brings quarantined "
                "files back."
            ),
        )
        self._progress.start(step, len(todo))
        for entry in reversed(todo):
            try:
                self._restore(entry)
            except OSError as exc:
                _LOGGER.debug("Restore failed on %s", entry.path, exc_info=True)
                self._tally.failed.append(Incident(Path(entry.path), str(exc)))
            finally:
                self._progress.advance()
        self._progress.stop()
        return self._tally.freeze()

    def _restore(self, entry: JournalEntry) -> None:
        """Restore one file, journaling the undo like any other action.

        Args:
            entry: Latest `clean` state of the action to reverse.
        """
        path = Path(entry.path)
        if path.exists():
            # Never overwrite: the file is back already, or the action never happened.
            self._tally.skipped.append(Incident(path, _("the file already exists")))
            return
        source = _source_of(entry)
        if source is not None and not source.is_file():
            self._tally.skipped.append(
                Incident(path, _("its copy {path} is gone").format(path=source)),
            )
            return
        pending = entry.model_copy(
            update={"phase": Phase.UNDO, "status": Status.PENDING}
        )
        self._journal.record(pending)
        _rebuild(entry, source)
        os.utime(path, ns=(entry.mtime_ns, entry.mtime_ns))
        self._journal.record(pending.as_done())
        self._tally.done += 1
        self._tally.bytes_done += entry.size


def _source_of(entry: JournalEntry) -> Path | None:
    """Return the file an action can be rebuilt from.

    Args:
        entry: A `clean` entry.

    Returns:
        The keeper of a deleted duplicate, the quarantined copy, or None for an
        empty file (recreated from nothing).
    """
    match entry.action:
        case ActionKind.DELETE_DUPLICATE:
            return Path(entry.keeper) if entry.keeper else None
        case ActionKind.QUARANTINE:
            return Path(entry.quarantine) if entry.quarantine else None
        case ActionKind.DELETE_EMPTY:
            return None


def _rebuild(entry: JournalEntry, source: Path | None) -> None:
    """Recreate the file of `entry` and prove its content is the original one.

    Args:
        entry: The `clean` entry being reversed.
        source: Where to copy the content from (None for an empty file).

    Raises:
        OSError: The rebuilt content does not match the journaled digest.
    """
    path = Path(entry.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if source is None:
        path.touch()
        return
    shutil.copy2(source, path)
    if entry.sha256 is not None and full_digest(path) != entry.sha256:
        path.unlink()
        raise OSError(_("the restored copy does not match the original"))
    if entry.action is ActionKind.QUARANTINE:
        source.unlink()
