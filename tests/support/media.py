"""Create real media files (JPEG, PNG, HEIC, MP4) and their broken variants."""

from __future__ import annotations

import os
import random
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pillow_heif
from PIL import Image

if TYPE_CHECKING:
    from pathlib import Path

IMAGE_SIZE: Final = (96, 64)
DAY_NS: Final = 86_400 * 1_000_000_000
BASE_TIME_NS: Final = 1_700_000_000 * 1_000_000_000
FFMPEG: Final = shutil.which("ffmpeg")


@dataclass(frozen=True, slots=True)
class MediaFactory:
    """Writes media files below `root`; each `seed` gives a distinct picture."""

    root: Path

    def _target(self, relative: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def image(self, relative: str, seed: int = 0) -> Path:
        """Write a noise image; the format follows the extension (JPEG, PNG, HEIC).

        Args:
            relative: Path below the root.
            seed: Picture identity: same seed, same pixels.

        Returns:
            The file written.
        """
        noise = random.Random(seed).randbytes(  # noqa: S311 - test pixels, not secrets
            IMAGE_SIZE[0] * IMAGE_SIZE[1] * 3
        )
        picture = Image.frombytes("RGB", IMAGE_SIZE, noise)
        path = self._target(relative)
        if path.suffix.casefold() == ".heic":
            pillow_heif.from_pillow(picture).save(path, quality=90)
        else:
            picture.save(path)
        return age(path, seed)

    def copy(self, source: Path, relative: str) -> Path:
        """Copy a file byte for byte, keeping its modification time.

        Args:
            source: File to copy.
            relative: Destination below the root.

        Returns:
            The copy.
        """
        target = self._target(relative)
        shutil.copy2(source, target)
        return target

    def empty(self, relative: str) -> Path:
        """Write a 0-byte media file.

        Args:
            relative: Path below the root.

        Returns:
            The file written.
        """
        path = self._target(relative)
        path.touch()
        return path

    def truncated(self, source: Path, relative: str) -> Path:
        """Write the first half of `source`: a typical interrupted copy.

        Args:
            source: Healthy file.
            relative: Destination below the root.

        Returns:
            The broken file.
        """
        path = self._target(relative)
        data = source.read_bytes()
        path.write_bytes(data[: len(data) // 2])
        return path

    def video(self, relative: str) -> Path:
        """Encode a short test video with ffmpeg (moov atom at the end, like cameras).

        Args:
            relative: Path below the root.

        Returns:
            The video written.
        """
        path = self._target(relative)
        source = "testsrc=duration=2:size=160x120:rate=10"
        command = [FFMPEG or "ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi"]
        command += ["-i", source, "-pix_fmt", "yuv420p", str(path)]
        subprocess.run(command, check=True)  # noqa: S603 - fixed, trusted arguments
        return path


def age(path: Path, days: int) -> Path:
    """Set the modification time to a fixed date plus `days` days.

    Args:
        path: File to date.
        days: Offset in days (older files have smaller offsets).

    Returns:
        The same path.
    """
    stamp = BASE_TIME_NS + days * DAY_NS
    os.utime(path, ns=(stamp, stamp))
    return path
