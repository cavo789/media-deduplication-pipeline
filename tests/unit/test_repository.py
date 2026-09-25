"""The SQLite index of facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.constants import BrokenReason, MediaKind
from media_dedup.index.facts import FileFacts
from media_dedup.index.repository import FactsRepository
from media_dedup.scan.models import MediaFile

if TYPE_CHECKING:
    from pathlib import Path


def test_facts_round_trip_and_invalidation(tmp_path: Path) -> None:
    """Facts survive a reopen, and a new mtime makes them stale."""
    index = tmp_path / "index.sqlite"
    file = MediaFile(tmp_path / "a.jpg", 10, 1, MediaKind.IMAGE)
    facts = (
        FileFacts()
        .with_partial("p")
        .with_full("f")
        .with_integrity(BrokenReason.UNREADABLE_IMAGE, "boom")
    )
    with FactsRepository.open(index) as repository:
        repository.put(file, facts)
    with FactsRepository.open(index) as repository:
        assert repository.get(file) == facts
        touched = MediaFile(file.path, file.size, 2, file.kind)
        assert repository.get(touched) == FileFacts()


def test_in_memory_index_starts_empty(tmp_path: Path) -> None:
    """Without a cache mount the index lives in memory only."""
    file = MediaFile(tmp_path / "a.jpg", 10, 1, MediaKind.IMAGE)
    with FactsRepository.open(None) as repository:
        assert repository.get(file) == FileFacts()
        repository.put(file, FileFacts().with_integrity(None, ""))
        assert repository.get(file).integrity_checked
