"""Decode an image to prove it is readable, and describe it (in worker processes)."""

from __future__ import annotations

import signal
import struct
import threading
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pillow_heif
from PIL import Image

from media_dedup.scan.visual import ANALYSIS_EDGE, visual_facts

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.scan.models import VisualFacts

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
    """Configure a worker: ignore Ctrl+C, HEIC support, no pixel limit.

    Ctrl+C reaches every process of the terminal; the parent alone handles it, so
    workers never print a `KeyboardInterrupt` traceback. Huge panoramas are
    legitimate photos, not decompression bombs to refuse: without lifting the limit
    they would be reported as broken.
    """
    if threading.current_thread() is threading.main_thread():  # a worker process
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    pillow_heif.register_heif_opener()
    Image.MAX_IMAGE_PIXELS = None


@dataclass(frozen=True, slots=True)
class ImageInspection:
    """Outcome of decoding an image: the decoder error, or what the image looks like."""

    problem: str | None = None
    visual: VisualFacts | None = None


def inspect_image(path: Path) -> ImageInspection:
    """Verify the structure of an image, decode it, then describe it.

    JPEG files are decoded at a reduced scale (still at least `ANALYSIS_EDGE` pixels
    per side when the photo is that large): every byte is still read and checked.

    Args:
        path: Image file.

    Returns:
        The decoder error, or the visual facts of a readable image.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                stored_size = image.size
                image.draft("RGB", (ANALYSIS_EDGE, ANALYSIS_EDGE))
                image.load()
                return ImageInspection(visual=visual_facts(image, stored_size))
        except _DECODE_ERRORS as exc:
            return ImageInspection(problem=f"{type(exc).__name__}: {exc}")
