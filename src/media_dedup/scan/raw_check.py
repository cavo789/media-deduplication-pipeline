"""Decode a RAW file with LibRaw to prove it is readable, and read its preview.

Runs in worker processes, like the image checks. RAW files get no visual facts: they
stay out of near duplicates and bursts, whose tests are tuned on JPEG pictures.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Final

import numpy as np
import rawpy
from PIL import ExifTags, Image, ImageOps

# rawpy's package only re-exports these names to type checkers: take them at the source.
from rawpy._rawpy import (
    LibRawError,
    LibRawNoThumbnailError,
    LibRawUnsupportedThumbnailError,
    NotSupportedError,
    ThumbFormat,
)

from media_dedup.scan.image_check import ImageInspection

if TYPE_CHECKING:
    from pathlib import Path

# A damaged RAW file can make LibRaw fail in many ways: all mean "unreadable".
RAW_ERRORS: Final = (LibRawError, NotSupportedError, OSError, MemoryError)
_NO_PREVIEW: Final = (LibRawNoThumbnailError, LibRawUnsupportedThumbnailError)
# LibRaw's `flip`: how the picture must be turned to be seen upright.
_FLIPS: Final = {
    3: Image.Transpose.ROTATE_180,
    5: Image.Transpose.ROTATE_90,
    6: Image.Transpose.ROTATE_270,
}
_UPRIGHT: Final = 1


def inspect_raw(path: Path) -> ImageInspection:
    """Unpack every pixel of a RAW file: a truncated or damaged one fails.

    Args:
        path: RAW file.

    Returns:
        The decoder error, or nothing to report.
    """
    try:
        with rawpy.imread(str(path)) as raw:
            raw.unpack()
    except RAW_ERRORS as exc:
        return ImageInspection(problem=_describe(exc))
    return ImageInspection()


def raw_preview(path: Path) -> Image.Image:
    """Return the preview embedded in a RAW file, upright.

    Cameras embed a JPEG preview; without one, the file is developed at half size.

    Args:
        path: RAW file.

    Returns:
        The preview.
    """
    with rawpy.imread(str(path)) as raw:
        try:
            thumb = raw.extract_thumb()
        except _NO_PREVIEW:
            return Image.fromarray(raw.postprocess(half_size=True))  # already upright
        flip = raw.sizes.flip
    image: Image.Image
    if thumb.format is ThumbFormat.JPEG:
        image = Image.open(io.BytesIO(thumb.data))
        if image.getexif().get(ExifTags.Base.Orientation, _UPRIGHT) != _UPRIGHT:
            return ImageOps.exif_transpose(image)
    else:
        image = Image.fromarray(np.asarray(thumb.data))
    return image.transpose(_FLIPS[flip]) if flip in _FLIPS else image


def _describe(exc: Exception) -> str:
    """Turn a LibRaw error (its message is bytes) into readable text.

    Args:
        exc: The error.

    Returns:
        `<error type>: <message>`.
    """
    message = exc.args[0] if exc.args else ""
    if isinstance(message, bytes):
        message = message.decode(errors="replace")
    return f"{type(exc).__name__}: {message}"
