"""Turn the `[folders]` and `[scan]` settings into policies and filters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.plan.keeper import KeepPolicy
from media_dedup.plan.name_rules import NameRules
from media_dedup.scan.filters import ScanFilters

if TYPE_CHECKING:
    from media_dedup.config.settings import FolderSettings, Settings
    from media_dedup.paths.host_paths import HostPathMapper


def keep_policy(settings: Settings, mapper: HostPathMapper) -> KeepPolicy:
    """Build the keep policy from the `[folders]` host paths and the `[keep]` names.

    Args:
        settings: The effective settings.
        mapper: Host/container path translator.

    Returns:
        The policy, in container paths.
    """
    folders, keep = settings.folders, settings.keep
    return KeepPolicy(
        preferred=tuple(mapper.to_container(path) for path in folders.preferred),
        protected=tuple(mapper.to_container(path) for path in folders.protected),
        names=NameRules.from_patterns(keep.generated_names, keep.generic_folders),
    )


def scan_filters(settings: Settings, mapper: HostPathMapper) -> ScanFilters:
    """Build the scan filters from the excluded host paths and the extensions.

    Args:
        settings: The effective settings.
        mapper: Host/container path translator.

    Returns:
        The filters, in container paths.
    """
    return ScanFilters(
        excluded=tuple(mapper.to_container(p) for p in settings.folders.excluded),
        extensions=frozenset(settings.scan.extensions),
    )


def unmounted_folders(folders: FolderSettings, mapper: HostPathMapper) -> list[str]:
    """List configured folders that are not visible in the container.

    A protected folder that is not mounted protects nothing: the user must know.

    Args:
        folders: The `[folders]` settings.
        mapper: Host/container path translator.

    Returns:
        The host paths that do not exist in the container.
    """
    configured = (*folders.preferred, *folders.protected, *folders.excluded)
    return [path for path in configured if not mapper.to_container(path).exists()]
