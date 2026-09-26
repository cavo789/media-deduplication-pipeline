"""Last-moment checks: the kept copy must still exist, be distinct, be identical."""

from __future__ import annotations

import filecmp
import os
from typing import TYPE_CHECKING

from media_dedup.i18n import _
from media_dedup.scan.sidecars import companions_of

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.scan.models import MediaFile


def removal_blocker(keeper: Path, candidate: Path, size: int) -> str | None:
    """Explain why `candidate` must not be deleted, or return None when it is safe.

    Safe means: both files exist, are two distinct files (not one file reached through
    two paths), still have the scanned size, and are equal byte for byte — so deleting
    `candidate` never loses data.

    Args:
        keeper: The copy that stays.
        candidate: The copy about to be deleted.
        size: Size recorded by the scan.

    Returns:
        The translated reason to skip, or None.
    """
    if not keeper.is_file():
        return _("the kept copy {path} no longer exists").format(path=keeper)
    if not candidate.is_file():
        return _("the file no longer exists")
    if keeper.samefile(candidate):
        return _("it is the kept copy itself, seen through another path")
    if keeper.stat().st_size != size or candidate.stat().st_size != size:
        return _("a file changed since the audit")
    if not filecmp.cmp(keeper, candidate, shallow=False):
        return _("the files are no longer identical")
    return None


def near_blocker(keeper: Path, candidate: MediaFile) -> str | None:
    """Explain why a near duplicate must not be moved, or return None when it is safe.

    A near duplicate is not identical to the kept picture, so no byte comparison
    applies: the kept picture must still exist, and the copy must be exactly the file
    the audit saw (same size, same modification time).

    Args:
        keeper: The picture that stays.
        candidate: The copy about to be moved to the quarantine, as audited.

    Returns:
        The translated reason to skip, or None.
    """
    if not keeper.is_file():
        return _("the kept copy {path} no longer exists").format(path=keeper)
    return change_blocker(candidate)


def burst_blocker(kept: tuple[MediaFile, ...], candidate: MediaFile) -> str | None:
    """Explain why a burst shot set aside must not be moved, or return None.

    The shot was set aside because another shot of its series is better: one of them
    must still be there, and the shot must be exactly the file the review showed.

    Args:
        kept: The shots of the series the review kept.
        candidate: The shot about to be moved to the quarantine, as audited.

    Returns:
        The translated reason to skip, or None.
    """
    if not any(shot.path.is_file() for shot in kept):
        return _("no shot kept from its series is left")
    return change_blocker(candidate)


def change_blocker(file: MediaFile) -> str | None:
    """Explain why a file is no longer the one the audit saw, or return None.

    Args:
        file: The file, as audited.

    Returns:
        The translated reason to skip it, or None when unchanged.
    """
    if not file.path.is_file():
        return _("the file no longer exists")
    stat = file.path.stat()
    if (stat.st_size, stat.st_mtime_ns) != (file.size, file.mtime_ns):
        return _("a file changed since the audit")
    return None


def orphan_blocker(sidecar: MediaFile) -> str | None:
    """Explain why a sidecar must not be moved, or return None when it is an orphan.

    The files it belongs to must be gone: a copy the clean skipped, or a file added
    since the audit, still needs it.

    Args:
        sidecar: The sidecar, as audited.

    Returns:
        The translated reason to skip it, or None.
    """
    blocker = change_blocker(sidecar)
    if blocker is not None:
        return blocker
    with os.scandir(sidecar.path.parent) as entries:
        names = [entry.name for entry in entries if not entry.is_dir()]
    if companions_of(sidecar.path, names):
        return _("a file with the same name is still next to it")
    return None
