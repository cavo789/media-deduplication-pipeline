"""Folder pairs: the copies each pair holds, and whether a folder is a full copy."""

from __future__ import annotations

from pathlib import Path

from media_dedup.constants import MediaKind
from media_dedup.plan.models import KeepDecision
from media_dedup.plan.pairs import folder_pairs
from media_dedup.scan.models import MediaFile


def media(path: str) -> MediaFile:
    """A tiny image at `path`."""
    return MediaFile(Path(path), 1, 0, MediaKind.IMAGE)


def copied(name: str, folder: str = "/data/d/Backup") -> KeepDecision:
    """`name` kept in /data/c/Photos, its copy deleted from `folder`."""
    return KeepDecision(
        name, 1, media(f"/data/c/Photos/{name}"), (media(f"{folder}/{name}"),)
    )


def test_a_folder_whose_every_file_goes_is_a_complete_copy() -> None:
    r"""Both files of D:\Backup have a kept copy: the folder is entirely a copy."""
    folders = {Path("/data/d/Backup"): 2, Path("/data/c/Photos"): 5}
    (pair,) = folder_pairs([copied("a.jpg"), copied("b.jpg")], folders)
    assert pair.complete
    assert pair.files == len(pair.copies) == 2
    assert {copy.removed.path.name for copy in pair.copies} == {"a.jpg", "b.jpg"}


def test_a_folder_keeping_other_files_is_not_complete() -> None:
    r"""A third, unique file stays in D:\Backup; unknown counts are never complete."""
    decisions = [copied("a.jpg"), copied("b.jpg")]
    (partial,) = folder_pairs(decisions, {Path("/data/d/Backup"): 3})
    (unknown,) = folder_pairs(decisions)
    assert not partial.complete
    assert not unknown.complete


def test_copies_inside_one_folder_are_never_complete() -> None:
    """Duplicates within a folder do not empty it: its originals stay."""
    decision = KeepDecision(
        "d", 1, media("/data/c/Photos/a.jpg"), (media("/data/c/Photos/a (1).jpg"),)
    )
    (pair,) = folder_pairs([decision], {Path("/data/c/Photos"): 1})
    assert not pair.complete


def test_equal_pairs_are_ordered_by_path() -> None:
    """Same gain, same count: the order is still stable."""
    pairs = folder_pairs([copied("a.jpg", "/data/e/Z"), copied("b.jpg", "/data/e/A")])
    assert [str(pair.removed_from) for pair in pairs] == ["/data/e/A", "/data/e/Z"]
