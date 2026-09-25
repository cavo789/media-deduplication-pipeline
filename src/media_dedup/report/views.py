"""What the HTML templates display — plain, immutable, already host-path-translated."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from media_dedup.actions.outcome import Outcome
    from media_dedup.constants import BrokenReason, RunKind
    from media_dedup.plan.models import AuditFindings
    from media_dedup.report.summary import ReportSummary


@dataclass(frozen=True, slots=True)
class ReportRecord:
    """Everything a report is written from."""

    kind: RunKind
    findings: AuditFindings
    outcome: Outcome | None = None
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class FolderPairView:
    """Two folders sharing identical files: the fastest way to sanity-check a clean."""

    kept_in: str
    removed_from: str
    files: int
    size: int


@dataclass(frozen=True, slots=True)
class GroupView:
    """One duplicate group."""

    size: int
    keeper: str
    removable: tuple[str, ...]
    protected: tuple[str, ...]
    thumbnail: str | None


@dataclass(frozen=True, slots=True)
class BrokenView:
    """One broken file."""

    path: str
    reason: BrokenReason
    detail: str
    thumbnail: str | None


@dataclass(frozen=True, slots=True)
class IncidentView:
    """A file `clean` left untouched or failed on."""

    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class BrokenSection:
    """Broken files `clean` handles, and those it leaves alone (protected folders)."""

    handled: tuple[BrokenView, ...]
    protected: tuple[BrokenView, ...]


@dataclass(frozen=True, slots=True)
class IncidentsSection:
    """Files a clean skipped (on purpose) or failed on."""

    skipped: tuple[IncidentView, ...] = ()
    failed: tuple[IncidentView, ...] = ()


@dataclass(frozen=True, slots=True)
class ReportView:
    """The full report."""

    summary: ReportSummary
    roots: tuple[str, ...]
    pairs: tuple[FolderPairView, ...]
    groups: tuple[GroupView, ...]
    hidden_groups: int
    broken: BrokenSection
    incidents: IncidentsSection
