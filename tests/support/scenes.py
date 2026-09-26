"""Structured test pictures (shapes, not noise) with EXIF: hashes behave as on photos.

Random noise averages out to flat gray once reduced to a hash thumbnail, so near
duplicates and bursts are tested on drawn scenes instead.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from PIL import Image, ImageDraw, ImageFilter

from tests.support.media import age

if TYPE_CHECKING:
    from pathlib import Path

SCENE_SIZE: Final = (480, 360)
_SKY: Final = (200, 220, 240)
_SHAPES: Final = 25
_EXIF_IFD: Final = 0x8769
_DATE_TAG: Final = 0x9003
_MAKE_TAG: Final = 0x010F
_MODEL_TAG: Final = 0x0110
_ORIENTATION_TAG: Final = 0x0112
_QUARTER_TURN_CLOCKWISE: Final = 6
_BLUR_RADIUS: Final = 3.0


class Effect(StrEnum):
    """What happened to a shot besides its size and quality."""

    NONE = "none"
    BLURRED = "blurred"  # a shaken shot
    ROTATED = "rotated"  # stored sideways, displayed upright (a phone's portrait)


@dataclass(frozen=True, slots=True)
class Shot:
    """How to write one test picture."""

    seed: int
    size: tuple[int, int] = SCENE_SIZE
    shift: int = 0
    taken_at: str | None = None
    camera: bool = True
    quality: int = 92
    effect: Effect = Effect.NONE


def scene(seed: int, size: tuple[int, int] = SCENE_SIZE, shift: int = 0) -> Image.Image:
    """Draw a scene of shapes; the same seed gives the same scene.

    Args:
        seed: Scene identity.
        size: Width and height.
        shift: Horizontal offset of every shape (a camera that moved a little).

    Returns:
        The picture.
    """
    picture = Image.new("RGB", size, _SKY)
    draw = ImageDraw.Draw(picture)
    rnd = random.Random(seed)  # noqa: S311 - test pictures, not secrets
    width, height = size
    for _ in range(_SHAPES):
        left, top = rnd.randrange(width) + shift, rnd.randrange(height)
        box = (
            left,
            top,
            left + rnd.randrange(width // 10, width // 3),
            top + rnd.randrange(height // 10, height // 3),
        )
        colour = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
        shape = draw.ellipse if rnd.random() < 0.5 else draw.rectangle
        shape(box, fill=colour)
    return picture


def write_shot(path: Path, shot: Shot) -> Path:
    """Write a JPEG of the scene, with the EXIF of a camera when asked.

    Args:
        path: Target file (its folder is created).
        shot: The picture to write.

    Returns:
        The file written, dated with its seed like the other test media.
    """
    picture = scene(shot.seed, SCENE_SIZE, shot.shift).resize(shot.size)
    if shot.effect is Effect.BLURRED:
        picture = picture.filter(ImageFilter.GaussianBlur(_BLUR_RADIUS))
    exif = Image.Exif()
    if shot.camera:
        exif[_MAKE_TAG], exif[_MODEL_TAG] = "Canon", "EOS 80D"
    if shot.taken_at:
        exif.get_ifd(_EXIF_IFD)[_DATE_TAG] = shot.taken_at
    if shot.effect is Effect.ROTATED:
        picture = picture.rotate(90, expand=True)
        exif[_ORIENTATION_TAG] = _QUARTER_TURN_CLOCKWISE
    path.parent.mkdir(parents=True, exist_ok=True)
    picture.save(path, "JPEG", quality=shot.quality, exif=exif)
    return age(path, shot.seed)
