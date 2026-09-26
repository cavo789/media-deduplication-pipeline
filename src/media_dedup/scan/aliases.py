"""Keep one path per file: a file reachable through two paths is analysed once.

Two paths lead to the same file when a folder is mounted twice, or through hard
links. Listed twice, the file would look like a duplicate of itself, and deleting
"the copy" would delete the only one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from media_dedup.scan.models import FileIdentity, MediaFile


@dataclass(frozen=True, slots=True)
class Alias:
    """A second path of a file already listed under `same_as`."""

    path: Path
    same_as: Path


@dataclass(frozen=True, slots=True)
class UniqueFiles:
    """The files to analyse, one path each, and the other paths set aside."""

    files: tuple[MediaFile, ...]
    aliases: tuple[Alias, ...]


def unique_files(found: Iterable[MediaFile]) -> UniqueFiles:
    """Keep the first path, in sorted order, of every file.

    A path listed twice (nested mounts) is kept once, silently. Different paths
    sharing a filesystem identity, size and modification time are one file.

    Args:
        found: The files listed by the walker, in any order.

    Returns:
        The files by path, and the paths set aside.
    """
    by_path = {file.path: file for file in found}
    first_path: dict[tuple[FileIdentity, int, int], Path] = {}
    files: list[MediaFile] = []
    aliases: list[Alias] = []
    for path in sorted(by_path):
        file = by_path[path]
        if file.identity is not None:
            key = (file.identity, file.size, file.mtime_ns)
            first = first_path.setdefault(key, path)
            if first != path:
                aliases.append(Alias(path, first))
                continue
        files.append(file)
    return UniqueFiles(tuple(files), tuple(aliases))
