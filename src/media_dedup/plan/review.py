"""Apply the folder-pair decisions of a review (the report's controls) to the plan.

A folder pair holds the copies deleted from `removed_from` because an identical file is
kept in `kept_in`. A review can swap a pair (keep the copies of `removed_from`, delete
the one of `kept_in`) or skip it (delete nothing of the pair). Several decisions may
touch one group: a copy some decision keeps is never deleted.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING

from media_dedup.constants import KeepReason

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from media_dedup.plan.keeper import KeepPolicy
    from media_dedup.plan.models import CleanPlan, KeepDecision

type _Choices = Mapping[tuple[Path, Path], PairAction]


class PairAction(StrEnum):
    """What a review decided for a folder pair (no decision: as planned)."""

    SWAP = "swap"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class PairChoice:
    """The decision on one folder pair, in container paths."""

    kept_in: Path
    removed_from: Path
    action: PairAction


def apply_choices(
    plan: CleanPlan, choices: Iterable[PairChoice], policy: KeepPolicy
) -> CleanPlan:
    """Rewrite the exact duplicate groups the decisions touch.

    Args:
        plan: The plan of the audit.
        choices: The decisions, checked against the audit (see `services.review`).
        policy: Ranks the copies a swap keeps, to choose the new keeper.

    Returns:
        The plan; groups left with nothing to delete are dropped.
    """
    by_pair = {(c.kept_in, c.removed_from): c.action for c in choices}
    decisions = (_reviewed(decision, by_pair, policy) for decision in plan.decisions)
    return replace(plan, decisions=tuple(d for d in decisions if d.removable))


def _reviewed(
    decision: KeepDecision, choices: _Choices, policy: KeepPolicy
) -> KeepDecision:
    """Apply the decisions of the pairs a group belongs to.

    Args:
        decision: The group, as the keep policy decided it.
        choices: Decisions by (kept folder, folder losing the copy).
        policy: Ranks the copies kept, when the keeper is swapped away.

    Returns:
        The group: swapped (new keeper, the old one deleted), spared, or unchanged.
    """
    folder = decision.keeper.path.parent
    actions = [
        (file, choices.get((folder, file.path.parent))) for file in decision.removable
    ]
    kept = tuple(file for file, action in actions if action is not None)
    if not kept:
        return decision
    removable = tuple(file for file, action in actions if action is None)
    if PairAction.SWAP not in {action for _file, action in actions}:
        return replace(decision, removable=removable, spared=(*decision.spared, *kept))
    keeper, *spared = sorted(kept, key=policy.rank)
    return replace(
        decision,
        keeper=keeper,
        removable=(*removable, decision.keeper),
        spared=(*decision.spared, *spared),
        reason=KeepReason.REVIEWED,
    )
