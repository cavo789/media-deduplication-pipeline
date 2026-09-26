"""Small JPEG previews for the report, generated in worker processes."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from PIL import Image, ImageFile, ImageOps

from media_dedup.constants import THUMBNAILS_DIR_NAME, MediaKind, Sizes
from media_dedup.scan.image_check import prepare_image_worker

if TYPE_CHECKING:
    from collections.abc import Sequence
    from concurrent.futures import Executor
    from pathlib import Path

    from media_dedup.scan.models import MediaFile

PREVIEWABLE: Final = frozenset({MediaKind.IMAGE})
_JPEG_QUALITY = 80
_THUMBNAIL_NAME_LENGTH = 20
_THUMBNAIL_ERRORS = (
    OSError,
    ValueError,
    SyntaxError,
    EOFError,
    Image.DecompressionBombError,
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
        with Image.open(job.source) as image:
            preview = ImageOps.exif_transpose(image).convert("RGB")
            preview.thumbnail((Sizes.THUMBNAIL_EDGE, Sizes.THUMBNAIL_EDGE))
            job.target.parent.mkdir(parents=True, exist_ok=True)
            preview.save(job.target, "JPEG", quality=_JPEG_QUALITY)
    except _THUMBNAIL_ERRORS:
        return False
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = False
    return True


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
