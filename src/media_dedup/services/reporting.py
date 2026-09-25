"""Write reports when a reports mount exists."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.writer import ReportWriter

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.report.views import ReportRecord
    from media_dedup.services.runtime import Runtime


def write_report(runtime: Runtime, record: ReportRecord) -> Path | None:
    """Write the HTML report of a run.

    Args:
        runtime: Settings, mount points and output.
        record: What to report.

    Returns:
        Path of `report.html`, or None when reports would not survive the container.
    """
    if not runtime.persistent(MountKind.REPORTS):
        return None
    runtime.locations.reports_dir.mkdir(parents=True, exist_ok=True)
    with runtime.executor_factory() as executor:
        writer = ReportWriter(runtime.locations.reports_dir, runtime.mapper, executor)
        return writer.write(record)
