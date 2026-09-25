"""Choose which copy of a duplicate group is kept — deterministically."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.paths.host_paths import is_within
from media_dedup.plan.copy_names import looks_like_copy
from media_dedup.plan.models import KeepDecision

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.scan.models import DuplicateGroup, MediaFile

type _SortKey = tuple[bool, int, bool, int, int, str]


@dataclass(frozen=True, slots=True)
class KeepPolicy:
    """Container paths of the preferred (ordered) and protected folders."""

    preferred: tuple[Path, ...] = ()
    protected: tuple[Path, ...] = ()

    def is_protected(self, file: MediaFile) -> bool:
        """Tell whether a file lies in a protected folder.

        Args:
            file: Candidate file.

        Returns:
            True when it must never be modified.
        """
        return any(is_within(file.path, folder) for folder in self.protected)

    def rank(self, file: MediaFile) -> _SortKey:
        """Sort key: the smallest key is the copy to keep.

        Order: protected folder, preferred folder (in the configured order), a name
        that does not look like a copy, the oldest modification time, the shortest
        path, then alphabetical order (case-insensitive) as the final tie-breaker.

        Args:
            file: Candidate file.

        Returns:
            Its sort key.
        """
        preference = next(
            (
                index
                for index, folder in enumerate(self.preferred)
                if is_within(file.path, folder)
            ),
            len(self.preferred),
        )
        return (
            not self.is_protected(file),
            preference,
            looks_like_copy(file.path),
            file.mtime_ns,
            len(file.path.parts),
            str(file.path).casefold(),
        )

    def decide(self, group: DuplicateGroup) -> KeepDecision:
        """Split a duplicate group into the keeper, removable and protected copies.

        Args:
            group: Identical files.

        Returns:
            The decision; protected copies other than the keeper are never removable.
        """
        ordered = sorted(group.files, key=self.rank)
        keeper, others = ordered[0], ordered[1:]
        return KeepDecision(
            digest=group.digest,
            size=group.size,
            keeper=keeper,
            removable=tuple(file for file in others if not self.is_protected(file)),
            protected=tuple(file for file in others if self.is_protected(file)),
        )
