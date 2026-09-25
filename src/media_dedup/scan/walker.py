"""List every media file below the data roots, without following symbolic links."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.scan.filters import media_kind
from media_dedup.scan.models import MediaFile

if TYPE_CHECKING:
    from collections.abc import Iterator

    from media_dedup.scan.filters import ScanFilters

_LOGGER = logging.getLogger(__name__)


def walk(root: Path, filters: ScanFilters) -> Iterator[MediaFile]:
    """Yield the media files below `root`, depth-first, skipping excluded folders.

    Unreadable folders are logged and skipped: one bad folder never stops the scan.

    Args:
        root: Folder to walk.
        filters: Folders to skip.

    Yields:
        Every media file found.
    """
    pending = [root]
    while pending:
        folder = pending.pop()
        try:
            entries = list(os.scandir(folder))
        except OSError as exc:
            _LOGGER.warning("Cannot read folder %s: %s", folder, exc.strerror)
            continue
        for entry in sorted(entries, key=lambda item: item.name):
            path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                if not filters.skips_dir(path):
                    pending.append(path)
                continue
            media = _media_file(entry, path)
            if media is not None:
                yield media


def _media_file(entry: os.DirEntry[str], path: Path) -> MediaFile | None:
    """Describe a directory entry when it is a regular media file.

    Args:
        entry: The directory entry (its stat is cached by `scandir`).
        path: Its path.

    Returns:
        The media file, or None for anything else.
    """
    kind = media_kind(path)
    if kind is None or not entry.is_file(follow_symlinks=False):
        return None
    try:
        stat = entry.stat(follow_symlinks=False)
    except OSError as exc:
        _LOGGER.warning("Cannot read %s: %s", path, exc.strerror)
        return None
    return MediaFile(path=path, size=stat.st_size, mtime_ns=stat.st_mtime_ns, kind=kind)
