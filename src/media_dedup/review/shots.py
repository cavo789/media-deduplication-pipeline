"""The shots of a review: found among the audit's series, checked, written back."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.i18n import _
from media_dedup.report.decisions import BurstDecision

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.similar_models import BurstSeries
    from media_dedup.review.views import StateBuilder
    from media_dedup.scan.models import MediaFile


@dataclass(frozen=True, slots=True)
class ShotPlace:
    """Where a shot is: its series, and its rank in the series."""

    series: int
    shot: int


@dataclass(frozen=True, slots=True)
class MatchedBurst:
    """A review of a series, as ranks in one series of the audit."""

    series: int
    kept: frozenset[int]
    discarded: frozenset[int]


def shot_places(
    bursts: Sequence[BurstSeries], mapper: HostPathMapper
) -> dict[str, ShotPlace]:
    """Index every shot of the audit by host path, as decisions files name them.

    Args:
        bursts: The burst series of the audit.
        mapper: Container to host path translator.

    Returns:
        The place of each shot.
    """
    return {
        mapper.to_host(file.path): ShotPlace(number, rank)
        for number, series in enumerate(bursts)
        for rank, file in enumerate(series.shots)
    }


def match_burst(
    decision: BurstDecision, places: Mapping[str, ShotPlace]
) -> MatchedBurst | None:
    """Find the series of the audit a review was made on.

    Args:
        decision: The review of one series.
        places: Every shot of the audit, from `shot_places`.

    Returns:
        The series and ranks, or None when a shot left the burst series or the shots
        now belong to several series (files changed since the review).
    """
    found: list[ShotPlace] = []
    for path in (*decision.kept, *decision.discarded):
        place = places.get(path)
        if place is None:
            return None
        found.append(place)
    if len({place.series for place in found}) != 1:
        return None
    kept = frozenset(place.shot for place in found[: len(decision.kept)])
    discarded = frozenset(place.shot for place in found[len(decision.kept) :])
    return MatchedBurst(found[0].series, kept, discarded)


def set_aside_problem(
    builder: StateBuilder, shots: tuple[MediaFile, ...], discarded: frozenset[int]
) -> str | None:
    """Explain why these shots of a series cannot be set aside, or return None.

    Args:
        builder: Knows the protected folders and the host paths.
        shots: The shots of the series.
        discarded: Ranks of the shots to set aside.

    Returns:
        The translated reason, or None.
    """
    if any(not 0 <= rank < len(shots) for rank in discarded):
        return _("There is no such shot in this series.")
    if len(discarded) == len(shots):
        return _("Keep at least one shot of the series.")
    policy = builder.policy
    locked = [
        shots[rank] for rank in sorted(discarded) if policy.is_protected(shots[rank])
    ]
    if locked:
        message = _("{path} is in a protected folder: it is never moved.")
        return message.format(path=builder.mapper.to_host(locked[0].path))
    return None


def burst_decision(
    mapper: HostPathMapper, shots: tuple[MediaFile, ...], discarded: frozenset[int]
) -> BurstDecision:
    """Write the review of a series as the decisions file holds it.

    Args:
        mapper: Container to host path translator.
        shots: The shots of the series.
        discarded: Ranks of the shots set aside.

    Returns:
        The decision, in host paths.
    """
    paths = [
        (rank in discarded, mapper.to_host(file.path))
        for rank, file in enumerate(shots)
    ]
    return BurstDecision(
        kept=tuple(path for aside, path in paths if not aside),
        discarded=tuple(path for aside, path in paths if aside),
    )
