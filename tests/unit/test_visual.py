"""What images look like: copies found near, bursts and other scenes not, sharpness."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from media_dedup.plan.near import is_near
from media_dedup.scan.image_check import inspect_image, prepare_image_worker
from tests.support.scenes import Effect, Shot, write_shot

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.scan.models import VisualFacts

DATE = "2019:06:12 14:30:12"
ORIGINAL = Shot(1, size=(960, 720), taken_at=DATE)


def visual_of(path: Path, shot: Shot) -> VisualFacts:
    """Write a shot and describe it."""
    prepare_image_worker()
    visual = inspect_image(write_shot(path, shot)).visual
    assert visual is not None
    return visual


@pytest.mark.parametrize(
    "copy",
    [
        Shot(1, size=(480, 360), taken_at=DATE),  # resized, EXIF kept
        Shot(1, size=(960, 720), taken_at=DATE, quality=35),  # recompressed
        Shot(1, size=(960, 720), camera=False),  # EXIF stripped by an upload
        Shot(1, size=(960, 720), taken_at=DATE, effect=Effect.ROTATED),
    ],
    ids=["resized", "recompressed", "stripped", "rotated"],
)
def test_copies_are_near(tmp_path: Path, copy: Shot) -> None:
    """Every usual kind of copy is a near duplicate of the original."""
    original = visual_of(tmp_path / "original.jpg", ORIGINAL)
    assert is_near(original, visual_of(tmp_path / "copy.jpg", copy))


def test_a_rotated_copy_keeps_its_displayed_size(tmp_path: Path) -> None:
    """Stored sideways with an orientation tag: width and height as displayed."""
    turned = Shot(1, size=(960, 720), effect=Effect.ROTATED)
    rotated = visual_of(tmp_path / "r.jpg", turned)
    assert (rotated.width, rotated.height) == (960, 720)


def test_bursts_and_other_scenes_are_not_near(tmp_path: Path) -> None:
    """The next shot of a burst (another second) and another scene never qualify."""
    original = visual_of(tmp_path / "original.jpg", ORIGINAL)
    burst = Shot(1, size=(960, 720), shift=6, taken_at="2019:06:12 14:30:13")
    other = Shot(2, size=(960, 720), taken_at=DATE)
    assert not is_near(original, visual_of(tmp_path / "burst.jpg", burst))
    assert not is_near(original, visual_of(tmp_path / "other.jpg", other))


def test_a_blurred_shot_is_less_sharp(tmp_path: Path) -> None:
    """The variance of the Laplacian drops with blur."""
    sharp = visual_of(tmp_path / "sharp.jpg", ORIGINAL)
    blurred = visual_of(
        tmp_path / "blurred.jpg",
        Shot(1, size=(960, 720), taken_at=DATE, effect=Effect.BLURRED),
    )
    assert blurred.sharpness * 10 < sharp.sharpness


def test_exif_date_and_camera(tmp_path: Path) -> None:
    """The date and the camera come from EXIF; nothing when there is no EXIF."""
    with_exif = visual_of(tmp_path / "a.jpg", ORIGINAL)
    assert (with_exif.taken_at, with_exif.camera) == (DATE, "Canon EOS 80D")
    bare = visual_of(tmp_path / "b.jpg", Shot(1, camera=False))
    assert (bare.taken_at, bare.camera) == (None, None)


def test_unreadable_images_have_no_visual_facts(tmp_path: Path) -> None:
    """A truncated JPEG is a problem, not a picture."""
    whole = write_shot(tmp_path / "whole.jpg", ORIGINAL)
    cut = tmp_path / "cut.jpg"
    cut.write_bytes(whole.read_bytes()[:500])
    inspection = inspect_image(cut)
    assert inspection.problem is not None
    assert inspection.visual is None
