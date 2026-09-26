"""Describe how an image looks: perceptual hashes, sharpness, when and with what.

Computed on the image the integrity check has just decoded, in the same worker: the
file is never read twice. Hashes follow the usual dHash (gradient of a 9 x 8 thumbnail)
and pHash (low frequencies of the DCT of a 32 x 32 thumbnail). Sharpness is the variance
of the Laplacian, as digiKam's blur detection, on a thumbnail of fixed size so that
shots of one series compare fairly.
"""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Final

import numpy as np
from PIL import Image, ImageOps

from media_dedup.scan.models import VisualFacts

if TYPE_CHECKING:
    from numpy.typing import NDArray

ANALYSIS_EDGE: Final = 512
_HASH_SIDE: Final = 8
_DCT_SIDE: Final = 32
_ORIENTATION_TAG: Final = 0x0112
_EXIF_IFD: Final = 0x8769
_DATE_TAG: Final = 0x9003
_SUBSEC_TAG: Final = 0x9291
_MAKE_TAG: Final = 0x010F
_MODEL_TAG: Final = 0x0110
_QUARTER_TURNS: Final = frozenset({5, 6, 7, 8})


def visual_facts(image: Image.Image, stored_size: tuple[int, int]) -> VisualFacts:
    """Describe a decoded image.

    Args:
        image: The image, loaded (possibly drafted: decoded at a reduced scale).
        stored_size: Its full size as stored in the file, before any rotation.

    Returns:
        Its visual facts.
    """
    exif = image.getexif()
    upright = ImageOps.exif_transpose(image)
    gray = upright.convert("L")
    width, height = stored_size
    if exif.get(_ORIENTATION_TAG) in _QUARTER_TURNS:
        width, height = height, width
    return VisualFacts(
        dhash=_dhash(gray),
        phash=_phash(gray),
        width=width,
        height=height,
        sharpness=_sharpness(gray),
        taken_at=_taken_at(exif),
        camera=_camera(exif),
    )


def _pixels(gray: Image.Image, size: tuple[int, int]) -> NDArray[np.float64]:
    """Resize a grayscale image and return its pixels as floats.

    Args:
        gray: A grayscale image.
        size: Target width and height.

    Returns:
        A `height x width` array.
    """
    small = gray.resize(size, Image.Resampling.LANCZOS)
    return np.asarray(small, dtype=np.float64)


def _as_int(bits: NDArray[np.bool_]) -> int:
    """Pack 64 booleans into an integer, first bit most significant.

    Args:
        bits: The bits, in any shape.

    Returns:
        The integer.
    """
    return int("".join("1" if bit else "0" for bit in bits.flatten()), 2)


def _dhash(gray: Image.Image) -> int:
    """Difference hash: is each pixel brighter than its right neighbour?

    Args:
        gray: A grayscale image.

    Returns:
        A 64-bit hash.
    """
    pixels = _pixels(gray, (_HASH_SIDE + 1, _HASH_SIDE))
    return _as_int(pixels[:, 1:] > pixels[:, :-1])


@cache
def _dct_matrix() -> NDArray[np.float64]:
    """Rows of the DCT-II basis for the lowest frequencies.

    Returns:
        A `8 x 32` matrix.
    """
    frequencies = np.arange(_HASH_SIDE)[:, None]
    positions = np.arange(_DCT_SIDE)[None, :]
    return np.cos(np.pi * (2 * positions + 1) * frequencies / (2 * _DCT_SIDE))


def _phash(gray: Image.Image) -> int:
    """Perceptual hash: which low frequencies are above their median?

    Args:
        gray: A grayscale image.

    Returns:
        A 64-bit hash.
    """
    basis = _dct_matrix()
    low = basis @ _pixels(gray, (_DCT_SIDE, _DCT_SIDE)) @ basis.T
    return _as_int(low > np.median(low))


def _sharpness(gray: Image.Image) -> float:
    """Variance of the Laplacian: high for crisp edges, low for a blurred shot.

    Args:
        gray: A grayscale image.

    Returns:
        The score, rounded to one decimal.
    """
    small = gray.copy()
    small.thumbnail((ANALYSIS_EDGE, ANALYSIS_EDGE))
    pixels = np.asarray(small, dtype=np.float64)
    laplacian = (
        pixels[:-2, 1:-1]
        + pixels[2:, 1:-1]
        + pixels[1:-1, :-2]
        + pixels[1:-1, 2:]
        - 4 * pixels[1:-1, 1:-1]
    )
    return round(float(laplacian.var()), 1) if laplacian.size else 0.0


def _text(value: object) -> str | None:
    """Clean an EXIF text value (bytes or str, padded with NULs or spaces).

    Args:
        value: The raw value.

    Returns:
        The text, or None when empty.
    """
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    if not isinstance(value, str):
        return None
    return value.strip("\x00 ").strip() or None


def _taken_at(exif: Image.Exif) -> str | None:
    """When the shot was taken, with sub-seconds when recorded (bursts share seconds).

    Args:
        exif: The image's EXIF.

    Returns:
        `YYYY:MM:DD HH:MM:SS[.fraction]`, or None.
    """
    details = exif.get_ifd(_EXIF_IFD)
    taken = _text(details.get(_DATE_TAG))
    subsec = _text(details.get(_SUBSEC_TAG))
    if taken is None:
        return None
    return f"{taken}.{subsec}" if subsec else taken


def _camera(exif: Image.Exif) -> str | None:
    """Which device took the shot.

    Args:
        exif: The image's EXIF.

    Returns:
        Make and model, or None.
    """
    parts = (_text(exif.get(_MAKE_TAG)), _text(exif.get(_MODEL_TAG)))
    return " ".join(part for part in parts if part) or None
