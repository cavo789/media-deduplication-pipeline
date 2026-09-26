"""One path per file: nested mounts and hard links do not make duplicates."""

from __future__ import annotations

from pathlib import Path

from media_dedup.constants import MediaKind
from media_dedup.scan.aliases import Alias, unique_files
from media_dedup.scan.models import FileIdentity, MediaFile

SHARED = FileIdentity(device=1, inode=42)


def file(
    path: str, identity: FileIdentity | None = SHARED, size: int = 10
) -> MediaFile:
    """A listed file."""
    return MediaFile(Path(path), size, 0, MediaKind.IMAGE, identity)


def test_the_first_path_in_sorted_order_is_kept() -> None:
    """Two paths of one file: the second is set aside, whatever the listing order."""
    unique = unique_files([file("/data/c/photos/a.jpg"), file("/data/c/Photos/a.jpg")])
    assert [str(item.path) for item in unique.files] == ["/data/c/Photos/a.jpg"]
    assert unique.aliases == (
        Alias(Path("/data/c/photos/a.jpg"), Path("/data/c/Photos/a.jpg")),
    )


def test_the_same_path_twice_is_silently_merged() -> None:
    """Nested mounts list a path twice: that is no alias."""
    unique = unique_files([file("/data/a.jpg"), file("/data/a.jpg")])
    assert len(unique.files) == 1
    assert not unique.aliases


def test_distinct_or_unknown_identities_are_kept() -> None:
    """Other inode, other size, or no identity (st_ino 0): distinct files."""
    unique = unique_files(
        [
            file("/data/a.jpg"),
            file("/data/b.jpg", FileIdentity(device=1, inode=43)),
            file("/data/c.jpg", size=11),
            file("/data/d.jpg", None),
            file("/data/e.jpg", None),
        ]
    )
    assert len(unique.files) == 5
    assert not unique.aliases
