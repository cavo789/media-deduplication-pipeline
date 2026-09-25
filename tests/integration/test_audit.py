"""The audit service on a realistic tree (the demo tree)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from media_dedup.constants import BrokenReason
from media_dedup.errors import MountError
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from tests.support.demo import build_demo
from tests.support.media import FFMPEG
from tests.support.runtime import make_runtime, output_of

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.config.layers import Layer
    from media_dedup.paths.locations import Locations
    from media_dedup.plan.models import AuditFindings


def audit(locations: Locations, cli: Layer | None = None) -> AuditFindings:
    """Run a complete audit of the data mount point."""
    return AuditService(make_runtime(locations, cli), NullProgress()).run()


def names(paths: list[Path]) -> list[str]:
    """File names, sorted, for readable assertions."""
    return sorted(path.name for path in paths)


def test_demo_tree_findings(locations: Locations) -> None:
    """Exact copies are grouped; bursts, sidecars and unique files are left alone."""
    build_demo(locations.data_dir)
    plan = audit(locations).plan
    keepers = sorted(
        str(d.keeper.path.relative_to(locations.data_dir)) for d in plan.decisions
    )
    expected_groups = 5 if FFMPEG else 4
    assert len(plan.decisions) == expected_groups
    assert "d/backup/2019/IMG_0001.jpg" in keepers  # shortest path wins the final tie
    removable = [f.path for d in plan.decisions for f in d.removable]
    assert "IMG_0001 (1).jpg" in names(removable)
    assert not any("Rafale" in str(path) for path in removable)
    reasons = {item.file.path.name: item.reason for item in plan.broken}
    assert reasons["IMG_9999.jpg"] is BrokenReason.EMPTY
    assert reasons["IMG_0001_interrupted.jpg"] is BrokenReason.UNREADABLE_IMAGE
    if FFMPEG:
        assert reasons["anniversaire-coupée.mp4"] is BrokenReason.UNREADABLE_VIDEO


def test_protected_folder_is_never_modified(locations: Locations) -> None:
    """A protected folder holds the kept copies; its broken files are left alone."""
    build_demo(locations.data_dir)
    plan = audit(locations, {"folders": {"protected": ["D:\\backup"]}}).plan
    removable = [f.path for d in plan.decisions for f in d.removable]
    assert not any("backup" in str(path) for path in removable)
    assert all("backup" in str(d.keeper.path) for d in plan.decisions)
    assert plan.protected_broken
    assert all("backup" not in str(item.file.path) for item in plan.broken)


def test_preferred_folder_keeps_its_copies(locations: Locations) -> None:
    """The preferred folder keeps the originals; copies go from the other folders."""
    build_demo(locations.data_dir)
    folders: dict[str, object] = {"preferred": ["C:\\Users\\Public\\Pictures"]}
    plan = audit(locations, {"folders": folders}).plan
    removable = [f.path for d in plan.decisions for f in d.removable]
    assert all("Pictures" not in str(path) for path in removable)


def test_excluded_folder_is_not_scanned(locations: Locations) -> None:
    """Files of an excluded folder are neither counted nor grouped."""
    build_demo(locations.data_dir)
    everything = audit(locations).files_scanned
    without_backup = audit(locations, {"folders": {"excluded": ["D:\\backup"]}})
    assert without_backup.files_scanned < everything
    decisions = without_backup.plan.decisions
    paths = [f.path for d in decisions for f in (d.keeper, *d.removable)]
    assert not any("backup" in str(path) for path in paths)


def test_second_audit_reuses_the_index(
    locations: Locations,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a persistent cache, unchanged files are neither hashed nor decoded again."""
    build_demo(locations.data_dir)
    first = audit(locations)

    def forbidden(*_args: object) -> None:
        raise AssertionError

    monkeypatch.setattr("media_dedup.scan.exact.full_digest", forbidden)
    monkeypatch.setattr("media_dedup.scan.broken.image_problem", forbidden)
    second = audit(locations)
    assert len(second.plan.decisions) == len(first.plan.decisions)


def test_unmounted_folders_are_reported(locations: Locations) -> None:
    """A configured folder that is not mounted produces a warning."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations, {"folders": {"protected": ["Z:\\nowhere"]}})
    AuditService(runtime, NullProgress()).run()
    assert "Z:\\nowhere" in output_of(runtime)


def test_nothing_mounted_is_an_error(locations: Locations) -> None:
    """An empty data directory means the -v options are missing."""
    with pytest.raises(MountError) as caught:
        audit(locations)
    assert caught.value.tip is not None
