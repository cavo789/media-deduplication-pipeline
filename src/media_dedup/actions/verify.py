"""Last-moment checks: the kept copy must still exist, be distinct, be identical."""

from __future__ import annotations

import filecmp
from typing import TYPE_CHECKING

from media_dedup.i18n import _

if TYPE_CHECKING:
    from pathlib import Path


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
