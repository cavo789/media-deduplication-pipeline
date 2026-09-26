"""Run identifiers and the per-run history derived from journals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from media_dedup.actions.journal import journal_file, latest_states, read_journal
from media_dedup.actions.quarantine import QUARANTINED
from media_dedup.constants import JOURNAL_SUFFIX, Phase, Status

if TYPE_CHECKING:
    from pathlib import Path

_RUN_ID_FORMAT: Final = "%Y%m%d-%H%M%S"


def new_run_id(journal_dir: Path) -> str:
    """Create a sortable, unique run identifier such as `20260925-183015`.

    Args:
        journal_dir: Where journals live, to avoid collisions.

    Returns:
        A fresh identifier.
    """
    base = datetime.now(UTC).strftime(_RUN_ID_FORMAT)
    run_id, suffix = base, 1
    while journal_file(journal_dir, run_id).exists():
        suffix += 1
        run_id = f"{base}-{suffix}"
    return run_id


@dataclass(frozen=True, slots=True)
class RunSummary:
    """What a `clean` run did, and whether it was undone."""

    run_id: str
    deleted: int
    freed: int
    quarantined: int
    restored: int


def summarize(journal_dir: Path, run_id: str) -> RunSummary:
    """Summarise one run from its journal.

    Args:
        journal_dir: Journal mount point.
        run_id: Identifier of the run.

    Returns:
        The run summary.
    """
    entries = read_journal(journal_file(journal_dir, run_id))
    done = [
        e
        for e in latest_states(entries, Phase.CLEAN).values()
        if e.status is Status.DONE
    ]
    restored = latest_states(entries, Phase.UNDO).values()
    removed = [e for e in done if e.action not in QUARANTINED]
    return RunSummary(
        run_id=run_id,
        deleted=len(removed),
        freed=sum(entry.size for entry in done),
        quarantined=len(done) - len(removed),
        restored=sum(1 for entry in restored if entry.status is Status.DONE),
    )


def list_run_ids(journal_dir: Path) -> list[str]:
    """List every run that has a journal, newest first.

    Args:
        journal_dir: Journal mount point.

    Returns:
        The run identifiers.
    """
    if not journal_dir.is_dir():
        return []
    ids = (
        path.name.removesuffix(JOURNAL_SUFFIX)
        for path in journal_dir.glob(f"*{JOURNAL_SUFFIX}")
    )
    return sorted(ids, reverse=True)
