"""Hashing, walking and file classification."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import TYPE_CHECKING

import pytest

from media_dedup.constants import MediaKind, Sizes
from media_dedup.scan.filters import ScanFilters, media_kind
from media_dedup.scan.hashing import full_digest, partial_digest
from media_dedup.scan.progress import NullProgress
from media_dedup.scan.walker import walk

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.scan.models import MediaFile


def listed(root: Path, filters: ScanFilters) -> list[MediaFile]:
    """Walk `root` and return its media files, sorted by path."""
    found = asyncio.run(walk((root,), filters, NullProgress()))
    return sorted(found, key=lambda file: file.path)


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("a.JPG", MediaKind.IMAGE),
        ("b.heic", MediaKind.IMAGE),
        ("c.CR2", MediaKind.RAW),
        ("d.MOV", MediaKind.VIDEO),
        ("e.xmp", None),
        ("f.AAE", None),
        ("g.txt", None),
    ],
)
def test_media_kind(tmp_path: Path, name: str, kind: MediaKind | None) -> None:
    """Extensions decide, case-insensitively; sidecars are never media."""
    assert media_kind(tmp_path / name) is kind


@pytest.mark.parametrize(
    "size",
    [10, Sizes.PARTIAL_HASH + 10, 2 * Sizes.PARTIAL_HASH + 10],
)
def test_digests(tmp_path: Path, size: int) -> None:
    """The full digest is SHA-256; partial digests differ when the ends differ."""
    data = os.urandom(size)
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(data)
    second.write_bytes(data[:-1] + bytes([data[-1] ^ 0xFF]))
    assert full_digest(first) == hashlib.sha256(data).hexdigest()
    assert partial_digest(first) != partial_digest(second)
    assert partial_digest(first) == partial_digest(first)


def test_walk_skips_system_and_excluded_folders(tmp_path: Path) -> None:
    """System folders, excluded folders, sidecars and symlinks are left out."""
    for relative in ("keep/a.jpg", "$RECYCLE.BIN/b.jpg", "@eaDir/c.jpg", "skip/d.jpg"):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_bytes(b"x")
    (tmp_path / "keep/a.xmp").write_text("sidecar")
    (tmp_path / "keep/link.jpg").symlink_to(tmp_path / "keep/a.jpg")
    (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
    found = listed(tmp_path, ScanFilters(excluded=(tmp_path / "SKIP",)))
    assert [file.path.relative_to(tmp_path).as_posix() for file in found] == [
        "keep/a.jpg"
    ]


def test_walk_logs_unreadable_folders(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A folder that cannot be listed is reported and skipped."""
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "a.jpg").write_bytes(b"x")
    locked.chmod(0)
    try:
        with caplog.at_level(logging.WARNING):
            assert not listed(tmp_path, ScanFilters())
    finally:
        locked.chmod(0o755)
    assert "Cannot read folder" in caplog.text


def test_walk_keeps_only_the_extensions_asked_for(tmp_path: Path) -> None:
    """An extension filter keeps matching files, whatever their case."""
    for name in ("a.PNG", "b.jpg", "c.webp"):
        (tmp_path / name).write_bytes(b"x")
    filters = ScanFilters(extensions=frozenset({".png", ".webp"}))
    assert [file.path.name for file in listed(tmp_path, filters)] == [
        "a.PNG",
        "c.webp",
    ]


def test_walk_reaches_every_level_of_many_folders(tmp_path: Path) -> None:
    """Folders read concurrently still yield every file, however deep or numerous."""
    expected = []
    for index in range(40):
        folder = tmp_path.joinpath(*(f"level{depth}" for depth in range(index % 6)))
        folder = folder / f"leaf{index}"
        folder.mkdir(parents=True)
        (folder / f"{index}.jpg").write_bytes(b"x")
        expected.append(folder / f"{index}.jpg")
    assert [file.path for file in listed(tmp_path, ScanFilters())] == sorted(expected)
