"""Last-moment checks before deleting a duplicate copy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.actions.verify import burst_blocker, removal_blocker
from media_dedup.constants import MediaKind
from media_dedup.scan.models import MediaFile

if TYPE_CHECKING:
    from pathlib import Path


def test_identical_files_can_be_removed(tmp_path: Path) -> None:
    """Same size, same bytes: no blocker."""
    keeper, copy = tmp_path / "keeper", tmp_path / "copy"
    keeper.write_bytes(b"same")
    copy.write_bytes(b"same")
    assert removal_blocker(keeper, copy, 4) is None


def test_every_blocker(tmp_path: Path) -> None:
    """Missing keeper, missing copy, changed size, different bytes: all block."""
    keeper, copy = tmp_path / "keeper", tmp_path / "copy"
    assert removal_blocker(keeper, copy, 4) is not None
    keeper.write_bytes(b"same")
    assert removal_blocker(keeper, copy, 4) == "the file no longer exists"
    copy.write_bytes(b"longer")
    assert removal_blocker(keeper, copy, 4) == "a file changed since the audit"
    copy.write_bytes(b"diff")
    assert removal_blocker(keeper, copy, 4) == "the files are no longer identical"


def test_one_file_reached_through_two_paths_is_never_deleted(tmp_path: Path) -> None:
    """A hard link, or a folder mounted twice, is the kept file itself: kept."""
    keeper, alias = tmp_path / "keeper", tmp_path / "alias"
    keeper.write_bytes(b"same")
    alias.hardlink_to(keeper)
    assert removal_blocker(keeper, alias, 4) == (
        "it is the kept copy itself, seen through another path"
    )


def test_a_burst_shot_moves_only_while_a_kept_shot_is_left(tmp_path: Path) -> None:
    """Every kept shot gone: the shot set aside stays; one left: it may move."""
    kept, aside = tmp_path / "kept.jpg", tmp_path / "aside.jpg"
    aside.write_bytes(b"shot")
    stat = aside.stat()
    candidate = MediaFile(aside, stat.st_size, stat.st_mtime_ns, MediaKind.IMAGE)
    shot = MediaFile(kept, 4, 0, MediaKind.IMAGE)
    assert burst_blocker((shot,), candidate) == "no shot kept from its series is left"
    kept.write_bytes(b"best")
    assert burst_blocker((shot,), candidate) is None
