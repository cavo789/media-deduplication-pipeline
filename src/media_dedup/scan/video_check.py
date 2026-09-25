"""Ask `ffprobe` whether a video container can be opened."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

_LOGGER = logging.getLogger(__name__)
_TIMEOUT_SECONDS: Final = 60
_PROBE_ARGS: Final = (
    "-v",
    "error",
    "-show_entries",
    "stream=codec_type",
    "-of",
    "json",
)


async def video_problem(path: Path, ffprobe: str) -> str | None:
    """Probe a video: a container ffprobe cannot open, or without any stream, is broken.

    A probe that times out is inconclusive: the file is then considered healthy.

    Args:
        path: Video file.
        ffprobe: Path of the `ffprobe` executable.

    Returns:
        The probe error, or None when the video looks readable.
    """
    process = await asyncio.create_subprocess_exec(
        ffprobe,
        *_PROBE_ARGS,
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            stdout, stderr = await process.communicate()
    except TimeoutError:
        process.kill()
        await process.wait()
        _LOGGER.warning("ffprobe timed out on %s: kept as healthy", path)
        return None
    if process.returncode != 0:
        lines = stderr.decode(errors="replace").strip().splitlines()
        return lines[-1] if lines else f"ffprobe exit code {process.returncode}"
    streams = json.loads(stdout or b"{}").get("streams", [])
    return None if streams else "no audio or video stream"
