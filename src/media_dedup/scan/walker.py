"""List every media file below the data roots, without following symbolic links.

Folders are read concurrently: on a Windows drive seen through Docker, each directory
listing waits for a slow round trip, so several are kept in flight at once.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.constants import Sizes
from media_dedup.scan.filters import media_kind
from media_dedup.scan.models import MediaFile

if TYPE_CHECKING:
    from collections.abc import Iterable

    from media_dedup.scan.filters import ScanFilters
    from media_dedup.scan.progress import ProgressSink

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _Listing:
    """What one folder holds: its media files and the subfolders to visit."""

    files: tuple[MediaFile, ...] = ()
    folders: tuple[Path, ...] = ()


async def walk(
    roots: Iterable[Path],
    filters: ScanFilters,
    progress: ProgressSink,
) -> list[MediaFile]:
    """Return the media files below `roots`, as `filters` allows, in no fixed order.

    Unreadable folders are logged and skipped: one bad folder never stops the scan.
    Nested roots list their files twice: callers deduplicate by path.

    Args:
        roots: Folders to walk.
        filters: Folders to skip and extensions to keep.
        progress: Advanced once per media file found.

    Returns:
        Every media file found.
    """
    found: list[MediaFile] = []
    visits: list[asyncio.Task[None]] = []
    slots = asyncio.Semaphore(Sizes.IO_CONCURRENCY)
    async with asyncio.TaskGroup() as group:

        async def visit(folder: Path) -> None:
            async with slots:
                listing = await asyncio.to_thread(_list_folder, folder, filters)
            found.extend(listing.files)
            for _file in listing.files:
                progress.advance()
            visits.extend(group.create_task(visit(sub)) for sub in listing.folders)

        visits.extend(group.create_task(visit(root)) for root in roots)
    return found


def _list_folder(folder: Path, filters: ScanFilters) -> _Listing:
    """Read one folder (runs in a worker thread).

    Args:
        folder: Folder to read.
        filters: Folders to skip and extensions to keep.

    Returns:
        Its media files and the subfolders to visit; nothing when it cannot be read.
    """
    try:
        with os.scandir(folder) as entries:
            items = list(entries)
    except OSError as exc:
        _LOGGER.warning("Cannot read folder %s: %s", folder, exc.strerror)
        return _Listing()
    files: list[MediaFile] = []
    folders: list[Path] = []
    for entry in items:
        path = Path(entry.path)
        if entry.is_dir(follow_symlinks=False):
            if not filters.skips_dir(path):
                folders.append(path)
            continue
        media = _media_file(entry, path) if filters.accepts(path) else None
        if media is not None:
            files.append(media)
    return _Listing(tuple(files), tuple(folders))


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
