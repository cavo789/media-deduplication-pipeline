"""Decide which files are media and which folders are skipped."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.constants import (
    EXCLUDED_DIR_NAMES,
    IMAGE_EXTENSIONS,
    RAW_EXTENSIONS,
    VIDEO_EXTENSIONS,
    MediaKind,
)
from media_dedup.paths.host_paths import is_within

if TYPE_CHECKING:
    from pathlib import Path


def media_kind(path: Path) -> MediaKind | None:
    """Classify a file by its extension, case-insensitively.

    Sidecars (`.xmp`, `.aae`, `.thm`) and every other file return None: never touched.

    Args:
        path: File to classify.

    Returns:
        Its media kind, or None when it is not a media file.
    """
    suffix = path.suffix.casefold()
    if suffix in IMAGE_EXTENSIONS:
        return MediaKind.IMAGE
    if suffix in RAW_EXTENSIONS:
        return MediaKind.RAW
    if suffix in VIDEO_EXTENSIONS:
        return MediaKind.VIDEO
    return None


@dataclass(frozen=True, slots=True)
class ScanFilters:
    """Folders the walk must not enter, and the extensions it keeps (all when empty)."""

    excluded: tuple[Path, ...] = ()
    extensions: frozenset[str] = frozenset()

    def accepts(self, path: Path) -> bool:
        """Tell whether a file has one of the extensions asked for.

        Args:
            path: A file.

        Returns:
            True when no extension filter is set, or when its extension is listed.
        """
        return not self.extensions or path.suffix.casefold() in self.extensions

    def skips_dir(self, path: Path) -> bool:
        """Tell whether a directory must be skipped.

        Args:
            path: Directory about to be entered.

        Returns:
            True for system folders and user-excluded folders.
        """
        if path.name.casefold() in EXCLUDED_DIR_NAMES:
            return True
        return any(is_within(path, folder) for folder in self.excluded)
