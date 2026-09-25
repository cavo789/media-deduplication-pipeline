"""Build a realistic demo tree: `python -m tests.support.demo <data dir>` (demo helper).

Layout, with the /data/<drive letter>/<path> convention of the image:
exact copies across "C:" and "D:", Windows-style "(1)" copies, an empty file,
a truncated JPEG, HEIC and MP4 duplicates, a broken video, a sidecar, and a
burst of similar-but-different photos that must never be touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

from tests.support.media import FFMPEG, MediaFactory

_PHOTOS = "c/Family Photos"
_PICTURES = "c/Users/Public/Pictures"
_BACKUP = "d/backup"
_BURST_SIZE = 5
_BURST_SEED = 100


def build_demo(data_dir: Path) -> None:
    """Populate `data_dir` with the demo media.

    Args:
        data_dir: Directory standing for the /data mount point.
    """
    media = MediaFactory(data_dir)
    for index in range(1, 4):
        original = media.image(
            f"{_PHOTOS}/2019/Vacances/IMG_000{index}.jpg", seed=index
        )
        media.copy(original, f"{_PICTURES}/Été 2019/IMG_000{index}.jpg")
        media.copy(original, f"{_BACKUP}/2019/IMG_000{index}.jpg")
    first = data_dir / _PHOTOS / "2019/Vacances/IMG_0001.jpg"
    media.copy(first, f"{_PHOTOS}/2019/Vacances/IMG_0001 (1).jpg")
    heic = media.image(f"{_PHOTOS}/iPhone/IMG_4242.HEIC", seed=42)
    media.copy(heic, f"{_BACKUP}/iPhone/IMG_4242.HEIC")
    media.image(f"{_PICTURES}/Noël/scan.png", seed=7)
    media.empty(f"{_BACKUP}/2020/IMG_9999.jpg")
    media.truncated(first, f"{_BACKUP}/2020/IMG_0001_interrupted.jpg")
    (data_dir / _PHOTOS / "2019/Vacances/IMG_0001.xmp").write_text("<x:xmpmeta/>")
    for shot in range(_BURST_SIZE):
        media.image(f"{_PHOTOS}/Rafale/IMG_20{shot}.jpg", seed=_BURST_SEED + shot)
    if FFMPEG is not None:
        video = media.video(f"{_PHOTOS}/Vidéos/anniversaire.mp4")
        media.copy(video, f"{_BACKUP}/Vidéos/anniversaire.mp4")
        media.truncated(video, f"{_BACKUP}/Vidéos/anniversaire-coupée.mp4")


if __name__ == "__main__":
    build_demo(Path(sys.argv[1]))
