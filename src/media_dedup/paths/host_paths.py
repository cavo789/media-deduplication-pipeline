r"""Translate container paths to the host paths the user knows, and back.

Convention: `X:\some\folder` is mounted on `/data/x/some/folder`, and any other host
path `/p/q` on `/data/p/q`. That makes the translation lossless in both directions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_WINDOWS_PATH = re.compile(r"^(?P<drive>[A-Za-z]):[\\/]*(?P<rest>.*)$")
_SEPARATORS = re.compile(r"[\\/]+")


@dataclass(frozen=True, slots=True)
class HostPathMapper:
    r"""Maps between the container view (`/data/...`) and the host view (`C:\...`)."""

    data_dir: Path

    def to_host(self, path: Path) -> str:
        r"""Render a container path the way the user sees it on the host.

        Args:
            path: A path inside the container.

        Returns:
            `C:\\...` for a drive-letter mount, `/...` otherwise.
        """
        if not path.is_relative_to(self.data_dir):
            return str(path)
        parts = path.relative_to(self.data_dir).parts
        if parts and len(parts[0]) == 1 and parts[0].isalpha():
            return f"{parts[0].upper()}:\\" + "\\".join(parts[1:])
        return str(PurePosixPath("/", *parts))

    def relative(self, path: Path) -> Path:
        """Return `path` relative to the data directory (kept whole when outside it).

        Args:
            path: A path inside the container.

        Returns:
            The relative path, used to mirror the tree in the quarantine.
        """
        if path.is_relative_to(self.data_dir):
            return path.relative_to(self.data_dir)
        return Path(*path.parts[1:])

    def to_container(self, host_path: str) -> Path:
        r"""Translate a path typed by the user (config file or CLI) into the container.

        Args:
            host_path: `C:\\folder`, `/home/me/folder` or `/data/c/folder`.

        Returns:
            The matching path under the data directory.
        """
        windows = _WINDOWS_PATH.match(host_path)
        if windows is not None:
            rest = [part for part in _SEPARATORS.split(windows["rest"]) if part]
            return self.data_dir.joinpath(windows["drive"].lower(), *rest)
        path = Path(host_path)
        if path.is_relative_to(self.data_dir):
            return path
        return self.data_dir.joinpath(
            *path.parts[1:] if path.is_absolute() else path.parts
        )


def is_within(path: Path, folder: Path) -> bool:
    """Tell whether `path` is `folder` or lies below it, ignoring case (like Windows).

    Args:
        path: Candidate path.
        folder: Folder to test against.

    Returns:
        True when `path` is inside `folder`.
    """
    folder_parts = [part.casefold() for part in folder.parts]
    path_parts = [part.casefold() for part in path.parts]
    return path_parts[: len(folder_parts)] == folder_parts
