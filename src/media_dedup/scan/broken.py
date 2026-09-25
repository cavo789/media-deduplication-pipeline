"""Find broken files: empty ones, images that do not decode, videos that do not open."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from media_dedup.constants import BrokenReason, MediaKind
from media_dedup.i18n import _
from media_dedup.scan.image_check import image_problem
from media_dedup.scan.models import BrokenFile
from media_dedup.scan.video_check import video_problem

if TYPE_CHECKING:
    from collections.abc import Sequence

    from media_dedup.index.facts import FileFacts
    from media_dedup.scan.deps import IntegrityTools, ScanDeps
    from media_dedup.scan.models import MediaFile

_CHECKED_KINDS = frozenset({MediaKind.IMAGE, MediaKind.VIDEO})
_EMPTY_DETAIL = "0 bytes"


class BrokenFileFinder:
    """Checks every file once per version; results are cached in the index."""

    def __init__(self, deps: ScanDeps, tools: IntegrityTools) -> None:
        """Keep the shared collaborators and the checking tools.

        Args:
            deps: Index, progress sink and I/O concurrency limit.
            tools: Image-decoding pool and optional `ffprobe`.
        """
        self._deps = deps
        self._tools = tools

    async def find(self, files: Sequence[MediaFile]) -> tuple[BrokenFile, ...]:
        """Return the broken files among `files`.

        RAW files are only checked for emptiness (no decoder), and videos are skipped
        when `ffprobe` is unavailable.

        Args:
            files: Every media file found.

        Returns:
            The broken files, sorted by path.
        """
        repository = self._deps.repository
        broken = [
            BrokenFile(file, BrokenReason.EMPTY, _EMPTY_DETAIL)
            for file in files
            if file.size == 0
        ]
        to_check: list[MediaFile] = []
        for file in files:
            if file.size == 0 or not self._can_check(file):
                continue
            facts = repository.get(file)
            if facts.integrity_checked:
                broken.extend(_as_broken(file, facts))
            else:
                to_check.append(file)
        self._deps.progress.start(_("Checking that files can be read"), len(to_check))
        async with asyncio.TaskGroup() as group:
            tasks = {file: group.create_task(self._check(file)) for file in to_check}
        self._deps.progress.stop()
        for file, task in tasks.items():
            facts = task.result()
            repository.put(file, facts)
            broken.extend(_as_broken(file, facts))
        return tuple(sorted(broken, key=lambda item: str(item.file.path)))

    def _can_check(self, file: MediaFile) -> bool:
        """Tell whether a decoder exists for this file.

        Args:
            file: Candidate file.

        Returns:
            True for images, and for videos when `ffprobe` is available.
        """
        if file.kind is MediaKind.VIDEO:
            return self._tools.ffprobe is not None
        return file.kind in _CHECKED_KINDS

    async def _check(self, file: MediaFile) -> FileFacts:
        """Check one file and return its updated facts.

        Args:
            file: File to check.

        Returns:
            Its facts, including the integrity outcome.
        """
        try:
            if file.kind is MediaKind.VIDEO and self._tools.ffprobe is not None:
                async with self._deps.io_slots:
                    problem = await video_problem(file.path, self._tools.ffprobe)
                reason = BrokenReason.UNREADABLE_VIDEO
            else:
                loop = asyncio.get_running_loop()
                problem = await loop.run_in_executor(
                    self._tools.executor, image_problem, file.path
                )
                reason = BrokenReason.UNREADABLE_IMAGE
        finally:
            self._deps.progress.advance()
        facts = self._deps.repository.get(file)
        return facts.with_integrity(reason if problem else None, problem or "")


def _as_broken(file: MediaFile, facts: FileFacts) -> list[BrokenFile]:
    """Turn cached facts into a broken-file record when they say so.

    Args:
        file: The file.
        facts: Its integrity facts.

    Returns:
        One record when broken, none otherwise.
    """
    if facts.broken_reason is None:
        return []
    return [BrokenFile(file, facts.broken_reason, facts.broken_detail)]
