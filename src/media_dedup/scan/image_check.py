"""Decode an image fully to prove it is readable — run in worker processes."""

from __future__ import annotations

import struct
import warnings
from typing import TYPE_CHECKING, Final

import pillow_heif
from PIL import Image

from media_dedup.constants import Sizes

if TYPE_CHECKING:
    from pathlib import Path

# A corrupt file can make a decoder raise almost anything: all mean "unreadable".
_DECODE_ERRORS: Final = (
    OSError,
    SyntaxError,
    ValueError,
    EOFError,
    struct.error,
    Image.DecompressionBombError,
    TypeError,
    IndexError,
    ZeroDivisionError,
    MemoryError,
)


def prepare_image_worker() -> None:
    """Configure Pillow in a worker: HEIC support, no pixel limit.

    Huge panoramas are legitimate photos, not decompression bombs to refuse: without
    lifting the limit they would be reported as broken.
    """
    pillow_heif.register_heif_opener()
    Image.MAX_IMAGE_PIXELS = None


def image_problem(path: Path) -> str | None:
    """Verify the structure of an image, then decode it (downscaled for JPEG speed).

    Args:
        path: Image file.

    Returns:
        The decoder error, or None when the image is readable.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                size = (
                    max(1, image.width // Sizes.JPEG_DRAFT_DIVISOR),
                    max(1, image.height // Sizes.JPEG_DRAFT_DIVISOR),
                )
                image.draft("RGB", size)
                image.load()
        except _DECODE_ERRORS as exc:
            return f"{type(exc).__name__}: {exc}"
    return None
