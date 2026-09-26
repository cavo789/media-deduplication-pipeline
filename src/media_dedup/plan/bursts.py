"""Burst series: shots of one camera, seconds apart, of the same scene.

A burst is curation, not duplication: two shots may be great and eight blurry. Series
are listed, the sharpest shot suggested; a plain `clean` never touches them. Only the
shots set aside in `media-dedup review` are moved, by `clean --decisions`.

Time comes first: shots are sorted by camera and moment, and each one is compared only
with the shots taken up to `BURST_GAP_SECONDS` later, which keeps the comparisons few.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from media_dedup.plan.near import distance
from media_dedup.plan.similar_models import BurstSeries
from media_dedup.plan.union_find import UnionFind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from media_dedup.scan.models import MediaFile, VisualFacts

BURST_GAP_SECONDS: Final = 10.0
BURST_DISTANCE: Final = 18
_EXIF_MOMENT: Final = re.compile(
    r"^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$"
)


@dataclass(frozen=True, slots=True)
class _Shot:
    """An image with a camera and a moment: a possible burst member."""

    file: MediaFile
    visual: VisualFacts
    camera: str
    moment: float


def moment_of(taken_at: str | None) -> float | None:
    """Turn an EXIF date (`2019:06:12 14:30:12.35`) into seconds.

    Args:
        taken_at: The EXIF date, with optional sub-seconds.

    Returns:
        A timestamp (the camera's local time read as UTC), or None when unreadable.
    """
    found = _EXIF_MOMENT.match(taken_at or "")
    if found is None:
        return None
    year, month, day, hour, minute, second = (int(part) for part in found.groups()[:6])
    try:
        when = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except ValueError:
        return None
    return when.timestamp() + float(f"0.{found[7] or 0}")


def burst_series(
    files: Sequence[MediaFile], visuals: Mapping[Path, VisualFacts]
) -> tuple[BurstSeries, ...]:
    """Find burst series and suggest the sharpest shot of each.

    Args:
        files: Candidate images, one per exact-duplicate group.
        visuals: What each image looks like.

    Returns:
        The series, in time order, each with its shots in time order.
    """
    shots = sorted(
        (shot for shot in (_shot(file, visuals) for file in files) if shot),
        key=lambda shot: (shot.camera, shot.moment, str(shot.file.path)),
    )
    links = UnionFind(shots)
    for index, shot in enumerate(shots):
        for later in range(index + 1, len(shots)):
            other = shots[later]
            gap = other.moment - shot.moment
            if other.camera != shot.camera or gap > BURST_GAP_SECONDS:
                break
            if gap > 0 and distance(shot.visual.phash, other.visual.phash) <= (
                BURST_DISTANCE
            ):
                links.link(index, later)
    series = [
        BurstSeries(
            shots=tuple(shot.file for shot in members),
            best=max(members, key=lambda shot: shot.visual.sharpness).file,
        )
        for members in links.sets()
    ]
    return tuple(sorted(series, key=lambda item: str(item.shots[0].path)))


def _shot(file: MediaFile, visuals: Mapping[Path, VisualFacts]) -> _Shot | None:
    """Describe an image as a possible burst member.

    Args:
        file: The image.
        visuals: What each image looks like.

    Returns:
        The shot, or None without a camera or a readable date.
    """
    visual = visuals.get(file.path)
    if visual is None or visual.camera is None:
        return None
    moment = moment_of(visual.taken_at)
    if moment is None:
        return None
    return _Shot(file, visual, visual.camera, moment)
