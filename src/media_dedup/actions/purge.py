"""Permanently delete the quarantine of one or every run."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def quarantine_runs(quarantine_dir: Path) -> list[str]:
    """List the runs that still have quarantined files, newest first.

    Args:
        quarantine_dir: Quarantine mount point.

    Returns:
        The run identifiers.
    """
    if not quarantine_dir.is_dir():
        return []
    return sorted(
        (path.name for path in quarantine_dir.iterdir() if path.is_dir()), reverse=True
    )


def folder_size(folder: Path) -> int:
    """Sum the size of every file below `folder`.

    Args:
        folder: Folder to measure.

    Returns:
        Its size in bytes.
    """
    return sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())


def purge_run(quarantine_dir: Path, run_id: str) -> int:
    """Delete the quarantined files of a run.

    Args:
        quarantine_dir: Quarantine mount point.
        run_id: Run whose quarantine goes.

    Returns:
        Bytes freed.
    """
    folder = quarantine_dir / run_id
    freed = folder_size(folder)
    shutil.rmtree(folder)
    return freed
