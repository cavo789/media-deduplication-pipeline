"""Last-moment checks before deleting a duplicate copy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.actions.verify import removal_blocker

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
