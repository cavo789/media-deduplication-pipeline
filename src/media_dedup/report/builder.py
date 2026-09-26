"""Translate audit findings and a clean outcome into the report's view model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.constants import PLAN_CSV_FILE_NAME, RunKind, Sizes
from media_dedup.report.group_views import (
    GroupRenderer,
    largest_groups,
    sample_groups,
)
from media_dedup.report.pair_views import PairRenderer, report_pairs, sampled_files
from media_dedup.report.similar_views import SimilarRenderer, similar_files
from media_dedup.report.summary import CrossCheckSummary, ReportSummary
from media_dedup.report.thumbnails import PREVIEWABLE, ThumbnailJob, thumbnail_name
from media_dedup.report.views import (
    BrokenSection,
    BrokenView,
    GroupsSection,
    IncidentsSection,
    IncidentView,
    OrphansSection,
    ReportHeader,
    ReportView,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from media_dedup.actions.outcome import Incident
    from media_dedup.paths.host_paths import HostPathMapper
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
            One job per previewable keeper, sample, similar picture or broken image.
        """
        plan = record.findings.plan
        groups = (*largest_groups(plan), *sample_groups(plan))
        files = {
            file.path: file
            for file in (
                *(decision.keeper for decision in groups),
                *sampled_files(report_pairs(record)),
                *similar_files(record.findings.similar),
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
            orphan_sidecars=len(plan.orphans),
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
            header=ReportHeader(
                self.summary(record), self.mapper.roots_on_host(record.findings.roots)
            ),
            pairs=tuple(
                self._renderer(record, previews).summary(index, pair)
                for index, pair in enumerate(report_pairs(record), start=1)
            ),
            similar=SimilarRenderer(self.mapper, names).section(
                record.findings.similar
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
            orphans=OrphansSection(
                paths=tuple(
                    self.mapper.to_host(file.path)
                    for file in plan.orphans[: Sizes.MAX_ORPHANS_IN_REPORT]
                ),
                hidden=max(0, len(plan.orphans) - Sizes.MAX_ORPHANS_IN_REPORT),
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
                for index, pair in enumerate(report_pairs(record), start=1)
            )
        )

    def _renderer(self, record: ReportRecord, previews: set[Path]) -> PairRenderer:
        return PairRenderer(
            self.mapper, self._names(previews), record.kind is RunKind.CLEAN
        )

    def _names(self, previews: set[Path]) -> frozenset[str]:
        return frozenset(str(path.relative_to(self.folder)) for path in previews)

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
