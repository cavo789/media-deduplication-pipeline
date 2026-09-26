"""Compare two duplicate finders: agreement, disagreements, what is set aside."""

from __future__ import annotations

from pathlib import Path

from media_dedup.crosscheck.compare import AnalysedScope, OutsideReason, compare
from media_dedup.scan.filters import ScanFilters

SCOPE = AnalysedScope(
    roots=(Path("/data/c/Photos"),),
    filters=ScanFilters(excluded=(Path("/data/c/Photos/Backup"),)),
    broken=frozenset({Path("/data/c/Photos/cut.jpg")}),
)


def group(*names: str) -> frozenset[Path]:
    """A group of files below /data/c/Photos."""
    return frozenset(Path("/data/c/Photos") / name for name in names)


def test_same_groups_agree() -> None:
    """Identical groups, whatever their order: agreement, copies counted."""
    ours = [group("a.jpg", "b.jpg", "c.jpg"), group("d.mp4", "e.mp4")]
    result = compare(ours, list(reversed(ours)), SCOPE)
    assert result.agrees
    assert result.copies == 3
    assert not result.outside


def test_differences_are_listed_both_ways() -> None:
    """A group only one tool found, or split differently, is a disagreement."""
    result = compare(
        [group("a.jpg", "b.jpg")],
        [group("a.jpg", "b.jpg", "c.jpg")],
        SCOPE,
    )
    assert not result.agrees
    assert result.only_ours == (group("a.jpg", "b.jpg"),)
    assert result.only_theirs == (group("a.jpg", "b.jpg", "c.jpg"),)


def test_files_media_dedup_does_not_analyse_are_set_aside() -> None:
    """Other types, excluded or system folders, broken files, other mounts."""
    theirs = [
        group("a.jpg", "b.jpg", "notes.txt"),
        group("x.jpg", "Backup/x.jpg"),
        group("y.jpg", "$RECYCLE.BIN/y.jpg"),
        group("cut.jpg", "cut2.jpg"),
        frozenset({Path("/data/d/z.jpg"), Path("/data/d/z2.jpg")}),
    ]
    result = compare([group("a.jpg", "b.jpg")], theirs, SCOPE)
    assert result.agrees
    assert result.outside == {
        OutsideReason.EXTENSION: 1,
        OutsideReason.EXCLUDED: 2,
        OutsideReason.BROKEN: 1,
        OutsideReason.NOT_MOUNTED: 2,
    }
