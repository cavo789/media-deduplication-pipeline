"""Sidecars: which files they belong to, and when they become orphans."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from media_dedup.constants import MediaKind
from media_dedup.plan.keeper import KeepPolicy
from media_dedup.plan.models import CleanPlan, KeepDecision
from media_dedup.plan.orphans import sidecars_in_scope
from media_dedup.scan.filters import ScanFilters
from media_dedup.scan.models import MediaFile
from media_dedup.scan.progress import NullProgress
from media_dedup.scan.sidecars import Sidecar, companions_of, is_sidecar
from media_dedup.scan.walker import walk

DATA = Path("/data")
NAMES = ("IMG_1.JPG", "IMG_1.CR2", "IMG_1.aae", "IMG_10.jpg", "img_1 (1).jpg")


def file_at(relative: str, kind: MediaKind = MediaKind.IMAGE) -> MediaFile:
    """Describe a 10-byte file at `/data/<relative>`."""
    return MediaFile(DATA / relative, 10, 0, kind)


def sidecar_at(relative: str, *companions: str) -> Sidecar:
    """A sidecar at `/data/<relative>` belonging to `companions`."""
    return Sidecar(file_at(relative, MediaKind.SIDECAR), frozenset(companions))


@pytest.mark.parametrize(
    ("name", "expected"),
    [("a.XMP", True), ("a.aae", True), ("a.Thm", True), ("a.jpg", False)],
)
def test_is_sidecar(name: str, expected: bool) -> None:  # noqa: FBT001
    """Extensions decide, case-insensitively."""
    assert is_sidecar(name) is expected


@pytest.mark.parametrize(
    ("sidecar", "expected"),
    [
        ("IMG_1.xmp", {"IMG_1.JPG", "IMG_1.CR2"}),
        ("img_1.XMP", {"IMG_1.JPG", "IMG_1.CR2"}),
        ("IMG_1.CR2.xmp", {"IMG_1.CR2"}),
        ("IMG_2.xmp", set()),
    ],
)
def test_companions_share_the_name(sidecar: str, expected: set[str]) -> None:
    """Same name without extension, or the whole name; never another sidecar."""
    assert companions_of(DATA / sidecar, NAMES) == expected


def test_orphan_once_every_companion_is_removed() -> None:
    """A sidecar is an orphan when all the files it belongs to are removed."""
    sidecar = sidecar_at("c/IMG_1.xmp", "IMG_1.jpg", "IMG_1.CR2")
    assert not sidecar.is_orphan_without(frozenset({DATA / "c/IMG_1.jpg"}))
    both = frozenset({DATA / "c/IMG_1.jpg", DATA / "c/IMG_1.CR2"})
    assert sidecar.is_orphan_without(both)
    assert sidecar_at("c/lone.thm").is_orphan_without(frozenset())


def test_scope_leaves_protected_and_lone_sidecars() -> None:
    """Protected folders are never touched; lone sidecars only without a filter."""
    found = (
        sidecar_at("c/IMG_1.xmp", "IMG_1.jpg"),
        sidecar_at("c/lone.thm"),
        sidecar_at("d/safe/IMG_1.xmp", "IMG_1.jpg"),
        sidecar_at("c/IMG_1.xmp", "IMG_1.jpg"),
    )
    policy = KeepPolicy(protected=(DATA / "d/safe",))
    everything = sidecars_in_scope(found, policy, alone=True)
    assert [s.file.path for s in everything] == [
        DATA / "c/IMG_1.xmp",
        DATA / "c/lone.thm",
    ]
    filtered = sidecars_in_scope(found, policy, alone=False)
    assert [s.file.path for s in filtered] == [DATA / "c/IMG_1.xmp"]


def test_plan_orphans_follow_its_removals() -> None:
    """Only the sidecars whose files the plan removes (or had none) are orphans."""
    copy, keeper = file_at("d/IMG_1.jpg"), file_at("c/IMG_1.jpg")
    sidecars = (
        sidecar_at("d/IMG_1.aae", "IMG_1.jpg"),
        sidecar_at("c/IMG_1.xmp", "IMG_1.jpg"),
        sidecar_at("c/lone.thm"),
    )
    decision = KeepDecision("digest", 10, keeper, (copy,))
    plan = CleanPlan((decision,), (), sidecars=sidecars)
    assert [file.path for file in plan.orphans] == [
        DATA / "d/IMG_1.aae",
        DATA / "c/lone.thm",
    ]
    assert plan.removed == {copy.path}
    only_sidecars = CleanPlan((), (), sidecars=sidecars[2:])
    assert not only_sidecars.is_empty
    assert not CleanPlan((), (), sidecars=sidecars[:2]).orphans


def test_walk_lists_sidecars_with_their_files(tmp_path: Path) -> None:
    """Sidecars are listed apart, whatever the extension filter, with their files."""
    for name in ("IMG_1.jpg", "IMG_1.CR2", "IMG_1.xmp", "lone.thm"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "IMG_1").mkdir()
    filters = ScanFilters(extensions=frozenset({".png"}))
    found = asyncio.run(walk((tmp_path,), filters, NullProgress()))
    assert not found.files
    by_name = {s.file.path.name: s for s in found.sidecars}
    assert by_name["IMG_1.xmp"].companions == {"IMG_1.jpg", "IMG_1.CR2"}
    assert by_name["IMG_1.xmp"].file.kind is MediaKind.SIDECAR
    assert by_name["lone.thm"].companions == frozenset()
