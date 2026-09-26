"""The machine-readable summary stored next to every report (`summary.json`)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from media_dedup.constants import RunKind


class ReportSummary(BaseModel):
    """Headline numbers of one audit or clean, listed by the `reports` command."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    folder: str
    kind: RunKind
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    files_scanned: int
    duplicate_groups: int
    duplicate_files: int
    reclaimable_bytes: int
    broken_files: int
    freed_bytes: int = 0
    run_id: str | None = None
    plan_file: str | None = None
