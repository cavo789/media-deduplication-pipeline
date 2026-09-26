"""Value objects produced by the scan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.constants import BrokenReason, MediaKind


@dataclass(frozen=True, slots=True)
class FileIdentity:
    """A file's identity on its filesystem: two paths, one identity, one file."""

    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class MediaFile:
    """A media file as seen when the scan listed it."""

    path: Path
    size: int
    mtime_ns: int
    kind: MediaKind
    identity: FileIdentity | None = None


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    """Files proven identical by size and SHA-256 (re-compared before any delete)."""

    digest: str
    size: int
    files: tuple[MediaFile, ...]


@dataclass(frozen=True, slots=True)
class BrokenFile:
    """A file that is empty or cannot be decoded."""

    file: MediaFile
    reason: BrokenReason
    detail: str = ""
