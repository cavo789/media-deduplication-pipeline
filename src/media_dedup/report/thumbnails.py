"""JPEG previews, generated in worker processes: small for reports, large for review."""

from __future__ import annotations

import asyncio
import hashlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from PIL import Image, ImageFile, ImageOps

from media_dedup.constants import THUMBNAILS_DIR_NAME, MediaKind, Sizes
from media_dedup.scan.filters import media_kind
from media_dedup.scan.image_check import prepare_image_worker
from media_dedup.scan.raw_check import RAW_ERRORS, raw_preview

if TYPE_CHECKING:
    from collections.abc import Sequence
    from concurrent.futures import Executor
    from pathlib import Path

    from media_dedup.scan.models import MediaFile

PREVIEWABLE: Final = frozenset({MediaKind.IMAGE, MediaKind.RAW})
_JPEG_QUALITY = 80
# Large enough to judge sharpness on a screen, small enough to load at once.
_REVIEW_EDGE: Final = 1600
_REVIEW_QUALITY: Final = 88
_THUMBNAIL_NAME_LENGTH = 20
_THUMBNAIL_ERRORS = (
    ValueError,
    SyntaxError,
    EOFError,
    Image.DecompressionBombError,
    *RAW_ERRORS,
)


def thumbnail_name(file: MediaFile) -> str:
    """Return a stable, collision-free preview file name for `file`.

    Args:
        file: The media file.

    Returns:
        A relative path such as `thumbs/0f3a....jpg`.
    """
    digest = hashlib.sha256(str(file.path).encode()).hexdigest()[
        :_THUMBNAIL_NAME_LENGTH
    ]
    return f"{THUMBNAILS_DIR_NAME}/{digest}.jpg"


@dataclass(frozen=True, slots=True)
class ThumbnailJob:
    """Render `source` as a preview at `target`."""

    source: Path
    target: Path


def make_thumbnail(job: ThumbnailJob) -> bool:
    """Write a preview, tolerating truncated images (a partial preview helps decide).

    Args:
        job: Source image and target file.

    Returns:
        True when the preview was written.
    """
    prepare_image_worker()
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        preview = _upright(job.source)
        preview.thumbnail((Sizes.THUMBNAIL_EDGE, Sizes.THUMBNAIL_EDGE))
        job.target.parent.mkdir(parents=True, exist_ok=True)
        preview.save(job.target, "JPEG", quality=_JPEG_QUALITY)
    except _THUMBNAIL_ERRORS:
        return False
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = False
    return True


def review_preview(source: Path) -> bytes | None:
    """Render a picture for the review page, tolerating truncated images.

    Args:
        source: Image or RAW file.

    Returns:
        The JPEG bytes, or None when the picture cannot be decoded.
    """
    prepare_image_worker()
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        preview = _upright(source)
        preview.thumbnail((_REVIEW_EDGE, _REVIEW_EDGE))
        buffer = io.BytesIO()
        preview.save(buffer, "JPEG", quality=_REVIEW_QUALITY)
    except (*_THUMBNAIL_ERRORS, OSError):
        return None
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = False
    return buffer.getvalue()


def _upright(source: Path) -> Image.Image:
    """Open a picture as seen: an image, or the preview embedded in a RAW file.

    Args:
        source: Image or RAW file.

    Returns:
        The picture, upright, in RGB.
    """
    if media_kind(source) is MediaKind.RAW:
        return raw_preview(source).convert("RGB")
    with Image.open(source) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


async def make_thumbnails(
    jobs: Sequence[ThumbnailJob], executor: Executor
) -> set[Path]:
    """Render every preview in parallel.

    Args:
        jobs: Previews to render.
        executor: Pool running `make_thumbnail`.

    Returns:
        The targets actually written.
    """
    loop = asyncio.get_running_loop()
    results = await asyncio.gather(
        *(loop.run_in_executor(executor, make_thumbnail, job) for job in jobs),
    )
    return {job.target for job, written in zip(jobs, results, strict=True) if written}
