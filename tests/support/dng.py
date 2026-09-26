"""Write tiny but real DNG files, which LibRaw decodes like a camera's RAW file.

Layout, as cameras write it (metadata first, pixels last, so that a truncated copy
keeps its header): a TIFF header, IFD0 describing the JPEG preview, a sub-IFD
describing the 16-bit Bayer pixels, then the preview, then the pixels.
"""

from __future__ import annotations

import io
import random
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Final

from PIL import Image

if TYPE_CHECKING:
    from pathlib import Path

SIZE: Final = (64, 48)
_HEADER: Final = 8
_WHITE: Final = 4095
_ENTRY: Final = 12
_INLINE: Final = 4


class _Type(IntEnum):
    """TIFF field types, with the struct format of one value."""

    BYTE = 1
    ASCII = 2
    SHORT = 3
    LONG = 4

    @property
    def code(self) -> str:
        """Struct format of one value."""
        return {1: "B", 2: "B", 3: "H", 4: "I"}[self.value]


type _Field = tuple[int, _Type, tuple[int, ...] | str]


@dataclass(frozen=True, slots=True)
class DngSpec:
    """What to write: the picture seed, the EXIF orientation, a preview or not."""

    seed: int = 0
    orientation: int = 1
    preview: bool = True


def dng_bytes(spec: DngSpec) -> bytes:
    """Build a DNG file.

    Args:
        spec: Seed, orientation and preview.

    Returns:
        The whole file.
    """
    width, height = SIZE
    noise = random.Random(spec.seed)  # noqa: S311 - test pixels, not secrets
    jpeg = io.BytesIO()
    if spec.preview:
        picture = Image.frombytes("RGB", SIZE, noise.randbytes(width * height * 3))
        picture.save(jpeg, "JPEG")
    preview = _even(jpeg.getvalue())
    pixels = struct.pack(
        f"<{width * height}H", *(noise.randrange(_WHITE) for _ in range(width * height))
    )
    ifd0_size = len(_ifd(_preview_fields(spec, (0, 0, 0)), 0))
    sub_size = len(_ifd(_raw_fields((0, 0)), 0))
    sub_at = _HEADER + ifd0_size
    preview_at = sub_at + sub_size
    pixels_at = preview_at + len(preview)
    fields = _preview_fields(spec, (preview_at, len(preview), sub_at))
    return b"".join(
        (
            b"II" + struct.pack("<HI", 42, _HEADER),
            _ifd(fields, _HEADER),
            _ifd(_raw_fields((pixels_at, len(pixels))), sub_at),
            preview,
            pixels,
        )
    )


def write_dng(path: Path, spec: DngSpec) -> Path:
    """Write a DNG file.

    Args:
        path: Target file.
        spec: Seed, orientation and preview.

    Returns:
        The same path.
    """
    path.write_bytes(dng_bytes(spec))
    return path


def _preview_fields(spec: DngSpec, where: tuple[int, int, int]) -> list[_Field]:
    """IFD0: camera, DNG version and JPEG preview (offset, size, sub-IFD offset)."""
    width, height = SIZE
    offset, length, sub_ifd = where
    fields: list[_Field] = [
        (254, _Type.LONG, (1,)),
        (256, _Type.LONG, (width,)),
        (257, _Type.LONG, (height,)),
        (271, _Type.ASCII, "Test"),
        (272, _Type.ASCII, "Synthetic"),
        (274, _Type.SHORT, (spec.orientation,)),
        (330, _Type.LONG, (sub_ifd,)),
        (50706, _Type.BYTE, (1, 4, 0, 0)),
        (50708, _Type.ASCII, "Test Synthetic"),
    ]
    if spec.preview:
        fields += [
            (258, _Type.SHORT, (8, 8, 8)),
            (259, _Type.SHORT, (7,)),
            (262, _Type.SHORT, (6,)),
            (273, _Type.LONG, (offset,)),
            (277, _Type.SHORT, (3,)),
            (278, _Type.LONG, (height,)),
            (279, _Type.LONG, (length,)),
        ]
    return fields


def _raw_fields(where: tuple[int, int]) -> list[_Field]:
    """The sub-IFD: uncompressed 16-bit RGGB pixels (offset, size)."""
    width, height = SIZE
    offset, length = where
    return [
        (254, _Type.LONG, (0,)),
        (256, _Type.LONG, (width,)),
        (257, _Type.LONG, (height,)),
        (258, _Type.SHORT, (16,)),
        (259, _Type.SHORT, (1,)),
        (262, _Type.SHORT, (32803,)),
        (273, _Type.LONG, (offset,)),
        (277, _Type.SHORT, (1,)),
        (278, _Type.LONG, (height,)),
        (279, _Type.LONG, (length,)),
        (284, _Type.SHORT, (1,)),
        (33421, _Type.SHORT, (2, 2)),
        (33422, _Type.BYTE, (0, 1, 1, 2)),
        (50717, _Type.LONG, (_WHITE,)),
    ]


def _ifd(fields: list[_Field], start: int) -> bytes:
    """Encode an IFD placed at `start`, its long values right after it."""
    table = struct.pack("<H", len(fields))
    extra = b""
    after = start + 2 + len(fields) * _ENTRY + _INLINE
    for tag, kind, values in sorted(fields):
        raw = (
            values.encode() + b"\0"
            if isinstance(values, str)
            else struct.pack(f"<{len(values)}{kind.code}", *values)
        )
        count = len(raw) // struct.calcsize(kind.code)
        if len(raw) <= _INLINE:
            table += struct.pack("<HHI", tag, kind, count) + raw.ljust(_INLINE, b"\0")
        else:
            table += struct.pack("<HHII", tag, kind, count, after + len(extra))
            extra += _even(raw)
    return table + struct.pack("<I", 0) + extra


def _even(data: bytes) -> bytes:
    """Pad to an even length: TIFF offsets are word-aligned."""
    return data + b"\0" * (len(data) % 2)
