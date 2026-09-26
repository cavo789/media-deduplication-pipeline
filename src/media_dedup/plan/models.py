"""The plan `clean` executes, as immutable value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from media_dedup.constants import KeepReason
    from media_dedup.scan.models import BrokenFile, MediaFile


@dataclass(frozen=True, slots=True)
class KeepDecision:
    """One duplicate group: the copy that stays and the copies that go."""

    digest: str
    size: int
    keeper: MediaFile
    removable: tuple[MediaFile, ...]
    protected: tuple[MediaFile, ...] = ()
    reason: KeepReason | None = None

    @property
    def reclaimable(self) -> int:
        """Bytes freed by removing the removable copies.

        Returns:
            Size times the number of removable copies.
        """
        return self.size * len(self.removable)


@dataclass(frozen=True, slots=True)
class CleanPlan:
    """Everything `clean` would do, computed by `audit`."""

    decisions: tuple[KeepDecision, ...]
    broken: tuple[BrokenFile, ...]
    protected_broken: tuple[BrokenFile, ...] = ()

    @property
    def removable_count(self) -> int:
        """Number of duplicate copies `clean` would delete.

        Returns:
            The count.
        """
        return sum(len(decision.removable) for decision in self.decisions)

    @property
    def reclaimable(self) -> int:
        """Bytes freed by deleting the duplicate copies.

        Returns:
            The byte count.
        """
        return sum(decision.reclaimable for decision in self.decisions)

    @property
    def broken_size(self) -> int:
        """Bytes of broken files `clean` would quarantine or delete.

        Returns:
            The byte count.
        """
        return sum(item.file.size for item in self.broken)

    @property
    def is_empty(self) -> bool:
        """Tell whether there is nothing to clean.

        Returns:
            True when no duplicate copy and no broken file are actionable.
        """
        return not self.removable_count and not self.broken


@dataclass(frozen=True, slots=True)
class AuditFindings:
    """Result of an audit: how much was scanned, and the plan derived from it."""

    files_scanned: int
    roots: tuple[Path, ...]
    plan: CleanPlan
    seconds: float = 0.0
    folder_files: Mapping[Path, int] = field(
        default_factory=lambda: MappingProxyType({})
    )
