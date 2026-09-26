"""Check, before a command starts, that the mount points it writes to accept writes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.errors import MountError
from media_dedup.i18n import _, ngettext
from media_dedup.paths.mounts import is_read_only, is_writable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from media_dedup.paths.mount_kind import MountKind
    from media_dedup.services.runtime import Runtime


def ensure_writable(runtime: Runtime, *kinds: MountKind) -> None:
    """Refuse to start when a mount point the command writes to is not writable.

    A folder Docker created for root, or one owned by another user, would otherwise
    fail once the long analysis is over. Mount points that do not persist are
    skipped: nothing is written there.

    Args:
        runtime: Settings, mount points and output.
        *kinds: The mount points the command writes to.

    Raises:
        MountError: One of them does not accept writes.
    """
    folders = [
        runtime.locations.path_of(kind) for kind in kinds if runtime.persistent(kind)
    ]
    blocked = [folder for folder in folders if not is_writable(folder)]
    if blocked:
        raise MountError(
            _("The container cannot write to {folders}.").format(
                folders=", ".join(runtime.mapper.to_host(folder) for folder in blocked)
            ),
            writable_tip(blocked),
        )


def writable_tip(folders: Sequence[Path]) -> str:
    """Tell how to let the container write to folders.

    Args:
        folders: Folders the container cannot write to.

    Returns:
        Drop `:ro` for a read-only mount; otherwise, create the folders as oneself.
    """
    count = len(folders)
    if any(folder.is_dir() and is_read_only(folder) for folder in folders):
        return ngettext(
            "Remove ':ro' from its -v option: the tool writes there.",
            "Remove ':ro' from their -v options: the tool writes there.",
            count,
        )
    return ngettext(
        "Create the folder yourself before docker run (Docker creates a missing one "
        'for root only); from WSL or Linux, add --user "$(id -u):$(id -g)".',
        "Create the folders yourself before docker run (Docker creates missing ones "
        'for root only); from WSL or Linux, add --user "$(id -u):$(id -g)".',
        count,
    )
