"""Write reports when a reports mount exists."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.errors import MountError
from media_dedup.i18n import _
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.writer import ReportWriter
from media_dedup.services.writable import writable_tip

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

    Raises:
        MountError: The report could not be written; the run itself is over.
    """
    if not runtime.persistent(MountKind.REPORTS):
        return None
    reports_dir = runtime.locations.reports_dir
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        with runtime.executor_factory() as executor:
            report = ReportWriter(reports_dir, runtime.mapper, executor).write(record)
    except OSError as exc:
        raise MountError(
            _("The HTML report could not be written to {folder}: {reason}.").format(
                folder=runtime.mapper.to_host(reports_dir),
                reason=exc.strerror or exc,
            ),
            writable_tip((reports_dir,)) if isinstance(exc, PermissionError) else None,
        ) from exc
    return report
