"""Find exact duplicates: same size, then same partial digest, then same SHA-256."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.i18n import _
from media_dedup.index.facts import FileFacts
from media_dedup.scan.hashing import full_digest, partial_digest
from media_dedup.scan.models import DuplicateGroup, MediaFile
from media_dedup.scan.progress import Step

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterable, Sequence
    from pathlib import Path

    from media_dedup.scan.deps import ScanDeps

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _DigestStep:
    """One hashing pass: how to compute, read from and write to the cached facts."""

    step: Step
    compute: Callable[[Path], str]
    cached: Callable[[FileFacts], str | None]
    store: Callable[[FileFacts, str], FileFacts]


def _groups[K: Hashable](
    files: Iterable[MediaFile],
    key: Callable[[MediaFile], K],
) -> list[list[MediaFile]]:
    """Bucket files by `key`, keeping only buckets of two files or more.

    Args:
        files: Files to bucket.
        key: Bucketing key.

    Returns:
        The buckets holding potential duplicates.
    """
    buckets: defaultdict[K, list[MediaFile]] = defaultdict(list)
    for file in files:
        buckets[key(file)].append(file)
    return [bucket for bucket in buckets.values() if len(bucket) > 1]


class ExactDuplicateFinder:
    """Narrow candidates cheaply first, so only true look-alikes are read in full."""

    def __init__(self, deps: ScanDeps) -> None:
        """Keep the shared scan collaborators.

        Args:
            deps: Index, progress sink and I/O concurrency limit.
        """
        self._deps = deps

    async def find(self, files: Sequence[MediaFile]) -> tuple[DuplicateGroup, ...]:
        """Group the files that are byte-for-byte identical.

        Args:
            files: Healthy, non-empty media files.

        Returns:
            The duplicate groups, largest files first.
        """
        by_size = [
            file for bucket in _groups(files, lambda f: f.size) for file in bucket
        ]
        partial = await self._digests(
            by_size,
            _DigestStep(
                Step(
                    _("Comparing files of equal size"),
                    _(
                        "Only files of the same size can be identical: their first and "
                        "last 64 KB rule most of them out quickly."
                    ),
                ),
                partial_digest,
                lambda facts: facts.partial_digest,
                FileFacts.with_partial,
            ),
        )
        same_partial = _groups(partial, lambda f: (f.size, partial[f]))
        full = await self._digests(
            [file for bucket in same_partial for file in bucket],
            _DigestStep(
                Step(
                    _("Proving identity (full SHA-256)"),
                    _(
                        "Reads the remaining candidates in full: same SHA-256 means "
                        "identical, byte for byte."
                    ),
                ),
                full_digest,
                lambda facts: facts.full_digest,
                FileFacts.with_full,
            ),
        )
        groups = (
            DuplicateGroup(
                digest=full[bucket[0]],
                size=bucket[0].size,
                files=tuple(sorted(bucket, key=lambda f: str(f.path))),
            )
            for bucket in _groups(full, lambda f: (f.size, full[f]))
        )
        return tuple(sorted(groups, key=lambda group: (-group.size, group.digest)))

    async def _digests(
        self,
        files: Sequence[MediaFile],
        step: _DigestStep,
    ) -> dict[MediaFile, str]:
        """Return the digest of each file, from the index or computed in threads.

        Args:
            files: Files to hash.
            step: Which digest to produce.

        Returns:
            The digests; unreadable files are left out.
        """
        repository = self._deps.repository
        digests: dict[MediaFile, str] = {}
        missing: list[MediaFile] = []
        for file in files:
            cached = step.cached(repository.get(file))
            if cached is None:
                missing.append(file)
            else:
                digests[file] = cached
        self._deps.progress.start(step.step, len(missing))
        async with asyncio.TaskGroup() as group:
            tasks = {
                file: group.create_task(self._hash(file, step)) for file in missing
            }
        self._deps.progress.stop()
        for file, task in tasks.items():
            digest = task.result()
            if digest is not None:
                digests[file] = digest
                repository.put(file, step.store(repository.get(file), digest))
        return digests

    async def _hash(self, file: MediaFile, step: _DigestStep) -> str | None:
        """Hash one file in a worker thread, within the I/O concurrency limit.

        Args:
            file: File to hash.
            step: Which digest to produce.

        Returns:
            The digest, or None when the file cannot be read.
        """
        async with self._deps.io_slots:
            try:
                return await asyncio.to_thread(step.compute, file.path)
            except OSError as exc:
                _LOGGER.warning("Cannot read %s: %s", file.path, exc.strerror)
                return None
            finally:
                self._deps.progress.advance()
