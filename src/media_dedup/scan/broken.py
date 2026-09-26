"""Find broken files (empty, undecodable, unopenable) and describe readable images."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from media_dedup.constants import BrokenReason, MediaKind
from media_dedup.i18n import _
from media_dedup.scan.image_check import inspect_image
from media_dedup.scan.models import BrokenFile
from media_dedup.scan.progress import Step
from media_dedup.scan.raw_check import inspect_raw
from media_dedup.scan.video_check import video_problem

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from media_dedup.index.facts import FileFacts
    from media_dedup.scan.deps import IntegrityTools, ScanDeps
    from media_dedup.scan.image_check import ImageInspection
    from media_dedup.scan.models import MediaFile, VisualFacts

type _Decoder = Callable[[Path], ImageInspection]

# Decoded in worker processes; videos are opened by `ffprobe` instead.
_DECODERS: Final[Mapping[MediaKind, tuple[_Decoder, BrokenReason]]] = MappingProxyType(
    {
        MediaKind.IMAGE: (inspect_image, BrokenReason.UNREADABLE_IMAGE),
        MediaKind.RAW: (inspect_raw, BrokenReason.UNREADABLE_RAW),
    }
)
# Other files (asked for with --ext) are never checked: nothing says what they hold.
_MEDIA_KINDS: Final = frozenset({MediaKind.IMAGE, MediaKind.RAW, MediaKind.VIDEO})
_EMPTY_DETAIL = "0 bytes"


@dataclass(frozen=True, slots=True)
class IntegrityFindings:
    """Broken files, and what every readable image looks like."""

    broken: tuple[BrokenFile, ...]
    visuals: Mapping[Path, VisualFacts]


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

    async def find(self, files: Sequence[MediaFile]) -> IntegrityFindings:
        """Return the broken files among `files`, and describe the readable images.

        Images are decoded by Pillow, RAW files by LibRaw, videos opened by `ffprobe`
        (skipped when it is unavailable). Other files are never broken, even empty:
        an empty file can be a marker a program needs.

        Args:
            files: Every media file found.

        Returns:
            The broken files, sorted by path, and the visual facts of images.
        """
        repository = self._deps.repository
        broken = [
            BrokenFile(file, BrokenReason.EMPTY, _EMPTY_DETAIL)
            for file in files
            if file.size == 0 and file.kind in _MEDIA_KINDS
        ]
        to_check: list[MediaFile] = []
        known: dict[Path, FileFacts] = {}
        for file in files:
            if file.size == 0 or not self._can_check(file):
                continue
            facts = repository.get(file)
            if _is_complete(file, facts):
                known[file.path] = facts
            else:
                to_check.append(file)
        step = Step(
            _("Checking that files can be read"),
            _(
                "Finds broken files: empty (0 bytes), images and RAW files that cannot "
                "be decoded, videos that cannot be opened."
            ),
        )
        self._deps.progress.start(step, len(to_check))
        async with asyncio.TaskGroup() as group:
            tasks = {file: group.create_task(self._check(file)) for file in to_check}
        self._deps.progress.stop()
        for file, task in tasks.items():
            repository.put(file, task.result())
            known[file.path] = task.result()
        by_path = {file.path: file for file in files}
        broken.extend(
            item
            for path, facts in known.items()
            for item in _as_broken(by_path[path], facts)
        )
        return IntegrityFindings(
            broken=tuple(sorted(broken, key=lambda item: str(item.file.path))),
            visuals=MappingProxyType(
                {path: facts.visual for path, facts in known.items() if facts.visual}
            ),
        )

    def _can_check(self, file: MediaFile) -> bool:
        """Tell whether a decoder exists for this file.

        Args:
            file: Candidate file.

        Returns:
            True for images and RAW files, and for videos when `ffprobe` is available.
        """
        if file.kind is MediaKind.VIDEO:
            return self._tools.ffprobe is not None
        return file.kind in _DECODERS

    async def _check(self, file: MediaFile) -> FileFacts:
        """Check one file and return its updated facts.

        Args:
            file: File to check.

        Returns:
            Its facts, including the integrity outcome.
        """
        facts = self._deps.repository.get(file)
        try:
            if file.kind is MediaKind.VIDEO and self._tools.ffprobe is not None:
                async with self._deps.io_slots:
                    problem = await video_problem(file.path, self._tools.ffprobe)
                reason = BrokenReason.UNREADABLE_VIDEO
            else:
                decode, reason = _DECODERS[file.kind]
                loop = asyncio.get_running_loop()
                inspection = await loop.run_in_executor(
                    self._tools.executor, decode, file.path
                )
                problem = inspection.problem
                facts = facts.with_visual(inspection.visual)
        finally:
            self._deps.progress.advance()
        return facts.with_integrity(reason if problem else None, problem or "")


def _is_complete(file: MediaFile, facts: FileFacts) -> bool:
    """Tell whether the index already knows all a check would compute.

    Images checked by an older version still lack their visual facts: they are
    decoded again once.

    Args:
        file: The file.
        facts: What the index knows about it.

    Returns:
        True when nothing needs computing.
    """
    if file.kind is MediaKind.IMAGE:
        return facts.integrity_checked and facts.visual_checked
    return facts.integrity_checked


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
