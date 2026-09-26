r"""A Windows folder mounted twice under /data: its files would look duplicated."""

from __future__ import annotations

from pathlib import Path

from media_dedup.paths.overlaps import Overlap, mount_overlaps

PHOTOS = (Path("/data/c/Photos"), "C:\\Photos")


def test_case_typo_on_a_subfolder_is_an_overlap() -> None:
    r"""Windows ignores case, the container does not: two views of C:\Photos\2019."""
    inner = (Path("/data/c/photos/2019"), "C:\\photos\\2019")
    assert mount_overlaps([PHOTOS, inner]) == (
        Overlap("C:\\photos\\2019", Path("/data/c/Photos/2019"), inner[0]),
    )


def test_same_folder_twice_is_reported_once() -> None:
    """One folder on two mount points: a single overlap, whatever the order."""
    other = (Path("/data/photos"), "c:\\PHOTOS")
    overlaps = mount_overlaps([other, PHOTOS])
    assert len(overlaps) == 1
    assert {overlaps[0].first, overlaps[0].second} == {PHOTOS[0], other[0]}


def test_subfolder_on_its_own_path_is_fine() -> None:
    r"""C:\Photos\2019 on /data/c/Photos/2019 (any case below /data/c/Photos): fine."""
    mirror = (Path("/data/c/Photos/2019"), "C:\\PHOTOS\\2019")
    drive = (Path("/data/c"), "C:\\")
    assert not mount_overlaps([drive, PHOTOS, mirror])


def test_subfolder_elsewhere_below_its_parent_is_an_overlap() -> None:
    r"""C:\Photos\2019 on /data/c/Photos/Old is seen there and in .../Photos/2019."""
    inner = (Path("/data/c/Photos/Old"), "C:\\Photos\\2019")
    assert mount_overlaps([PHOTOS, inner]) == (
        Overlap("C:\\Photos\\2019", Path("/data/c/Photos/2019"), inner[0]),
    )


def test_unrelated_folders_do_not_overlap() -> None:
    """Different drives, sibling folders, or a similar prefix are distinct folders."""
    assert not mount_overlaps(
        [
            PHOTOS,
            (Path("/data/d/Photos"), "D:\\Photos"),
            (Path("/data/c/Photos2"), "C:\\Photos2"),
            (Path("/data/c/Photos/Backup"), "E:\\Backup"),
        ]
    )
