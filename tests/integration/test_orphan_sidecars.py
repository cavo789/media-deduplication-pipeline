"""Orphan sidecars: moved to the quarantine by `clean`, brought back by `undo`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.actions.journal import journal_file, read_journal
from media_dedup.constants import ActionKind, RunKind
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.views import ReportRecord
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.clean import CleanService
from media_dedup.services.reporting import write_report
from media_dedup.services.undo import undo_run
from tests.support.media import MediaFactory
from tests.support.runtime import make_locations, make_runtime, output_of

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.paths.locations import Locations

_KEPT = "c/Photos/IMG_1.jpg"
_COPY = "d/backup/2019/IMG_1.jpg"


def sidecars_tree(media: MediaFactory) -> dict[str, Path]:
    """A photo kept with its sidecar, a copy with its own, and a lone sidecar."""
    original = media.image(_KEPT, seed=1)
    media.copy(original, _COPY)
    paths = {
        "kept": media.root / "c/Photos/IMG_1.xmp",
        "orphan": media.root / "d/backup/2019/IMG_1.aae",
        "lone": media.root / "d/backup/2019/MVI_7.THM",
    }
    for path in paths.values():
        path.write_text(path.name)
    return paths


def test_clean_moves_orphans_and_undo_brings_them_back(
    locations: Locations, media: MediaFactory
) -> None:
    """The copy's sidecar and a lone one move; the kept photo's sidecar stays."""
    paths = sidecars_tree(media)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    orphans = {file.path for file in findings.plan.orphans}
    assert orphans == {paths["orphan"], paths["lone"]}
    service = CleanService(runtime, NullProgress())
    run_id, outcome = service.execute(service.feasible(findings.plan))
    assert outcome.quarantined == len(orphans)
    assert paths["kept"].is_file()
    assert not paths["orphan"].exists()
    assert not paths["lone"].exists()
    entries = read_journal(journal_file(locations.journal_dir, run_id))
    moved = {e.path for e in entries if e.action is ActionKind.QUARANTINE_SIDECAR}
    assert moved == {str(path) for path in orphans}
    report = write_report(
        runtime, ReportRecord(RunKind.CLEAN, findings, outcome, run_id)
    )
    assert report is not None
    assert "D:\\backup\\2019\\MVI_7.THM" in report.read_text()
    assert undo_run(runtime, run_id, NullProgress()).done == len(orphans) + 1
    assert paths["orphan"].read_text() == paths["orphan"].name
    assert paths["lone"].is_file()


def test_sidecar_whose_photo_is_back_stays(
    locations: Locations, media: MediaFactory
) -> None:
    """A file of the same name next to the sidecar at clean time keeps it there."""
    paths = sidecars_tree(media)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    (paths["lone"].parent / "MVI_7.MOV").write_bytes(b"back")
    _run_id, outcome = CleanService(runtime, NullProgress()).execute(findings.plan)
    assert paths["lone"].is_file()
    assert [incident.path for incident in outcome.skipped] == [paths["lone"]]


def test_extension_filter_leaves_lone_sidecars(
    locations: Locations, media: MediaFactory
) -> None:
    """With --ext, only the sidecars the clean itself leaves alone are orphans."""
    paths = sidecars_tree(media)
    runtime = make_runtime(locations, {"scan": {"extensions": ["jpg"]}})
    findings = AuditService(runtime, NullProgress()).run()
    assert [file.path for file in findings.plan.orphans] == [paths["orphan"]]


def test_without_quarantine_orphans_stay(tmp_path: Path) -> None:
    """Orphans are moved, never deleted: without /quarantine they stay put."""
    locations = make_locations(tmp_path, MountKind.QUARANTINE)
    paths = sidecars_tree(MediaFactory(locations.data_dir))
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    assert findings.plan.orphans
    plan = CleanService(runtime, NullProgress()).feasible(findings.plan)
    assert not plan.orphans
    assert "orphan sidecars are left in place" in output_of(runtime)
    assert paths["lone"].is_file()
