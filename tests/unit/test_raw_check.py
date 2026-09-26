"""RAW files: decoded by LibRaw to prove them readable, previewed from their JPEG."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from media_dedup.constants import Sizes
from media_dedup.report.thumbnails import ThumbnailJob, make_thumbnail
from media_dedup.scan.raw_check import inspect_raw, raw_preview
from tests.support.dng import SIZE, DngSpec, dng_bytes, write_dng

if TYPE_CHECKING:
    from pathlib import Path

_ROTATED = 6


def test_healthy_raw_is_readable(tmp_path: Path) -> None:
    """Every pixel unpacks; RAW files get no visual facts."""
    inspection = inspect_raw(write_dng(tmp_path / "a.dng", DngSpec()))
    assert inspection.problem is None
    assert inspection.visual is None


def test_truncated_raw_is_broken(tmp_path: Path) -> None:
    """An interrupted copy keeps its header but loses pixels: LibRaw fails."""
    data = dng_bytes(DngSpec())
    cut = tmp_path / "cut.dng"
    cut.write_bytes(data[: len(data) // 2])
    assert inspect_raw(cut).problem == "LibRawIOError: Input/output error"


def test_other_content_is_broken(tmp_path: Path) -> None:
    """A file named .nef that is not a RAW file cannot be decoded."""
    junk = tmp_path / "junk.nef"
    junk.write_bytes(b"not a raw file" * 20)
    problem = inspect_raw(junk).problem
    assert problem is not None
    assert problem.startswith("LibRawFileUnsupportedError: Unsupported file format")


def test_preview_is_the_embedded_jpeg_upright(tmp_path: Path) -> None:
    """The camera's preview is used, turned as the camera held it."""
    assert raw_preview(write_dng(tmp_path / "a.dng", DngSpec())).size == SIZE
    rotated = write_dng(tmp_path / "r.dng", DngSpec(orientation=_ROTATED))
    assert raw_preview(rotated).size == SIZE[::-1]


def test_without_preview_the_raw_is_developed(tmp_path: Path) -> None:
    """No embedded preview: the pixels are developed at half size."""
    path = write_dng(tmp_path / "n.dng", DngSpec(preview=False))
    assert raw_preview(path).size == (SIZE[0] // 2, SIZE[1] // 2)


def test_report_previews_raw_files(tmp_path: Path) -> None:
    """The report gets a thumbnail of a RAW file, not of a broken one."""
    target = tmp_path / "thumbs/a.jpg"
    assert make_thumbnail(
        ThumbnailJob(write_dng(tmp_path / "a.CR2", DngSpec()), target)
    )
    with Image.open(target) as thumbnail:
        assert max(thumbnail.size) <= Sizes.THUMBNAIL_EDGE
    junk = tmp_path / "junk.nef"
    junk.write_bytes(b"not a raw file" * 20)
    assert not make_thumbnail(ThumbnailJob(junk, tmp_path / "thumbs/b.jpg"))
