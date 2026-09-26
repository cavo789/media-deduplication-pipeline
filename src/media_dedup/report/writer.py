"""Write one report folder: previews, report and pair pages, `summary.json`, index."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from media_dedup.constants import (
    PLAN_CSV_FILE_NAME,
    REPORT_FILE_NAME,
    SUMMARY_FILE_NAME,
)
from media_dedup.report.builder import ReportBuilder
from media_dedup.report.csv_export import write_plan_csv
from media_dedup.report.environment import make_environment
from media_dedup.report.index_page import write_index
from media_dedup.report.thumbnails import make_thumbnails

if TYPE_CHECKING:
    from concurrent.futures import Executor
    from pathlib import Path

    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.report.views import ReportRecord

_STAMP_FORMAT: Final = "%Y%m%d-%H%M%S"
_REPORT_TEMPLATE: Final = "report.html.j2"
_PAIR_TEMPLATE: Final = "pair.html.j2"


@dataclass(frozen=True, slots=True)
class ReportWriter:
    """Writes reports below the reports mount point."""

    reports_dir: Path
    mapper: HostPathMapper
    executor: Executor

    def write(self, record: ReportRecord) -> Path:
        """Write the report of an audit or a clean.

        Args:
            record: What to report.

        Returns:
            Path of `report.html`.
        """
        folder = self._new_folder(record)
        builder = ReportBuilder(self.mapper, folder)
        previews = asyncio.run(
            make_thumbnails(builder.thumbnail_jobs(record), self.executor)
        )
        view = builder.view(record, previews)
        environment = make_environment()
        target = folder / REPORT_FILE_NAME
        page = environment.get_template(_REPORT_TEMPLATE)
        target.write_text(page.render(report=view), encoding="utf-8")
        pair_page = environment.get_template(_PAIR_TEMPLATE)
        for name, pair_view in builder.pair_pages(record, previews):
            (folder / name).parent.mkdir(exist_ok=True)
            (folder / name).write_text(
                pair_page.render(page=pair_view), encoding="utf-8"
            )
        plan = record.findings.plan
        write_plan_csv(folder / PLAN_CSV_FILE_NAME, plan, self.mapper)
        summary_json = view.summary.model_dump_json(indent=2)
        (folder / SUMMARY_FILE_NAME).write_text(summary_json, encoding="utf-8")
        write_index(self.reports_dir)
        return target

    def _new_folder(self, record: ReportRecord) -> Path:
        stamp = record.run_id or datetime.now(UTC).strftime(_STAMP_FORMAT)
        base = f"{stamp}-{record.kind.value}"
        folder, suffix = self.reports_dir / base, 1
        while folder.exists():
            suffix += 1
            folder = self.reports_dir / f"{base}-{suffix}"
        folder.mkdir(parents=True)
        return folder
