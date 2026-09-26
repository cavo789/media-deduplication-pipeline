"""Inspect the mount table: which paths are Docker mounts, read-only, or writable."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.constants import MOUNTINFO_PATH
from media_dedup.paths.host_sources import windows_source

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations
    from media_dedup.paths.mount_kind import MountKind

_ROOT_FIELD = 3
_MOUNT_POINT_FIELD = 4
_SEPARATOR = "-"
_TAIL_FIELDS = 2
_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")


def _unescape(field: str) -> str:
    r"""Decode the octal escapes of mountinfo (`\040` is a space).

    Args:
        field: A raw mountinfo field.

    Returns:
        The decoded path.
    """
    return _OCTAL_ESCAPE.sub(lambda match: chr(int(match.group(1), 8)), field)


def read_mounts(mountinfo: Path = Path(MOUNTINFO_PATH)) -> tuple[Mount, ...]:
    """Read every mount of the current mount namespace.

    Args:
        mountinfo: The kernel mount table (overridable for tests).

    Returns:
        The mounts; empty when the table is unavailable (not Linux).
    """
    try:
        lines = mountinfo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    return tuple(
        mount for mount in (_parse(line.split(" ")) for line in lines) if mount
    )


def _parse(fields: list[str]) -> Mount | None:
    """Decode one mountinfo line.

    Args:
        fields: The line, split on spaces.

    Returns:
        The mount, or None for a malformed line.
    """
    if len(fields) <= _MOUNT_POINT_FIELD:
        return None
    point = Path(_unescape(fields[_MOUNT_POINT_FIELD]))
    tail = fields[fields.index(_SEPARATOR) + 1 :] if _SEPARATOR in fields else []
    if len(tail) < _TAIL_FIELDS:
        return Mount(point, None)
    root = _unescape(fields[_ROOT_FIELD])
    return Mount(point, windows_source(root, tail[0], _unescape(tail[1])))


def is_read_only(path: Path) -> bool:
    """Tell whether the filesystem holding `path` is mounted read-only.

    Args:
        path: An existing path.

    Returns:
        True for a `:ro` mount (or any read-only filesystem).
    """
    return bool(os.statvfs(path).f_flag & os.ST_RDONLY)


def is_writable(path: Path) -> bool:
    """Tell whether the container user can create files in `path`.

    Only a real write is reliable (Docker Desktop emulates the permissions of Windows
    folders): a nameless temporary file is created, then dropped. A missing folder is
    created first, as the command writing there would do.

    Args:
        path: A mount point.

    Returns:
        True when a file could be created in it.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class Mount:
    r"""One mount point, and the Windows folder it comes from when known."""

    point: Path
    windows_source: str | None


@dataclass(frozen=True, slots=True)
class MountTable:
    """A snapshot of the mount points, queried against the tool's locations."""

    mount_points: frozenset[Path]
    host_sources: tuple[tuple[Path, str], ...] = ()

    @classmethod
    def current(cls, mountinfo: Path = Path(MOUNTINFO_PATH)) -> MountTable:
        """Snapshot the mount table of this process.

        Args:
            mountinfo: The kernel mount table (overridable for tests).

        Returns:
            The current mount table.
        """
        mounts = read_mounts(mountinfo)
        return cls(
            frozenset(mount.point for mount in mounts),
            tuple(
                (mount.point, mount.windows_source)
                for mount in mounts
                if mount.windows_source is not None
            ),
        )

    def is_persistent(self, locations: Locations, kind: MountKind) -> bool:
        """Tell whether data written to `kind` survives the container.

        Args:
            locations: The tool's mount points.
            kind: Which mount point.

        Returns:
            True for a Docker mount, or a path set explicitly through the environment.
        """
        return (
            locations.is_explicit(kind) or locations.path_of(kind) in self.mount_points
        )

    def data_roots(self, data_dir: Path) -> tuple[Path, ...]:
        """List the folders mounted under `data_dir`, or `data_dir` itself if none.

        Args:
            data_dir: The directory holding the folders to analyse.

        Returns:
            The roots, sorted.
        """
        roots = sorted(
            point for point in self.mount_points if point.is_relative_to(data_dir)
        )
        nested = [root for root in roots if root != data_dir]
        return tuple(nested) if nested else (data_dir,)
