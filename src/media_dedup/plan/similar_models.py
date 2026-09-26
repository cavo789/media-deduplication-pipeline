"""Pictures that look alike without being identical: near duplicates and bursts."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from media_dedup.scan.models import MediaFile, VisualFacts


@dataclass(frozen=True, slots=True)
class NearDecision:
    """One picture saved several times: the best version kept, the others removable.

    Removable copies are resized, recompressed or stripped versions of the keeper. They
    are not identical to it: `clean --tier near` moves them to the quarantine, never
    deletes them.
    """

    keeper: MediaFile
    removable: tuple[MediaFile, ...]
    protected: tuple[MediaFile, ...] = ()

    @property
    def reclaimable(self) -> int:
        """Bytes freed once the removable copies are purged from the quarantine.

        Returns:
            Their total size.
        """
        return sum(file.size for file in self.removable)


@dataclass(frozen=True, slots=True)
class BurstSeries:
    """Shots of one burst: curation, not duplication — never cleaned."""

    shots: tuple[MediaFile, ...]
    best: MediaFile


@dataclass(frozen=True, slots=True)
class SimilarFindings:
    """Near duplicates, burst series, and what each image looks like."""

    near: tuple[NearDecision, ...] = ()
    bursts: tuple[BurstSeries, ...] = ()
    visuals: Mapping[Path, VisualFacts] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def near_count(self) -> int:
        """Number of near-duplicate copies `clean --tier near` would move.

        Returns:
            The count.
        """
        return sum(len(decision.removable) for decision in self.near)
