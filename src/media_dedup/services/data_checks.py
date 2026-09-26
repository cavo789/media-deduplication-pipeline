"""Check what the audit sees, and say what it leaves out or handles apart.

Every file of `/data` must be seen once: a file seen twice is no duplicate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.errors import MountError
from media_dedup.i18n import _, ngettext
from media_dedup.paths.overlaps import mount_overlaps
from media_dedup.services.policy import unmounted_folders

if TYPE_CHECKING:
    from collections.abc import Sequence

    from media_dedup.scan.aliases import Alias
    from media_dedup.services.runtime import Runtime


def refuse_overlapping_mounts(runtime: Runtime) -> None:
    r"""Stop when a Windows folder is mounted twice under the data directory.

    Args:
        runtime: Settings, mount points and output.

    Raises:
        MountError: `C:\Photos` and `C:\photos\2019` are mounted on unrelated paths.
    """
    data_dir = runtime.locations.data_dir
    overlaps = mount_overlaps(
        (point, host)
        for point, host in runtime.mounts.host_sources
        if point.is_relative_to(data_dir)
    )
    if not overlaps:
        return
    folders = "; ".join(
        _("{folder} (seen as {first} and as {second})").format(
            folder=item.folder, first=item.first, second=item.second
        )
        for item in overlaps
    )
    raise MountError(
        _(
            "The same folder is mounted twice: {folders}. Each of its files would "
            "look like a duplicate of itself."
        ).format(folders=folders),
        _(
            "Mount each folder only once (a folder already includes its subfolders): "
            "remove one of these -v options."
        ),
    )


def warn_about_aliases(runtime: Runtime, aliases: Sequence[Alias]) -> None:
    """Tell that some files are reachable through two paths and analysed once.

    Args:
        runtime: Settings, mount points and output.
        aliases: The paths set aside.
    """
    if not aliases:
        return
    example = aliases[0]
    runtime.output.warning(
        ngettext(
            "{count} file is reachable through two paths (hard link, or folder "
            "mounted twice): it is analysed once, e.g. {path} is {same_as}.",
            "{count} files are reachable through two paths (hard links, or folder "
            "mounted twice): each is analysed once, e.g. {path} is {same_as}.",
            len(aliases),
        ).format(
            count=len(aliases),
            path=runtime.mapper.to_host(example.path),
            same_as=runtime.mapper.to_host(example.same_as),
        )
    )


def warn_about_scope(runtime: Runtime) -> None:
    """Warn about the scope: unmounted folders, extension filter, other files.

    Args:
        runtime: Settings, mount points and output.
    """
    for folder in unmounted_folders(runtime.settings.folders, runtime.mapper):
        runtime.output.warning(
            _("Configured folder {path} is not mounted: it is ignored.").format(
                path=folder
            ),
        )
    scan = runtime.settings.scan
    if scan.extensions:
        runtime.output.warning(
            _("Only these extensions are analysed: {extensions}.").format(
                extensions=", ".join(scan.extensions)
            ),
        )
    if scan.other_files:
        runtime.output.warning(
            _(
                "Not photos or videos: {extensions}. These files are only compared "
                "byte for byte, and their copies are moved to the quarantine."
            ).format(extensions=", ".join(scan.other_files)),
        )
        runtime.output.tip(
            _(
                "Software folders (.git, node_modules, AppData, Program Files, ...) "
                "are skipped: there, where a file lies makes a program work."
            )
        )
