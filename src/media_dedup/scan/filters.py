"""Decide which files are media and which folders are skipped."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.constants import (
    APP_DIR_NAMES,
    EXCLUDED_DIR_NAMES,
    IMAGE_EXTENSIONS,
    MEDIA_EXTENSIONS,
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
    """Folders the walk must not enter, and the extensions it keeps (media when empty).

    Extensions that are not media (`.pdf`) make the walk skip software folders too
    (`.git`, `node_modules`, `AppData`, ...): there, where a file lies is what makes a
    program work, and identical files are expected.
    """

    excluded: tuple[Path, ...] = ()
    extensions: frozenset[str] = frozenset()

    @property
    def other_files(self) -> bool:
        """Tell whether files other than photos, RAW files and videos are analysed.

        Returns:
            True when an extension asked for is not a media one.
        """
        return not self.extensions <= MEDIA_EXTENSIONS

    def accepts(self, path: Path) -> bool:
        """Tell whether a file has one of the extensions analysed.

        Args:
            path: A file.

        Returns:
            True when its extension is listed, or is a media one without a filter.
        """
        return path.suffix.casefold() in (self.extensions or MEDIA_EXTENSIONS)

    def kind_of(self, path: Path) -> MediaKind | None:
        """Classify a file the walk keeps: its media kind, or `OTHER`.

        Args:
            path: A file.

        Returns:
            Its kind, or None when its extension is not analysed.
        """
        if not self.accepts(path):
            return None
        return media_kind(path) or MediaKind.OTHER

    def skips_dir(self, path: Path) -> bool:
        """Tell whether a directory must be skipped.

        Args:
            path: Directory about to be entered.

        Returns:
            True for system folders, software folders (other files only) and
            user-excluded folders.
        """
        name = path.name.casefold()
        if name in EXCLUDED_DIR_NAMES or (self.other_files and name in APP_DIR_NAMES):
            return True
        return any(is_within(path, folder) for folder in self.excluded)
