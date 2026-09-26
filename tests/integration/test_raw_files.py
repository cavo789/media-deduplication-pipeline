"""RAW files in an audit: duplicates grouped, truncated ones broken, previews shown."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.constants import BrokenReason, RunKind
from media_dedup.report.views import ReportRecord
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.reporting import write_report
from tests.support.dng import DngSpec, dng_bytes
from tests.support.runtime import make_runtime

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations


def test_audit_checks_and_previews_raw_files(locations: Locations) -> None:
    """Two identical RAW files make a group; the half-copied one is broken."""
    data = dng_bytes(DngSpec(seed=3))
    folder = locations.data_dir / "c/Photos"
    folder.mkdir(parents=True)
    (folder / "IMG_1.dng").write_bytes(data)
    (folder / "IMG_1 (1).dng").write_bytes(data)
    (folder / "IMG_2.dng").write_bytes(data[: len(data) // 2])
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    [decision] = findings.plan.decisions
    assert decision.keeper.path == folder / "IMG_1.dng"
    [broken] = findings.plan.broken
    assert broken.file.path == folder / "IMG_2.dng"
    assert broken.reason is BrokenReason.UNREADABLE_RAW
    report = write_report(runtime, ReportRecord(RunKind.AUDIT, findings))
    assert report is not None
    assert any((report.parent / "thumbs").glob("*.jpg"))
    assert "RAW file cannot be decoded" in report.read_text()
