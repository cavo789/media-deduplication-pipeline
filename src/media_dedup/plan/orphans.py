"""The sidecars a plan may leave orphan, and so move: `CleanPlan.orphans`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from media_dedup.plan.keeper import KeepPolicy
    from media_dedup.scan.sidecars import Sidecar


def sidecars_in_scope(
    found: Iterable[Sidecar], policy: KeepPolicy, *, alone: bool
) -> tuple[Sidecar, ...]:
    """Keep the sidecars `clean` may move, sorted by path.

    Protected folders are never modified, and a sidecar listed twice (nested mounts)
    is kept once. With an extension filter, the audit looks at some files only:
    sidecars already alone before the clean are then left where they are.

    Args:
        found: The sidecars the walk listed.
        policy: Protected folders.
        alone: Keep the sidecars already without their files.

    Returns:
        The sidecars in scope.
    """
    by_path = {sidecar.file.path: sidecar for sidecar in found}
    return tuple(
        sidecar
        for sidecar in (by_path[path] for path in sorted(by_path))
        if not policy.is_protected(sidecar.file) and (alone or sidecar.companions)
    )
