"""The report's folder pairs: samples, the complete-copy badge, one page per pair."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.constants import RunKind
from media_dedup.report.views import ReportRecord
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.reporting import write_report
from tests.support.runtime import make_runtime

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations
    from tests.support.media import MediaFactory


def test_a_backup_folder_is_a_pair_with_its_own_page(
    locations: Locations,
    media: MediaFactory,
) -> None:
    r"""Every photo of D:\Backup is also in C:\Photos: one complete pair."""
    for seed in range(3):
        original = media.image(f"c/Photos/IMG_{seed}.jpg", seed)
        media.copy(original, f"d/Backup/IMG_{seed} (1).jpg")
    media.image("c/Photos/unique.jpg", seed=9)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    report = write_report(runtime, ReportRecord(RunKind.AUDIT, findings))
    assert report is not None
    html = report.read_text()
    assert "entirely a copy" in html
    assert 'href="pairs/pair-0001.html"' in html
    assert html.count('<img src="thumbs/') >= 3
    assert "How do we know these are duplicates?" in html
    assert "Random sample" in html
    assert "Get-FileHash &#39;C:\\Photos\\IMG_" in html
    digest = findings.plan.decisions[0].digest
    assert digest[:16] in html
    page = (report.parent / "pairs/pair-0001.html").read_text()
    assert "IMG_2 (1).jpg" in page
    assert "D:\\Backup" in page
    assert '<img src="../thumbs/' in page
