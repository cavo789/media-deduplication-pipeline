"""Duplicate groups in the report: the sample, and the command to check a hash."""

from __future__ import annotations

from pathlib import Path

from media_dedup.constants import MediaKind, Sizes
from media_dedup.plan.models import CleanPlan, KeepDecision
from media_dedup.report.group_views import check_command, sample_groups
from media_dedup.scan.models import MediaFile


def test_windows_paths_are_checked_with_powershell() -> None:
    """Single quotes keep PowerShell from expanding $ or backticks; ' is doubled."""
    command = check_command(["C:\\Photos\\a$b.jpg", "D:\\Old\\it's.jpg"])
    assert command == "Get-FileHash 'C:\\Photos\\a$b.jpg','D:\\Old\\it''s.jpg'"


def test_other_paths_are_checked_with_sha256sum() -> None:
    """Linux paths use sha256sum, quoted for the shell."""
    command = check_command(["/home/me/a b.jpg", "/home/me/c.jpg"])
    assert command == "sha256sum '/home/me/a b.jpg' /home/me/c.jpg"


def group(digest: str, kind: MediaKind = MediaKind.IMAGE) -> KeepDecision:
    """A group of two identical files."""
    keeper = MediaFile(Path(f"/data/c/{digest}"), 1, 0, kind)
    copy = MediaFile(Path(f"/data/d/{digest}"), 1, 0, kind)
    return KeepDecision(digest, 1, keeper, (copy,))


def test_the_sample_holds_images_in_digest_order() -> None:
    """Videos are left out; the pick is stable and capped."""
    decisions = [group("v", MediaKind.VIDEO), group("b"), group("a")]
    assert [d.digest for d in sample_groups(CleanPlan(tuple(decisions), ()))] == [
        "a",
        "b",
    ]
    many = tuple(group(f"{index:04d}") for index in range(Sizes.RANDOM_SAMPLE + 5))
    assert len(sample_groups(CleanPlan(many, ()))) == Sizes.RANDOM_SAMPLE
