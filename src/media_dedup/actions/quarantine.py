"""Move a file to the quarantine, proving the copy identical before removing it."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Final

from media_dedup.constants import ActionKind
from media_dedup.i18n import _
from media_dedup.scan.hashing import full_digest

if TYPE_CHECKING:
    from pathlib import Path

# Actions undone by moving the file back from the quarantine.
QUARANTINED: Final = frozenset(
    {ActionKind.QUARANTINE, ActionKind.QUARANTINE_NEAR}
    | {ActionKind.QUARANTINE_DUPLICATE, ActionKind.QUARANTINE_SIDECAR},
)


def move_verified(source: Path, target: Path) -> None:
    """Copy `source` to `target`, prove the copy identical, then delete `source`.

    Works across disks, unlike a rename.

    Args:
        source: File to move.
        target: Destination.

    Raises:
        OSError: The copy differs from the original (the original is kept).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if full_digest(source) != full_digest(target):
        target.unlink()
        raise OSError(_("the quarantine copy differs from the original"))
    source.unlink()
