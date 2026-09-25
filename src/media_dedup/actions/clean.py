"""Execute a clean plan: delete duplicate copies, delete or quarantine broken files."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from media_dedup.actions.journal import JournalEntry
from media_dedup.actions.outcome import Incident, Outcome, Tally
from media_dedup.actions.verify import removal_blocker
from media_dedup.constants import ActionKind, BrokenReason, Phase, Status
from media_dedup.i18n import _
from media_dedup.scan.hashing import full_digest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from media_dedup.actions.journal import JournalWriter
    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.models import CleanPlan, KeepDecision
    from media_dedup.scan.models import BrokenFile, MediaFile
    from media_dedup.scan.progress import ProgressSink

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CleanContext:
    """Where and how a clean run acts."""

    journal: JournalWriter
    mapper: HostPathMapper
    quarantine_run_dir: Path
    progress: ProgressSink


class CleanExecutor:
    """Acts file by file; a problem on one file never stops the others."""

    def __init__(self, context: CleanContext) -> None:
        """Prepare a run.

        Args:
            context: Journal, path mapper, quarantine folder and progress sink.
        """
        self._context = context
        self._tally = Tally()
        self._seq = 0

    def run(self, plan: CleanPlan) -> Outcome:
        """Execute every action of the plan.

        Args:
            plan: What to clean.

        Returns:
            What was done, skipped and why.
        """
        self._context.progress.start(
            _("Cleaning"), plan.removable_count + len(plan.broken)
        )
        for decision in plan.decisions:
            for file in decision.removable:
                self._guarded(file, partial(self._delete_copy, decision, file))
        for item in plan.broken:
            self._guarded(item.file, partial(self._handle_broken, item))
        self._context.progress.stop()
        return self._tally.freeze()

    def _guarded(self, file: MediaFile, action: Callable[[], object]) -> None:
        """Run one action, turning an OS error into a recorded failure.

        Args:
            file: File the action is about.
            action: Zero-argument callable performing the action.
        """
        try:
            action()
        except OSError as exc:
            _LOGGER.debug("Action failed on %s", file.path, exc_info=True)
            self._tally.failed.append(Incident(file.path, exc.strerror or str(exc)))
        finally:
            self._context.progress.advance()

    def _delete_copy(self, decision: KeepDecision, file: MediaFile) -> None:
        """Delete one duplicate copy after a byte-for-byte check against the keeper.

        Args:
            decision: The group decision, holding the keeper.
            file: Copy to delete.
        """
        blocker = removal_blocker(decision.keeper.path, file.path, decision.size)
        if blocker is not None:
            self._tally.skipped.append(Incident(file.path, blocker))
            return
        entry = self._entry(file, ActionKind.DELETE_DUPLICATE).model_copy(
            update={"sha256": decision.digest, "keeper": str(decision.keeper.path)},
        )
        self._act(entry, file.path.unlink)

    def _handle_broken(self, item: BrokenFile) -> None:
        """Delete an empty file, or move an unreadable one to the quarantine.

        Args:
            item: The broken file.
        """
        path = item.file.path
        if not path.is_file() or path.stat().st_size != item.file.size:
            self._tally.skipped.append(
                Incident(path, _("a file changed since the audit"))
            )
            return
        if item.reason is BrokenReason.EMPTY:
            self._act(self._entry(item.file, ActionKind.DELETE_EMPTY), path.unlink)
            return
        target = self._context.quarantine_run_dir / self._context.mapper.relative(path)
        entry = self._entry(item.file, ActionKind.QUARANTINE).model_copy(
            update={"quarantine": str(target), "sha256": full_digest(path)},
        )
        self._act(entry, lambda: _move_verified(path, target))
        self._tally.quarantined += 1

    def _entry(self, file: MediaFile, action: ActionKind) -> JournalEntry:
        """Build the `pending` journal entry of an action.

        Args:
            file: File acted upon.
            action: What is about to happen.

        Returns:
            The entry, with the next sequence number.
        """
        self._seq += 1
        return JournalEntry(
            seq=self._seq,
            phase=Phase.CLEAN,
            status=Status.PENDING,
            action=action,
            path=str(file.path),
            host_path=self._context.mapper.to_host(file.path),
            size=file.size,
            mtime_ns=file.mtime_ns,
        )

    def _act(self, entry: JournalEntry, action: Callable[[], object]) -> None:
        """Journal `pending`, act, then journal `done`.

        Args:
            entry: The pending entry.
            action: Zero-argument callable performing the change.
        """
        self._context.journal.record(entry)
        action()
        self._context.journal.record(entry.as_done())
        self._tally.done += 1
        self._tally.bytes_done += entry.size


def _move_verified(source: Path, target: Path) -> None:
    """Copy `source` to `target`, prove the copy identical, then delete `source`.

    Works across disks, unlike a rename.

    Args:
        source: File to move.
        target: Destination.

    Raises:
        OSError: The copy differs from the original (the original is kept).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if full_digest(source) != full_digest(target):
        target.unlink()
        raise OSError(_("the quarantine copy differs from the original"))
    source.unlink()
