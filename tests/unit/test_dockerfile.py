"""The image's own ffprobe keeps a demuxer for every video extension analysed."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from media_dedup.constants import VIDEO_EXTENSIONS

ROOT: Final = Path(__file__).resolve().parents[2]
DEMUXER_MAP: Final = re.compile(
    r"^# Demuxers per video extension: (?P<map>(?:.*\n#)*.*)$", re.MULTILINE
)
ENABLED: Final = re.compile(r"--enable-demuxer=(?P<names>[a-z0-9,]+)")


def test_every_video_extension_has_its_demuxer() -> None:
    """A new video extension needs its demuxer in the ffprobe stage and its comment."""
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    documented = DEMUXER_MAP.search(dockerfile)
    enabled = ENABLED.search(dockerfile)
    assert documented is not None
    assert enabled is not None
    words = set(re.findall(r"[a-z0-9]+", documented["map"]))
    assert {extension.lstrip(".") for extension in VIDEO_EXTENSIONS} <= words
    assert set(enabled["names"].split(",")) <= words
