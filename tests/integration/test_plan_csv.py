"""plan.csv: every file of the plan, once, in a file Excel reads in any language."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from media_dedup.constants import Locale, RunKind
from media_dedup.i18n import install
from media_dedup.report.views import ReportRecord
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.reporting import write_report
from tests.support.demo import build_demo
from tests.support.runtime import make_runtime

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.paths.locations import Locations
    from media_dedup.plan.models import AuditFindings


def audit_with_report(locations: Locations) -> tuple[AuditFindings, Path]:
    """Audit the demo tree and write its report; return findings and report folder."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    report = write_report(runtime, ReportRecord(RunKind.AUDIT, findings))
    assert report is not None
    return findings, report.parent


def test_every_file_of_the_plan_is_listed_once(locations: Locations) -> None:
    """Keepers, copies and broken files: one row each, comma-separated in English."""
    findings, folder = audit_with_report(locations)
    raw = (folder / "plan.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # the BOM Excel needs for accents
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(text.splitlines()))
    header, body = rows[0], rows[1:]
    assert header[:4] == ["Group", "SHA-256", "Size (bytes)", "Action"]
    plan = findings.plan
    grouped = sum(1 + len(d.removable) + len(d.protected) for d in plan.decisions)
    assert len(body) == grouped + len(plan.broken) + len(plan.protected_broken)
    deleted = [row for row in body if row[3] == "delete" and row[0]]
    assert len(deleted) == plan.removable_count
    assert any(row[4].endswith("IMG_0001 (1).jpg") for row in deleted)
    assert any("Empty file (0 bytes)" in row[7] for row in body)
    assert 'href="plan.csv"' in (folder / "report.html").read_text()
    index = (locations.reports_dir / "index.html").read_text()
    assert f'href="{folder.name}/plan.csv"' in index


def test_french_uses_semicolons(locations: Locations) -> None:
    """French Excel expects ';' as the list separator, and French headers."""
    install(Locale.FR)
    _findings, folder = audit_with_report(locations)
    first = (folder / "plan.csv").read_text(encoding="utf-8-sig").splitlines()[0]
    assert first.startswith("Groupe;SHA-256;")
