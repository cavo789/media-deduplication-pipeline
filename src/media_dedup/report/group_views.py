"""Duplicate groups in the report: the largest, a sample, and how to check them.

"Exact duplicate" means the same SHA-256 (then byte-for-byte equal right before any
deletion). Each group shows that hash and the command recomputing it with the operating
system's own tool, so nobody has to take media-dedup's word for it.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from media_dedup.constants import Sizes
from media_dedup.report.thumbnails import PREVIEWABLE, thumbnail_name
from media_dedup.report.views import GroupView

if TYPE_CHECKING:
    from collections.abc import Sequence

    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.models import CleanPlan, KeepDecision

_WINDOWS_PATH: Final = re.compile(r"^[A-Za-z]:\\")


def largest_groups(plan: CleanPlan) -> tuple[KeepDecision, ...]:
    """The groups listed in full, the largest files first.

    Args:
        plan: The plan.

    Returns:
        Up to `Sizes.MAX_GROUPS_IN_REPORT` groups.
    """
    return plan.decisions[: Sizes.MAX_GROUPS_IN_REPORT]


def sample_groups(plan: CleanPlan) -> tuple[KeepDecision, ...]:
    """Image groups picked across the whole plan, the same ones on every run.

    The largest groups are mostly videos, which have no preview. Ordering by digest
    gives a spread-out, reproducible sample of photos instead.

    Args:
        plan: The plan.

    Returns:
        Up to `Sizes.RANDOM_SAMPLE` image groups.
    """
    images = (d for d in plan.decisions if d.keeper.kind in PREVIEWABLE)
    ordered = sorted(images, key=lambda decision: decision.digest)
    return tuple(ordered[: Sizes.RANDOM_SAMPLE])


def check_command(paths: Sequence[str]) -> str:
    """Build the command that prints the SHA-256 of each file with the system's tool.

    Args:
        paths: Host paths of identical files.

    Returns:
        A PowerShell `Get-FileHash` line for Windows paths, else `sha256sum`.
    """
    if all(_WINDOWS_PATH.match(path) for path in paths):
        quoted = (f"'{path.replace("'", "''")}'" for path in paths)
        return "Get-FileHash " + ",".join(quoted)
    return "sha256sum " + " ".join(shlex.quote(path) for path in paths)


@dataclass(frozen=True, slots=True)
class GroupRenderer:
    """Turns keep decisions into views, in host paths, with the previews written."""

    mapper: HostPathMapper
    previews: frozenset[str]

    def group(self, decision: KeepDecision) -> GroupView:
        """Describe one duplicate group.

        Args:
            decision: The group and which copy stays.

        Returns:
            Its view, with the hash and the command to check it.
        """
        host = self.mapper.to_host
        keeper = host(decision.keeper.path)
        removable = tuple(host(file.path) for file in decision.removable)
        protected = tuple(host(file.path) for file in decision.protected)
        name = thumbnail_name(decision.keeper)
        return GroupView(
            size=decision.size,
            keeper=keeper,
            removable=removable,
            protected=protected,
            thumbnail=name if name in self.previews else None,
            digest=decision.digest,
            command=check_command((keeper, *removable, *protected)),
        )
