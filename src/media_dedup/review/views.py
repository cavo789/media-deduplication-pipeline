"""What the review page receives: the series, their shots, and the choices so far."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, ConfigDict

from media_dedup.console.formatting import human_number, human_size
from media_dedup.i18n import _

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.keeper import KeepPolicy
    from media_dedup.plan.similar_models import BurstSeries
    from media_dedup.scan.models import MediaFile, VisualFacts

_FROZEN = ConfigDict(frozen=True, extra="forbid")
_PREVIEW_KEY_LENGTH: Final = 24
PREVIEW_PREFIX: Final = "/preview/"


class ShotState(BaseModel):
    """One shot as the page shows it."""

    model_config = _FROZEN

    name: str
    folder: str
    details: str
    preview: str
    protected: bool
    best: bool


class SeriesState(BaseModel):
    """One burst series: its shots in time order, and the ranks set aside."""

    model_config = _FROZEN

    camera: str
    shots: tuple[ShotState, ...]
    discarded: tuple[int, ...] = ()


class ReviewState(BaseModel):
    """Everything the page needs: `GET /api/state`."""

    model_config = _FROZEN

    decisions_file: str
    series: tuple[SeriesState, ...]


def preview_key(file: MediaFile) -> str:
    """Name the preview of a file: stable, and new as soon as the file changes.

    Args:
        file: The shot, as audited.

    Returns:
        A key, safe in a URL, that browsers may cache.
    """
    identity = f"{file.path}\0{file.size}\0{file.mtime_ns}"
    return hashlib.sha256(identity.encode()).hexdigest()[:_PREVIEW_KEY_LENGTH]


@dataclass(frozen=True, slots=True)
class StateBuilder:
    """Describes the shots of the audit for the page, in host paths."""

    mapper: HostPathMapper
    policy: KeepPolicy
    visuals: Mapping[Path, VisualFacts]

    def series(self, burst: BurstSeries) -> SeriesState:
        """Describe one series, no shot set aside yet.

        Args:
            burst: The series.

        Returns:
            Its state.
        """
        first = self.visuals.get(burst.shots[0].path)
        return SeriesState(
            camera=(first.camera if first else None) or "",
            shots=tuple(self._shot(file, file == burst.best) for file in burst.shots),
        )

    def _shot(self, file: MediaFile, best: bool) -> ShotState:  # noqa: FBT001
        """Describe one shot: name, folder, and what tells it from the others.

        Args:
            file: The shot.
            best: It is the sharpest of its series.

        Returns:
            Its state.
        """
        host = self.mapper.to_host(file.path)
        folder, name = host.rsplit("\\" if "\\" in host else "/", 1)
        visual = self.visuals.get(file.path)
        details = [human_size(file.size)]
        if visual is not None:
            details.insert(0, f"{visual.width} \N{MULTIPLICATION SIGN} {visual.height}")
            details.append(
                _("sharpness {value}").format(value=human_number(visual.sharpness))
            )
            details.extend(filter(None, (visual.taken_at,)))
        return ShotState(
            name=name,
            folder=folder,
            details=" · ".join(details),
            preview=f"{PREVIEW_PREFIX}{preview_key(file)}.jpg",
            protected=self.policy.is_protected(file),
            best=best,
        )
