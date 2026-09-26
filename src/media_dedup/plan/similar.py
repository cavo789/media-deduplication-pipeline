"""Find pictures that look alike: burst series first, then near duplicates.

Each exact-duplicate group takes part once, through the copy it keeps: its other copies
are already handled by the exact tier. Burst shots never count as near duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.plan.bursts import burst_series
from media_dedup.plan.near import near_decisions
from media_dedup.plan.similar_models import SimilarFindings

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from media_dedup.plan.keeper import KeepPolicy
    from media_dedup.scan.models import DuplicateGroup, MediaFile, VisualFacts


@dataclass(frozen=True, slots=True)
class SimilarInputs:
    """What the audit knows: the files, what images look like, the exact groups."""

    files: Sequence[MediaFile]
    visuals: Mapping[Path, VisualFacts]
    groups: Sequence[DuplicateGroup]


def find_similar(inputs: SimilarInputs, policy: KeepPolicy) -> SimilarFindings:
    """List burst series and near duplicates among the readable images.

    Args:
        inputs: Files, visual facts and exact-duplicate groups.
        policy: Protected folders and the usual keep rules.

    Returns:
        The findings, with the visual facts for the report.
    """
    other_copies = {
        file.path
        for decision in (policy.decide(group) for group in inputs.groups)
        for file in (*decision.removable, *decision.protected)
    }
    candidates = [
        file
        for file in inputs.files
        if file.path in inputs.visuals and file.path not in other_copies
    ]
    bursts = burst_series(candidates, inputs.visuals)
    in_bursts = {file.path for series in bursts for file in series.shots}
    near = near_decisions(
        [file for file in candidates if file.path not in in_bursts],
        inputs.visuals,
        policy,
    )
    return SimilarFindings(near=near, bursts=bursts, visuals=inputs.visuals)
