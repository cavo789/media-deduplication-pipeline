"""One file seen through two paths is never a duplicate of itself."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from media_dedup.errors import MountError
from media_dedup.paths.mounts import MountTable
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from tests.support.runtime import make_runtime, output_of

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations
    from tests.support.media import MediaFactory


def test_hard_links_are_one_file(locations: Locations, media: MediaFactory) -> None:
    """A hard link is listed once, reported, and never planned for deletion."""
    original = media.image("c/Photos/2019/IMG_0001.jpg")
    (locations.data_dir / "c/Photos/Mariage").mkdir()
    (locations.data_dir / "c/Photos/Mariage/Marie.jpg").hardlink_to(original)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    assert findings.files_scanned == 1
    assert not findings.plan.decisions
    assert "1 file is reachable through two paths" in output_of(runtime)


def test_a_folder_mounted_twice_stops_the_audit(
    locations: Locations,
    media: MediaFactory,
) -> None:
    r"""C:\Photos and C:\photos\2019 on unrelated mount points: refused, with a tip."""
    media.image("c/Photos/2019/IMG_0001.jpg")
    data = locations.data_dir
    mounts = MountTable(
        frozenset(),
        host_sources=(
            (data / "c/Photos", "C:\\Photos"),
            (data / "c/photos/2019", "C:\\photos\\2019"),
        ),
    )
    runtime = replace(make_runtime(locations), mounts=mounts)
    with pytest.raises(MountError) as caught:
        AuditService(runtime, NullProgress()).run()
    assert "C:\\photos\\2019" in caught.value.message
    assert caught.value.tip is not None
