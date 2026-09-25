"""The audit use case: list, check, hash and plan — never modifies `/data`."""

from __future__ import annotations

import asyncio
import shutil
from typing import TYPE_CHECKING

from media_dedup.constants import FFPROBE_BINARY
from media_dedup.errors import MountError
from media_dedup.i18n import _
from media_dedup.index.repository import FactsRepository
from media_dedup.paths.mount_kind import MountKind
from media_dedup.plan.models import AuditFindings
from media_dedup.plan.planner import build_plan
from media_dedup.scan.broken import BrokenFileFinder
from media_dedup.scan.deps import IntegrityTools, ScanDeps
from media_dedup.scan.exact import ExactDuplicateFinder
from media_dedup.scan.walker import walk
from media_dedup.services.policy import keep_policy, scan_filters, unmounted_folders

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.scan.models import BrokenFile, DuplicateGroup, MediaFile
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
        """List media files, find broken files and exact duplicates, plan the clean.

        Returns:
            The findings and the plan.

        Raises:
            MountError: Nothing is mounted under the data directory.
        """
        runtime = self._runtime
        data_dir = runtime.locations.data_dir
        if not data_dir.is_dir() or not any(data_dir.iterdir()):
            raise MountError(
                _("No folder to analyse under {path}.").format(path=data_dir),
                _('Mount your folders, e.g. -v "C:\\Photos:/data/c/Photos:ro".'),
            )
        for folder in unmounted_folders(runtime.settings.folders, runtime.mapper):
            runtime.output.warning(
                _("Configured folder {path} is not mounted: it is ignored.").format(
                    path=folder
                ),
            )
        roots = runtime.mounts.data_roots(data_dir)
        files = self._list_files(roots)
        ffprobe = shutil.which(FFPROBE_BINARY)
        if ffprobe is None:
            runtime.output.warning(_("ffprobe not found: videos are not checked."))
        index_file = runtime.locations.index_file
        persistent = runtime.persistent(MountKind.CACHE)
        with (
            FactsRepository.open(index_file if persistent else None) as repository,
            runtime.executor_factory() as executor,
        ):
            deps = ScanDeps(repository, self._progress)
            groups, broken = asyncio.run(
                _analyse(
                    files,
                    BrokenFileFinder(deps, IntegrityTools(executor, ffprobe)),
                    ExactDuplicateFinder(deps),
                ),
            )
        policy = keep_policy(runtime.settings.folders, runtime.mapper)
        return AuditFindings(
            files_scanned=len(files),
            roots=roots,
            plan=build_plan(groups, broken, policy),
        )

    def _list_files(self, roots: tuple[Path, ...]) -> list[MediaFile]:
        """Walk every root, without listing a file twice (nested mounts).

        Args:
            roots: Mounted folders.

        Returns:
            The media files, by path.
        """
        filters = scan_filters(self._runtime.settings.folders, self._runtime.mapper)
        unique = {file.path: file for root in roots for file in walk(root, filters)}
        return [unique[path] for path in sorted(unique)]


async def _analyse(
    files: list[MediaFile],
    broken_finder: BrokenFileFinder,
    exact_finder: ExactDuplicateFinder,
) -> tuple[tuple[DuplicateGroup, ...], tuple[BrokenFile, ...]]:
    """Find broken files first, then exact duplicates among the healthy ones.

    Broken and empty files are kept out of duplicate groups: they are handled on their
    own (deleted when empty, quarantined when unreadable).

    Args:
        files: Every media file found.
        broken_finder: Integrity checker.
        exact_finder: Duplicate finder.

    Returns:
        The duplicate groups and the broken files.
    """
    broken = await broken_finder.find(files)
    broken_paths = {item.file.path for item in broken}
    healthy = [
        file for file in files if file.size > 0 and file.path not in broken_paths
    ]
    return await exact_finder.find(healthy), broken
