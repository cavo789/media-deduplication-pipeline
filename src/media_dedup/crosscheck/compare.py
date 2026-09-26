"""Compare two duplicate finders group by group, explaining the expected differences.

Czkawka may group files media-dedup deliberately leaves out: another extension, an
excluded folder, a broken file. Those are set aside and counted as *explained*; what
remains must match group for group, or it is a real disagreement to look at.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from media_dedup.paths.host_paths import is_within
from media_dedup.scan.filters import media_kind

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime
    from pathlib import Path

    from media_dedup.crosscheck.czkawka import Group
    from media_dedup.scan.filters import ScanFilters


class OutsideReason(StrEnum):
    """Why media-dedup does not analyse a file Czkawka grouped."""

    NOT_MOUNTED = "not-mounted"
    EXTENSION = "extension"
    EXCLUDED = "excluded"
    BROKEN = "broken"


@dataclass(frozen=True, slots=True)
class AnalysedScope:
    """What media-dedup analysed in this run."""

    roots: tuple[Path, ...]
    filters: ScanFilters
    broken: frozenset[Path]

    def outside(self, path: Path) -> OutsideReason | None:
        """Tell why a file is out of media-dedup's scope, if it is.

        Args:
            path: A container path reported by Czkawka.

        Returns:
            The reason, or None when media-dedup analysed the file.
        """
        if not any(is_within(path, root) for root in self.roots):
            return OutsideReason.NOT_MOUNTED
        if media_kind(path) is None or not self.filters.accepts(path):
            return OutsideReason.EXTENSION
        if any(self.filters.skips_dir(folder) for folder in path.parents):
            return OutsideReason.EXCLUDED
        if path in self.broken:
            return OutsideReason.BROKEN
        return None


@dataclass(frozen=True, slots=True)
class CrossCheckResult:
    """Where the two tools agree, where they differ, and why."""

    ours: tuple[Group, ...]
    theirs: tuple[Group, ...]
    only_ours: tuple[Group, ...]
    only_theirs: tuple[Group, ...]
    outside: Mapping[OutsideReason, int]
    results_date: datetime | None = None

    @property
    def agrees(self) -> bool:
        """Tell whether every group in scope is the same in both tools.

        Returns:
            True when no group is found by one tool only.
        """
        return not self.only_ours and not self.only_theirs

    @property
    def copies(self) -> int:
        """Extra copies media-dedup found (files per group, minus the one kept).

        Returns:
            The count.
        """
        return sum(len(group) - 1 for group in self.ours)


def compare(
    ours: Iterable[Group],
    theirs: Iterable[Group],
    scope: AnalysedScope,
) -> CrossCheckResult:
    """Compare media-dedup's groups with Czkawka's, out-of-scope files set aside.

    Args:
        ours: media-dedup's duplicate groups.
        theirs: Czkawka's duplicate groups.
        scope: What media-dedup analysed.

    Returns:
        The comparison.
    """
    outside: Counter[OutsideReason] = Counter()
    in_scope: list[Group] = []
    for group in theirs:
        kept = frozenset(
            path for path in group if not _count_outside(path, scope, outside)
        )
        if len(kept) > 1:
            in_scope.append(kept)
    ours_set, theirs_set = frozenset(ours), frozenset(in_scope)
    return CrossCheckResult(
        ours=tuple(ours_set),
        theirs=tuple(theirs_set),
        only_ours=_sorted(ours_set - theirs_set),
        only_theirs=_sorted(theirs_set - ours_set),
        outside=dict(outside),
    )


def _count_outside(
    path: Path, scope: AnalysedScope, counts: Counter[OutsideReason]
) -> bool:
    """Tell whether a file is out of scope, counting it by reason when it is.

    Args:
        path: A file Czkawka grouped.
        scope: What media-dedup analysed.
        counts: Out-of-scope files by reason, updated.

    Returns:
        True when the file is set aside.
    """
    reason = scope.outside(path)
    if reason is not None:
        counts[reason] += 1
    return reason is not None


def _sorted(groups: Iterable[Group]) -> tuple[Group, ...]:
    """Order groups by their first path, for a stable display.

    Args:
        groups: Groups of paths.

    Returns:
        The groups, sorted.
    """
    return tuple(sorted(groups, key=lambda group: sorted(map(str, group))))
