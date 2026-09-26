"""A keyboard review in progress: the shots set aside, saved after every decision.

The decisions file is shared with the report's folder-pair decisions: a review keeps
the `pairs` it finds there and writes its own `bursts`. Reopened on the same folders,
it resumes where it stopped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.errors import DecisionsError
from media_dedup.i18n import _
from media_dedup.report.decisions import write_decisions
from media_dedup.review.shots import (
    burst_decision,
    match_burst,
    set_aside_problem,
    shot_places,
)
from media_dedup.review.views import ReviewState, preview_key

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.plan.similar_models import BurstSeries
    from media_dedup.report.decisions import DecisionsFile
    from media_dedup.review.views import SeriesState, StateBuilder


@dataclass(frozen=True, slots=True)
class ReviewSource:
    """What a review is about: the burst series, how to show them, the file to write."""

    bursts: tuple[BurstSeries, ...]
    builder: StateBuilder
    target: Path


class ReviewSession:
    """The series under review and the shots set aside, in memory and on disk."""

    def __init__(self, source: ReviewSource, base: DecisionsFile) -> None:
        """Resume the decisions of `base` that still match a series.

        Args:
            source: The series and the decisions file.
            base: What the decisions file holds already.
        """
        self._source = source
        self._base = base
        self._states = tuple(source.builder.series(burst) for burst in source.bursts)
        self._previews = {
            preview_key(file): file.path
            for burst in source.bursts
            for file in burst.shots
        }
        self._discarded: dict[int, frozenset[int]] = {}
        places = shot_places(source.bursts, source.builder.mapper)
        self.dropped = 0
        for decision in base.bursts:
            match = match_burst(decision, places)
            if match is None or self._problem(match.series, match.discarded):
                self.dropped += 1
                continue
            self._discarded[match.series] = match.discarded

    @property
    def target_name(self) -> str:
        """Name of the decisions file, as the user gives it to `clean --decisions`.

        Returns:
            The file name.
        """
        return self._source.target.name

    @property
    def progress(self) -> tuple[int, int]:
        """How far the review went.

        Returns:
            The number of series with shots set aside, and of shots set aside.
        """
        return len(self._discarded), sum(map(len, self._discarded.values()))

    def state(self) -> ReviewState:
        """Describe every series and the shots set aside, for the page.

        Returns:
            The state.
        """
        return ReviewState(
            decisions_file=self.target_name,
            series=tuple(
                self._with_choice(number) for number in range(len(self._states))
            ),
        )

    def preview_source(self, key: str) -> Path | None:
        """Find the shot a preview shows.

        Args:
            key: The preview key, from the page.

        Returns:
            The shot, in the container, or None for an unknown key.
        """
        return self._previews.get(key)

    def decide(self, series: int, discarded: frozenset[int]) -> None:
        """Set these shots of a series aside (none: keep it whole), then save.

        Args:
            series: Rank of the series.
            discarded: Ranks of the shots set aside.

        Raises:
            DecisionsError: An unknown series or shot, every shot set aside, or a
                shot of a protected folder.
        """
        problem = self._problem(series, discarded)
        if problem is not None:
            raise DecisionsError(problem)
        if discarded:
            self._discarded[series] = discarded
        else:
            self._discarded.pop(series, None)
        write_decisions(self._source.target, self.decisions())

    def decisions(self) -> DecisionsFile:
        """Build the decisions file: the pairs found in it, the series reviewed.

        Returns:
            The decisions, in host paths.
        """
        mapper, bursts = self._source.builder.mapper, self._source.bursts
        reviewed = tuple(
            burst_decision(mapper, bursts[number].shots, discarded)
            for number, discarded in sorted(self._discarded.items())
        )
        return self._base.model_copy(update={"bursts": reviewed})

    def _with_choice(self, number: int) -> SeriesState:
        """Describe a series with the shots set aside.

        Args:
            number: Rank of the series.

        Returns:
            Its state.
        """
        discarded = tuple(sorted(self._discarded.get(number, frozenset())))
        return self._states[number].model_copy(update={"discarded": discarded})

    def _problem(self, series: int, discarded: frozenset[int]) -> str | None:
        """Explain why shots cannot be set aside, or return None.

        Args:
            series: Rank of the series.
            discarded: Ranks of the shots to set aside.

        Returns:
            The translated reason, or None.
        """
        if not 0 <= series < len(self._source.bursts):
            return _("There is no such series.")
        shots = self._source.bursts[series].shots
        return set_aside_problem(self._source.builder, shots, discarded)
