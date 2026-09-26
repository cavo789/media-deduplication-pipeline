"""Translate audit findings and a clean outcome into the report's view model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.constants import PLAN_CSV_FILE_NAME, RunKind, Sizes
from media_dedup.plan.pairs import folder_pairs
from media_dedup.report.group_views import (
    GroupRenderer,
    largest_groups,
    sample_groups,
)
from media_dedup.report.pair_views import PairRenderer, sampled_files
from media_dedup.report.summary import CrossCheckSummary, ReportSummary
from media_dedup.report.thumbnails import PREVIEWABLE, ThumbnailJob, thumbnail_name
from media_dedup.report.views import (
    BrokenSection,
    BrokenView,
    GroupsSection,
    IncidentsSection,
    IncidentView,
    ReportView,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from media_dedup.actions.outcome import Incident
    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.pairs import FolderPair
    from media_dedup.report.views import PairPageView, ReportRecord
    from media_dedup.scan.models import BrokenFile


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
            One job per previewable keeper, pair sample or broken image.
        """
        plan = record.findings.plan
        groups = (*largest_groups(plan), *sample_groups(plan))
        files = {
            file.path: file
            for file in (
                *(decision.keeper for decision in groups),
                *sampled_files(_pairs(record)),
                *(item.file for item in plan.broken),
            )
        }
        return [
            ThumbnailJob(file.path, self.folder / thumbnail_name(file))
            for file in files.values()
            if file.kind in PREVIEWABLE
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
            plan_file=PLAN_CSV_FILE_NAME,
            crosscheck=CrossCheckSummary.of(record.crosscheck),
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
        names = self._names(previews)
        groups = GroupRenderer(self.mapper, names)
        return ReportView(
            summary=self.summary(record),
            roots=self._roots(record.findings.roots),
            pairs=tuple(
                self._renderer(record, previews).summary(index, pair)
                for index, pair in enumerate(_pairs(record), start=1)
            ),
            groups=GroupsSection(
                sample=tuple(groups.group(d) for d in sample_groups(plan)),
                largest=tuple(groups.group(d) for d in largest_groups(plan)),
                hidden=max(0, len(plan.decisions) - Sizes.MAX_GROUPS_IN_REPORT),
            ),
            broken=BrokenSection(
                handled=tuple(self._broken(item, names) for item in plan.broken),
                protected=tuple(
                    self._broken(item, names) for item in plan.protected_broken
                ),
            ),
            incidents=IncidentsSection(
                skipped=self._incidents(outcome.skipped if outcome else ()),
                failed=self._incidents(outcome.failed if outcome else ()),
            ),
        )

    def pair_pages(
        self, record: ReportRecord, previews: set[Path]
    ) -> tuple[tuple[str, PairPageView], ...]:
        """Describe the page of every folder pair.

        Args:
            record: What the report is written from.
            previews: Thumbnails actually written.

        Returns:
            Each page's relative path and view.
        """
        renderer = self._renderer(record, previews)
        return tuple(
            (view.pair.page, view)
            for view in (
                renderer.page(index, pair)
                for index, pair in enumerate(_pairs(record), start=1)
            )
        )

    def _renderer(self, record: ReportRecord, previews: set[Path]) -> PairRenderer:
        return PairRenderer(
            self.mapper, self._names(previews), record.kind is RunKind.CLEAN
        )

    def _names(self, previews: set[Path]) -> frozenset[str]:
        return frozenset(str(path.relative_to(self.folder)) for path in previews)

    def _roots(self, roots: tuple[Path, ...]) -> tuple[str, ...]:
        # /data mounted as a whole: show its drive folders (C:\, D:\) rather than "/".
        data_dir = self.mapper.data_dir
        if roots == (data_dir,) and data_dir.is_dir():
            roots = tuple(
                sorted(child for child in data_dir.iterdir() if child.is_dir())
            )
        return tuple(self.mapper.to_host(root) for root in roots)

    def _broken(self, item: BrokenFile, names: frozenset[str]) -> BrokenView:
        name = thumbnail_name(item.file)
        return BrokenView(
            path=self.mapper.to_host(item.file.path),
            reason=item.reason,
            detail=item.detail,
            thumbnail=name if name in names else None,
        )

    def _incidents(self, incidents: Iterable[Incident]) -> tuple[IncidentView, ...]:
        return tuple(
            IncidentView(self.mapper.to_host(Path(item.path)), item.reason)
            for item in incidents
        )


def _pairs(record: ReportRecord) -> tuple[FolderPair, ...]:
    """The folder pairs of a report, the same order everywhere.

    Args:
        record: What the report is written from.

    Returns:
        The pairs.
    """
    findings = record.findings
    return folder_pairs(findings.plan.decisions, findings.folder_files)
