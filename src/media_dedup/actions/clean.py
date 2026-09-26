"""Execute a plan: delete exact copies, quarantine near ones, broken files, orphans."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING

from media_dedup.actions.journaled import JournaledChanges
from media_dedup.actions.outcome import Incident, Outcome, Tally
from media_dedup.actions.verify import (
    change_blocker,
    near_blocker,
    orphan_blocker,
    removal_blocker,
)
from media_dedup.constants import ActionKind, BrokenReason, MediaKind
from media_dedup.i18n import _
from media_dedup.scan.progress import Step

if TYPE_CHECKING:
    from collections.abc import Callable

    from media_dedup.actions.journaled import CleanContext
    from media_dedup.plan.models import CleanPlan, KeepDecision
    from media_dedup.plan.similar_models import NearDecision
    from media_dedup.scan.models import BrokenFile, MediaFile

_LOGGER = logging.getLogger(__name__)


class CleanExecutor:
    """Acts file by file; a problem on one file never stops the others."""

    def __init__(self, context: CleanContext) -> None:
        """Prepare a run.

        Args:
            context: Journal, path mapper, quarantine folder and progress sink.
        """
        self._context = context
        self._tally = Tally()
        self._changes = JournaledChanges(context, self._tally)

    def run(self, plan: CleanPlan) -> Outcome:
        """Execute every action of the plan.

        Args:
            plan: What to clean.

        Returns:
            What was done, skipped and why.
        """
        step = Step(
            _("Cleaning"),
            _(
                "Each copy is compared again with the kept one before deletion; "
                "unreadable files go to the quarantine."
            ),
        )
        total = plan.removable_count + plan.near_count + len(plan.broken)
        self._context.progress.start(step, total + len(plan.orphans))
        for decision in plan.decisions:
            for file in decision.removable:
                self._guarded(file, partial(self._delete_copy, decision, file))
        for near in plan.near:
            for file in near.removable:
                self._guarded(file, partial(self._quarantine_near, near, file))
        for item in plan.broken:
            self._guarded(item.file, partial(self._handle_broken, item))
        # Last: a sidecar is an orphan only once the files it belongs to are gone.
        for file in plan.orphans:
            self._guarded(file, partial(self._quarantine_orphan, file))
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

        A copy of another file than a media (asked for with `--ext`) is moved to the
        quarantine instead: where a document lies may matter to a program.

        Args:
            decision: The group decision, holding the keeper.
            file: Copy to delete.
        """
        blocker = removal_blocker(decision.keeper.path, file.path, decision.size)
        if blocker is not None:
            self._tally.skipped.append(Incident(file.path, blocker))
            return
        if file.kind is MediaKind.OTHER:
            keeper = decision.keeper.path
            self._changes.quarantine(file, ActionKind.QUARANTINE_DUPLICATE, keeper)
            return
        entry = self._changes.entry(file, ActionKind.DELETE_DUPLICATE).model_copy(
            update={"sha256": decision.digest, "keeper": str(decision.keeper.path)},
        )
        self._changes.act(entry, file.path.unlink)

    def _quarantine_near(self, decision: NearDecision, file: MediaFile) -> None:
        """Move one near duplicate to the quarantine, where `undo` finds it again.

        Args:
            decision: The near-duplicate decision, holding the kept picture.
            file: Copy to move.
        """
        blocker = near_blocker(decision.keeper.path, file)
        if blocker is not None:
            self._tally.skipped.append(Incident(file.path, blocker))
            return
        self._changes.quarantine(file, ActionKind.QUARANTINE_NEAR, decision.keeper.path)

    def _handle_broken(self, item: BrokenFile) -> None:
        """Delete an empty file, or move an unreadable one to the quarantine.

        Args:
            item: The broken file.
        """
        blocker = change_blocker(item.file)
        if blocker is not None:
            self._tally.skipped.append(Incident(item.file.path, blocker))
            return
        if item.reason is BrokenReason.EMPTY:
            entry = self._changes.entry(item.file, ActionKind.DELETE_EMPTY)
            self._changes.act(entry, item.file.path.unlink)
            return
        self._changes.quarantine(item.file, ActionKind.QUARANTINE)

    def _quarantine_orphan(self, sidecar: MediaFile) -> None:
        """Move an orphan sidecar to the quarantine, where `undo` finds it again.

        Args:
            sidecar: The sidecar, as audited.
        """
        blocker = orphan_blocker(sidecar)
        if blocker is not None:
            self._tally.skipped.append(Incident(sidecar.path, blocker))
            return
        self._changes.quarantine(sidecar, ActionKind.QUARANTINE_SIDECAR)
