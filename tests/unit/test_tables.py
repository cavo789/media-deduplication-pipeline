"""Console summaries: the folder pairs read as plain sentences."""

from __future__ import annotations

import io
from pathlib import Path

from rich.console import Console

from media_dedup.console.tables import folder_pairs_view
from media_dedup.constants import MediaKind
from media_dedup.paths.host_paths import HostPathMapper
from media_dedup.plan.models import AuditFindings, CleanPlan, KeepDecision
from media_dedup.scan.models import MediaFile

MAPPER = HostPathMapper(Path("/data"))


def media(path: str) -> MediaFile:
    """A tiny image at `path`."""
    return MediaFile(Path(path), 1, 0, MediaKind.IMAGE)


def rendered(*decisions: KeepDecision) -> str:
    """The folder pairs of these decisions, as printed on a wide terminal."""
    findings = AuditFindings(0, (), CleanPlan(decisions, ()))
    table = folder_pairs_view(findings, MAPPER)
    assert table is not None
    buffer = io.StringIO()
    Console(file=buffer, width=200).print(table)
    return buffer.getvalue()


def test_two_folders_say_which_one_keeps_the_files() -> None:
    """A pair of folders names the kept folder and the one losing its copies."""
    decision = KeepDecision(
        "d", 1, media("/data/c/A/x.jpg"), (media("/data/c/B/x.jpg"),)
    )
    assert "1 file is both in C:\\A (kept) and in C:\\B (deleted), 1 B freed." in (
        rendered(decision)
    )


def test_one_folder_says_the_files_are_duplicated_inside() -> None:
    """Copies inside the same folder are described as such."""
    decisions = [
        KeepDecision(
            f"d{index}",
            1,
            media(f"/data/c/A/{index}.jpg"),
            (media(f"/data/c/A/{index} (1).jpg"),),
        )
        for index in range(2)
    ]
    assert "2 files are present several times in C:\\A" in rendered(*decisions)


def test_no_duplicate_means_no_pairs() -> None:
    """Without duplicates there is nothing to show."""
    assert folder_pairs_view(AuditFindings(0, (), CleanPlan((), ())), MAPPER) is None


def test_pairs_freeing_the_most_space_come_first() -> None:
    """One big video outweighs many small photos: the order follows the gain."""
    small = [
        KeepDecision(
            f"s{index}",
            1,
            media(f"/data/c/A/{index}.jpg"),
            (media(f"/data/c/B/{index}.jpg"),),
        )
        for index in range(3)
    ]
    big = KeepDecision(
        "v", 10_000, media("/data/c/C/v.mp4"), (media("/data/c/D/v.mp4"),)
    )
    output = rendered(*small, big)
    assert output.index("C:\\C") < output.index("C:\\A")
