"""HTML reports, their summaries and the catalogue page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.constants import RunKind
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.index_page import load_summaries, prune_reports
from media_dedup.report.views import ReportRecord
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.clean import CleanService
from media_dedup.services.reporting import write_report
from tests.support.demo import build_demo
from tests.support.runtime import make_locations, make_runtime

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.paths.locations import Locations


def test_audit_and_clean_reports(locations: Locations) -> None:
    """Each run gets a folder with report, summary and previews; the index lists all."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    audit_report = write_report(runtime, ReportRecord(RunKind.AUDIT, findings))
    run_id, outcome = CleanService(runtime, NullProgress()).execute(findings.plan)
    clean_record = ReportRecord(RunKind.CLEAN, findings, outcome, run_id)
    clean_report = write_report(runtime, clean_record)
    assert audit_report is not None
    assert clean_report is not None
    html = audit_report.read_text()
    assert "IMG_0001 (1).jpg" in html
    assert "C:\\Family Photos" in html
    assert "<code>D:\\</code>" in html
    assert any((audit_report.parent / "thumbs").glob("*.jpg"))
    assert clean_report.parent.name.startswith(run_id)
    summaries = load_summaries(locations.reports_dir)
    assert [summary.kind for summary in summaries] == [RunKind.CLEAN, RunKind.AUDIT]
    assert summaries[0].freed_bytes > 0
    index = (locations.reports_dir / "index.html").read_text()
    assert audit_report.parent.name in index


def test_prune_keeps_the_most_recent(locations: Locations) -> None:
    """Pruning deletes the oldest report folders and refreshes the index."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    written = [
        write_report(runtime, ReportRecord(RunKind.AUDIT, findings)) for _ in range(3)
    ]
    removed = prune_reports(locations.reports_dir, keep=1)
    assert len(removed) == 2
    assert [summary.folder for summary in load_summaries(locations.reports_dir)] == [
        report.parent.name for report in written[-1:] if report is not None
    ]


def test_no_report_without_a_reports_mount(tmp_path: Path) -> None:
    """Reports written inside the container would vanish: none is written."""
    locations = make_locations(tmp_path, MountKind.REPORTS)
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    assert write_report(runtime, ReportRecord(RunKind.AUDIT, findings)) is None


def test_unreadable_summary_is_skipped(locations: Locations) -> None:
    """A corrupt summary.json does not break the catalogue."""
    broken = locations.reports_dir / "20260101-000000-audit"
    broken.mkdir()
    (broken / "summary.json").write_text("{not json")
    assert load_summaries(locations.reports_dir) == []
