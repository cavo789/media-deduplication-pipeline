r"""Recognise the Windows folder behind a Docker Desktop bind mount.

Docker Desktop leaves the host folder visible in the mount table, in one of two shapes:

- a `9p` (drvfs) mount whose source is the drive (`C:\`) and whose root is the folder;
- a mount whose root is `/run/desktop/mnt/host/<drive>/<folder>`.

Knowing it lets the tool show `C:\Photos\2013` even for `-v "${PWD}:/data/current"`.
"""

from __future__ import annotations

import re
from typing import Final

_DESKTOP_ROOT = re.compile(
    r"^(?:/run)?/desktop/mnt/host/(?P<drive>[a-z])(?P<rest>/.*)?$"
)
_DRIVE_SOURCE = re.compile(r"^(?P<drive>[A-Za-z]):\\?$")
_DRVFS_TYPE: Final = "9p"


def windows_source(root: str, fs_type: str, source: str) -> str | None:
    r"""Return the Windows folder a mount comes from, when the mount table tells it.

    Args:
        root: The mount root (4th mountinfo field), unescaped.
        fs_type: The filesystem type (first field after ` - `).
        source: The mount source (second field after ` - `), unescaped.

    Returns:
        A path such as `C:\Photos`, or None when the source is not a Windows folder.
    """
    desktop = _DESKTOP_ROOT.match(root)
    if desktop is not None:
        return windows_path(desktop["drive"], desktop["rest"] or "")
    drive = _DRIVE_SOURCE.match(source)
    if fs_type == _DRVFS_TYPE and drive is not None:
        return windows_path(drive["drive"], root)
    return None


def windows_path(drive: str, posix_rest: str) -> str:
    r"""Build a Windows path from a drive letter and a `/`-separated remainder.

    Args:
        drive: The drive letter, any case.
        posix_rest: The folder below the drive root, e.g. `/Photos/2013`.

    Returns:
        The Windows path, e.g. `C:\Photos\2013`.
    """
    parts = [part for part in posix_rest.split("/") if part]
    return f"{drive.upper()}:\\" + "\\".join(parts)
