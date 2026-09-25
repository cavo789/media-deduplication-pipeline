"""Turn scan findings into the plan `clean` executes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.plan.models import CleanPlan

if TYPE_CHECKING:
    from collections.abc import Sequence

    from media_dedup.plan.keeper import KeepPolicy
    from media_dedup.scan.models import BrokenFile, DuplicateGroup


def build_plan(
    groups: Sequence[DuplicateGroup],
    broken: Sequence[BrokenFile],
    policy: KeepPolicy,
) -> CleanPlan:
    """Apply the keep policy to every group and set protected broken files aside.

    Args:
        groups: Exact duplicate groups (healthy files only).
        broken: Broken files.
        policy: Preferred and protected folders.

    Returns:
        The plan; groups where nothing is removable are dropped.
    """
    decisions = tuple(
        decision
        for decision in (policy.decide(group) for group in groups)
        if decision.removable
    )
    return CleanPlan(
        decisions=decisions,
        broken=tuple(item for item in broken if not policy.is_protected(item.file)),
        protected_broken=tuple(
            item for item in broken if policy.is_protected(item.file)
        ),
    )
