"""Translate audit findings and a clean outcome into the report's view model."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.constants import THUMBNAILS_DIR_NAME, MediaKind, Sizes
from media_dedup.report.summary import ReportSummary
from media_dedup.report.thumbnails import ThumbnailJob
from media_dedup.report.views import (
    BrokenSection,
    BrokenView,
    FolderPairView,
    GroupView,
    IncidentsSection,
    IncidentView,
    ReportView,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from media_dedup.actions.outcome import Incident
    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.models import KeepDecision
    from media_dedup.report.views import ReportRecord
    from media_dedup.scan.models import BrokenFile, MediaFile

_PREVIEWABLE = frozenset({MediaKind.IMAGE})
_THUMBNAIL_NAME_LENGTH = 20


def thumbnail_name(file: MediaFile) -> str:
    """Return a stable, collision-free preview file name for `file`.

    Args:
        file: The media file.

    Returns:
        A relative path such as `thumbs/0f3a....jpg`.
    """
    digest = hashlib.sha256(str(file.path).encode()).hexdigest()[
        :_THUMBNAIL_NAME_LENGTH
    ]
    return f"{THUMBNAILS_DIR_NAME}/{digest}.jpg"


@dataclass(frozen=True, slots=True)
class ReportBuilder:
    """Builds the view of one report folder."""

    mapper: HostPathMapper
    folder: Path

    def thumbnail_jobs(self, record: ReportRecord) -> list[ThumbnailJob]:
        """List the previews the report shows.

        Args:
            record: What the report is written from.

        Returns:
            One job per previewable keeper or broken image.
        """
        plan = record.findings.plan
        shown = [d.keeper for d in plan.decisions[: Sizes.MAX_GROUPS_IN_REPORT]]
        files = [*shown, *(item.file for item in plan.broken)]
        return [
            ThumbnailJob(file.path, self.folder / thumbnail_name(file))
            for file in files
            if file.kind in _PREVIEWABLE
        ]

    def summary(self, record: ReportRecord) -> ReportSummary:
        """Compute the headline numbers.

        Args:
            record: What the report is written from.

        Returns:
            The summary saved as `summary.json`.
        """
        plan = record.findings.plan
        return ReportSummary(
            folder=self.folder.name,
            kind=record.kind,
            files_scanned=record.findings.files_scanned,
            duplicate_groups=len(plan.decisions),
            duplicate_files=plan.removable_count,
            reclaimable_bytes=plan.reclaimable,
            broken_files=len(plan.broken),
            freed_bytes=record.outcome.bytes_done if record.outcome else 0,
            run_id=record.run_id,
        )

    def view(self, record: ReportRecord, previews: set[Path]) -> ReportView:
        """Assemble the full view.

        Args:
            record: What the report is written from.
            previews: Thumbnails actually written.

        Returns:
            The view handed to the template.
        """
        plan = record.findings.plan
        outcome = record.outcome
        return ReportView(
            summary=self.summary(record),
            roots=self._roots(record.findings.roots),
            pairs=self._pairs(plan.decisions),
            groups=tuple(
                self._group(decision, previews)
                for decision in plan.decisions[: Sizes.MAX_GROUPS_IN_REPORT]
            ),
            hidden_groups=max(0, len(plan.decisions) - Sizes.MAX_GROUPS_IN_REPORT),
            broken=BrokenSection(
                handled=tuple(self._broken(item, previews) for item in plan.broken),
                protected=tuple(
                    self._broken(item, previews) for item in plan.protected_broken
                ),
            ),
            incidents=IncidentsSection(
                skipped=self._incidents(outcome.skipped if outcome else ()),
                failed=self._incidents(outcome.failed if outcome else ()),
            ),
        )

    def _roots(self, roots: tuple[Path, ...]) -> tuple[str, ...]:
        # /data mounted as a whole: show its drive folders (C:\, D:\) rather than "/".
        data_dir = self.mapper.data_dir
        if roots == (data_dir,) and data_dir.is_dir():
            roots = tuple(
                sorted(child for child in data_dir.iterdir() if child.is_dir())
            )
        return tuple(self.mapper.to_host(root) for root in roots)

    def _preview(self, file: MediaFile, previews: set[Path]) -> str | None:
        name = thumbnail_name(file)
        return name if self.folder / name in previews else None

    def _group(self, decision: KeepDecision, previews: set[Path]) -> GroupView:
        host = self.mapper.to_host
        return GroupView(
            size=decision.size,
            keeper=host(decision.keeper.path),
            removable=tuple(host(file.path) for file in decision.removable),
            protected=tuple(host(file.path) for file in decision.protected),
            thumbnail=self._preview(decision.keeper, previews),
        )

    def _broken(self, item: BrokenFile, previews: set[Path]) -> BrokenView:
        return BrokenView(
            path=self.mapper.to_host(item.file.path),
            reason=item.reason,
            detail=item.detail,
            thumbnail=self._preview(item.file, previews),
        )

    def _pairs(self, decisions: Iterable[KeepDecision]) -> tuple[FolderPairView, ...]:
        counts: Counter[tuple[Path, Path]] = Counter()
        sizes: Counter[tuple[Path, Path]] = Counter()
        for decision in decisions:
            for file in decision.removable:
                pair = (decision.keeper.path.parent, file.path.parent)
                counts[pair] += 1
                sizes[pair] += decision.size
        host = self.mapper.to_host
        return tuple(
            FolderPairView(host(kept), host(removed), count, sizes[kept, removed])
            for (kept, removed), count in sorted(
                counts.items(), key=lambda item: -sizes[item[0]]
            )
        )

    def _incidents(self, incidents: Iterable[Incident]) -> tuple[IncidentView, ...]:
        return tuple(
            IncidentView(self.mapper.to_host(Path(item.path)), item.reason)
            for item in incidents
        )
