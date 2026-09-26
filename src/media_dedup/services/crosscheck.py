"""The cross-check use case: suggest Czkawka's command, then compare its results."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from media_dedup.constants import CZKAWKA_FILE_NAME, MEDIA_EXTENSIONS
from media_dedup.crosscheck.compare import AnalysedScope, OutsideReason, compare
from media_dedup.crosscheck.czkawka import (
    CzkawkaCommand,
    CzkawkaScope,
    read_czkawka_groups,
)
from media_dedup.errors import CrossCheckError
from media_dedup.i18n import _
from media_dedup.services.policy import scan_filters

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.crosscheck.compare import CrossCheckResult
    from media_dedup.plan.models import AuditFindings
    from media_dedup.services.runtime import Runtime


def czkawka_results(runtime: Runtime) -> Path:
    """Where Czkawka's command writes its results: the reports mount point.

    Args:
        runtime: Settings, mount points and output.

    Returns:
        The JSON file path, inside this container.
    """
    return runtime.locations.reports_dir / CZKAWKA_FILE_NAME


def czkawka_command(runtime: Runtime) -> CzkawkaCommand:
    """Build the Czkawka command that sees exactly what this run sees.

    Same host folders on the same mount points (Czkawka reports container paths),
    same extensions, same excluded folders, every file size.

    Args:
        runtime: Settings, mount points and output.

    Returns:
        The command.
    """
    settings, locations, mapper = runtime.settings, runtime.locations, runtime.mapper
    sources = dict(runtime.mounts.host_sources)
    roots = runtime.mounts.data_roots(locations.data_dir)
    extensions = settings.scan.extensions or tuple(sorted(MEDIA_EXTENSIONS))
    return CzkawkaCommand(
        mounts=tuple(
            (sources.get(root) or mapper.to_host(root), root) for root in roots
        ),
        output_dir=sources.get(locations.reports_dir)
        or _("<the folder you mount on /reports>"),
        scope=CzkawkaScope(
            data_dir=locations.data_dir,
            extensions=tuple(extension.lstrip(".") for extension in extensions),
            excluded=tuple(
                mapper.to_container(folder) for folder in settings.folders.excluded
            ),
        ),
    )


def cross_check(runtime: Runtime, findings: AuditFindings) -> CrossCheckResult | None:
    """Compare an audit with Czkawka's results, when they exist.

    Args:
        runtime: Settings, mount points and output.
        findings: The audit just run.

    Returns:
        The comparison, or None when there are no Czkawka results.

    Raises:
        CrossCheckError: The results cover none of the mounted folders.
    """
    results = czkawka_results(runtime)
    if not results.is_file():
        return None
    theirs = read_czkawka_groups(results)
    plan = findings.plan
    broken = (*plan.broken, *plan.protected_broken)
    scope = AnalysedScope(
        roots=findings.roots,
        filters=scan_filters(runtime.settings, runtime.mapper),
        broken=frozenset(item.file.path for item in broken),
    )
    ours = (frozenset(file.path for file in group.files) for group in findings.groups)
    result = compare(ours, theirs, scope)
    files = sum(len(group) for group in theirs)
    if files and result.outside.get(OutsideReason.NOT_MOUNTED) == files:
        raise CrossCheckError(
            _("Czkawka's results cover other folders than this run."),
            _("Run Czkawka with the same -v options: 'audit' prints the command."),
        )
    modified = datetime.fromtimestamp(results.stat().st_mtime, UTC)
    return replace(result, results_date=modified)
