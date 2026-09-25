"""Inspect the mount table: which paths are Docker mounts, and which are read-only."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.constants import MOUNTINFO_PATH

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations
    from media_dedup.paths.mount_kind import MountKind

_MOUNT_POINT_FIELD = 4
_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")


def _unescape(field: str) -> str:
    r"""Decode the octal escapes of mountinfo (`\040` is a space).

    Args:
        field: A raw mountinfo field.

    Returns:
        The decoded path.
    """
    return _OCTAL_ESCAPE.sub(lambda match: chr(int(match.group(1), 8)), field)


def read_mount_points(mountinfo: Path = Path(MOUNTINFO_PATH)) -> frozenset[Path]:
    """Read every mount point of the current mount namespace.

    Args:
        mountinfo: The kernel mount table (overridable for tests).

    Returns:
        The mount points; empty when the table is unavailable (not Linux).
    """
    try:
        lines = mountinfo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return frozenset()
    fields = (line.split(" ") for line in lines)
    return frozenset(
        Path(_unescape(parts[_MOUNT_POINT_FIELD]))
        for parts in fields
        if len(parts) > _MOUNT_POINT_FIELD
    )


def is_read_only(path: Path) -> bool:
    """Tell whether the filesystem holding `path` is mounted read-only.

    Args:
        path: An existing path.

    Returns:
        True for a `:ro` mount (or any read-only filesystem).
    """
    return bool(os.statvfs(path).f_flag & os.ST_RDONLY)


@dataclass(frozen=True, slots=True)
class MountTable:
    """A snapshot of the mount points, queried against the tool's locations."""

    mount_points: frozenset[Path]

    @classmethod
    def current(cls) -> MountTable:
        """Snapshot the mount table of this process.

        Returns:
            The current mount table.
        """
        return cls(read_mount_points())

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
