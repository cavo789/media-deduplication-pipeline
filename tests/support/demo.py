"""Build a realistic demo tree: `python -m tests.support.demo <data dir>` (demo helper).

Layout, with the /data/<drive letter>/<path> convention of the image:
exact copies across "C:" and "D:", Windows-style "(1)" copies, an empty file,
a truncated JPEG, HEIC and MP4 duplicates, a broken video, sidecars (each one keeps
its photo, except where two copies have their own: one is left orphan by the clean),
a burst of similar-but-different photos that must never be touched (one of them
blurred), and one photo saved again smaller (WhatsApp) and recompressed without its
date.
"""

from __future__ import annotations

import sys
from pathlib import Path

from tests.support.media import FFMPEG, MediaFactory
from tests.support.scenes import Effect, Shot, write_shot

_PHOTOS = "c/Family Photos"
_PICTURES = "c/Users/Public/Pictures"
_BACKUP = "d/backup"
_BURST_SIZE = 4
_BURST_SEED = 100
_BLURRED_SHOT = 2
_BEACH_SEED = 200
_WHATSAPP_SIZE = (240, 180)


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
    (data_dir / _BACKUP / "2019/IMG_0002.AAE").write_text("<plist/>")
    (data_dir / _PICTURES / "Été 2019/IMG_0002.xmp").write_text("<x:xmpmeta/>")
    for shot in range(_BURST_SIZE):
        write_shot(
            data_dir / f"{_PHOTOS}/Rafale/IMG_20{shot}.jpg",
            Shot(
                _BURST_SEED,
                shift=4 * shot,
                taken_at=f"2021:07:04 10:15:0{shot}",
                effect=Effect.BLURRED if shot == _BLURRED_SHOT else Effect.NONE,
            ),
        )
    _near_duplicates(data_dir)
    if FFMPEG is not None:
        video = media.video(f"{_PHOTOS}/Vidéos/anniversaire.mp4")
        media.copy(video, f"{_BACKUP}/Vidéos/anniversaire.mp4")
        media.truncated(video, f"{_BACKUP}/Vidéos/anniversaire-coupée.mp4")


def _near_duplicates(data_dir: Path) -> None:
    """One beach photo, saved again smaller and recompressed without EXIF.

    Args:
        data_dir: Directory standing for the /data mount point.
    """
    date = "2021:07:05 16:20:00"
    write_shot(data_dir / f"{_PHOTOS}/2021/Plage.jpg", Shot(_BEACH_SEED, taken_at=date))
    write_shot(
        data_dir / f"{_PICTURES}/WhatsApp/IMG-20210705-WA0001.jpg",
        Shot(_BEACH_SEED, size=_WHATSAPP_SIZE, camera=False, quality=70),
    )
    write_shot(
        data_dir / f"{_BACKUP}/email/Plage (petite).jpg",
        Shot(_BEACH_SEED, camera=False, quality=40),
    )


if __name__ == "__main__":
    build_demo(Path(sys.argv[1]))
