"""Collaborators shared by the scan steps, bundled to keep signatures short."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from media_dedup.constants import Sizes

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from media_dedup.index.repository import FactsRepository
    from media_dedup.scan.progress import ProgressSink


@dataclass(frozen=True, slots=True)
class ScanDeps:
    """The index to read/write facts, and where to report progress."""

    repository: FactsRepository
    progress: ProgressSink
    io_slots: asyncio.Semaphore = field(
        default_factory=lambda: asyncio.Semaphore(Sizes.IO_CONCURRENCY),
    )


@dataclass(frozen=True, slots=True)
class IntegrityTools:
    """How to check files: a pool for image decoding, `ffprobe` for videos."""

    executor: Executor
    ffprobe: str | None
