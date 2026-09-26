"""What the HTML templates display — plain, immutable, already host-path-translated."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from media_dedup.actions.outcome import Outcome
    from media_dedup.constants import BrokenReason, RunKind
    from media_dedup.crosscheck.compare import CrossCheckResult
    from media_dedup.plan.models import AuditFindings
    from media_dedup.report.similar_views import SimilarSection
    from media_dedup.report.summary import ReportSummary


@dataclass(frozen=True, slots=True)
class ReportRecord:
    """Everything a report is written from."""

    kind: RunKind
    findings: AuditFindings
    outcome: Outcome | None = None
    run_id: str | None = None
    crosscheck: CrossCheckResult | None = None


@dataclass(frozen=True, slots=True)
class PairEvidence:
    """What reassures about a folder pair.

    Why its copies are kept, sample previews, and whether the folder losing its copies
    is entirely a copy of the other one.
    """

    complete: bool = False
    reasons: tuple[str, ...] = ()
    samples: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FolderPairView:
    """Two folders sharing identical files: the fastest way to sanity-check a clean."""

    kept_in: str
    removed_from: str
    files: int
    size: int
    page: str = ""
    evidence: PairEvidence = field(default_factory=PairEvidence)


@dataclass(frozen=True, slots=True)
class CopyView:
    """One copy of a folder pair: the file kept, the identical file deleted."""

    kept: str
    removed: str
    size: int
    digest: str


@dataclass(frozen=True, slots=True)
class PairPageView:
    """The page listing every copy of one folder pair."""

    pair: FolderPairView
    copies: tuple[CopyView, ...]
    is_clean: bool


@dataclass(frozen=True, slots=True)
class ProofView:
    """How to check a group yourself: its SHA-256 and the command recomputing it."""

    digest: str = ""
    command: str = ""


@dataclass(frozen=True, slots=True)
class GroupView:
    """One duplicate group."""

    size: int
    keeper: str
    removable: tuple[str, ...]
    protected: tuple[str, ...]
    thumbnail: str | None
    proof: ProofView = field(default_factory=ProofView)
    reason: str = ""


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
class GroupsSection:
    """Duplicate groups: a sample of photos, the largest groups, how many are hidden."""

    sample: tuple[GroupView, ...]
    largest: tuple[GroupView, ...]
    hidden: int


@dataclass(frozen=True, slots=True)
class ReportView:
    """The full report."""

    summary: ReportSummary
    roots: tuple[str, ...]
    pairs: tuple[FolderPairView, ...]
    groups: GroupsSection
    similar: SimilarSection
    broken: BrokenSection
    incidents: IncidentsSection
