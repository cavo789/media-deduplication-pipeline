"""The audit use case: list, check, hash and plan — never modifies `/data`."""

from __future__ import annotations

import asyncio
import shutil
import time
from collections import Counter
from dataclasses import replace
from types import MappingProxyType
from typing import TYPE_CHECKING

from media_dedup.constants import FFPROBE_BINARY
from media_dedup.errors import MountError
from media_dedup.i18n import _
from media_dedup.index.repository import FactsRepository
from media_dedup.paths.mount_kind import MountKind
from media_dedup.plan.models import AuditFindings
from media_dedup.plan.orphans import sidecars_in_scope
from media_dedup.plan.planner import build_plan
from media_dedup.plan.similar import SimilarInputs, find_similar
from media_dedup.scan.aliases import unique_files
from media_dedup.scan.broken import BrokenFileFinder, IntegrityFindings
from media_dedup.scan.deps import IntegrityTools, ScanDeps
from media_dedup.scan.exact import ExactDuplicateFinder
from media_dedup.scan.progress import Step
from media_dedup.scan.sidecars import accompanied
from media_dedup.scan.walker import Walk, walk
from media_dedup.services.data_checks import (
    refuse_overlapping_mounts,
    warn_about_aliases,
    warn_about_scope,
)
from media_dedup.services.policy import keep_policy, scan_filters

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from media_dedup.scan.models import DuplicateGroup, MediaFile
    from media_dedup.scan.progress import ProgressSink
    from media_dedup.services.runtime import Runtime


class AuditService:
    """Runs a complete, read-only audit."""

    def __init__(self, runtime: Runtime, progress: ProgressSink) -> None:
        """Prepare an audit.

        Args:
            runtime: Settings, mount points and output.
            progress: Where to report progress.
        """
        self._runtime = runtime
        self._progress = progress

    def run(self) -> AuditFindings:
        """List media files, find broken files, exact duplicates and orphan sidecars.

        Returns:
            The findings and the plan.

        Raises:
            MountError: Nothing is mounted under the data directory, or a folder is
                mounted twice.
        """
        runtime, started = self._runtime, time.monotonic()
        data_dir = runtime.locations.data_dir
        if not data_dir.is_dir() or not any(data_dir.iterdir()):
            raise MountError(
                _("No folder to analyse under {path}.").format(path=data_dir),
                _('Mount your folders, e.g. -v "C:\\Photos:/data/c/Photos:ro".'),
            )
        refuse_overlapping_mounts(runtime)
        warn_about_scope(runtime)
        roots = runtime.mounts.data_roots(data_dir)
        found = self._list_files(roots)
        ffprobe = shutil.which(FFPROBE_BINARY)
        if ffprobe is None:
            runtime.output.warning(_("ffprobe not found: videos are not checked."))
        with (
            FactsRepository.open(self._index_file()) as repository,
            runtime.executor_factory() as executor,
        ):
            deps = ScanDeps(repository, self._progress)
            groups, integrity = asyncio.run(
                _analyse(
                    found.files,
                    BrokenFileFinder(deps, IntegrityTools(executor, ffprobe)),
                    ExactDuplicateFinder(deps),
                ),
            )
        policy = keep_policy(
            runtime.settings, runtime.mapper, accompanied(found.sidecars)
        )
        plan = build_plan(groups, integrity.broken, policy)
        # With --ext, sidecars already alone before the clean are left where they are.
        sidecars = sidecars_in_scope(
            found.sidecars, policy, alone=not runtime.settings.scan.extensions
        )
        return AuditFindings(
            files_scanned=len(found.files),
            roots=roots,
            plan=replace(plan, sidecars=sidecars),
            seconds=time.monotonic() - started,
            folder_files=MappingProxyType(
                Counter(file.path.parent for file in found.files)
            ),
            groups=groups,
            similar=find_similar(
                SimilarInputs(found.files, integrity.visuals, groups), policy
            ),
        )

    def _index_file(self) -> Path | None:
        """Return the index file, when the cache is mounted to keep it.

        Returns:
            Its path, or None for an index in memory.
        """
        runtime = self._runtime
        if runtime.persistent(MountKind.CACHE):
            return runtime.locations.index_file
        return None

    def _list_files(self, roots: tuple[Path, ...]) -> Walk:
        """Walk every root, without listing a file twice (nested mounts, hard links).

        Args:
            roots: Mounted folders.

        Returns:
            The media files, by path, and every sidecar found.
        """
        filters = scan_filters(self._runtime.settings, self._runtime.mapper)
        step = Step(
            _("Listing media files"),
            _(
                "Walks through every folder; photos and videos are recognised by their "
                "extension."
            ),
        )
        self._progress.start(step, None)
        found = asyncio.run(walk(roots, filters, self._progress))
        self._progress.stop()
        unique = unique_files(found.files)
        warn_about_aliases(self._runtime, unique.aliases)
        return Walk(unique.files, found.sidecars)


async def _analyse(
    files: Sequence[MediaFile],
    broken_finder: BrokenFileFinder,
    exact_finder: ExactDuplicateFinder,
) -> tuple[tuple[DuplicateGroup, ...], IntegrityFindings]:
    """Find broken files first (describing images), then exact duplicates.

    Broken and empty files are kept out of duplicate groups: they are handled on their
    own (deleted when empty, quarantined when unreadable).

    Args:
        files: Every media file found.
        broken_finder: Integrity checker.
        exact_finder: Duplicate finder.

    Returns:
        The duplicate groups, the broken files and the visual facts of images.
    """
    integrity = await broken_finder.find(files)
    broken_paths = {item.file.path for item in integrity.broken}
    healthy = [
        file for file in files if file.size > 0 and file.path not in broken_paths
    ]
    return await exact_finder.find(healthy), integrity
