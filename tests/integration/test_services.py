"""Safety checks of the clean and undo services."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from media_dedup.constants import BrokenReason
from media_dedup.errors import JournalError, MountError
from media_dedup.paths.mount_kind import MountKind
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.clean import CleanService
from media_dedup.services.undo import resolve_run_id
from tests.support.demo import build_demo
from tests.support.runtime import make_locations, make_runtime, output_of

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.paths.locations import Locations


def test_clean_refuses_without_a_journal(tmp_path: Path) -> None:
    """No journal mount, no clean: undo would be impossible."""
    runtime = make_runtime(make_locations(tmp_path, MountKind.JOURNAL))
    with pytest.raises(MountError, match="journal"):
        CleanService(runtime, NullProgress()).ensure_ready()


def test_clean_refuses_read_only_folders(
    locations: Locations,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Folders mounted with :ro are reported with the fix."""
    monkeypatch.setattr("media_dedup.services.clean.is_read_only", lambda _path: True)
    with pytest.raises(MountError) as caught:
        CleanService(make_runtime(locations), NullProgress()).ensure_ready()
    assert caught.value.tip is not None
    assert ":ro" in caught.value.tip


def test_without_quarantine_only_empty_files_are_handled(tmp_path: Path) -> None:
    """Unreadable files need a quarantine; empty ones can still be deleted."""
    locations = make_locations(tmp_path, MountKind.QUARANTINE)
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    plan = CleanService(runtime, NullProgress()).feasible(findings.plan)
    assert plan.broken
    assert all(item.reason is BrokenReason.EMPTY for item in plan.broken)
    assert "quarantine" in output_of(runtime)


def test_resolve_run_id_errors(tmp_path: Path, locations: Locations) -> None:
    """No journal, no run, or an unknown run: each gets its own message."""
    with pytest.raises(MountError):
        resolve_run_id(
            make_runtime(make_locations(tmp_path / "x", MountKind.JOURNAL)), None
        )
    runtime = make_runtime(locations)
    with pytest.raises(JournalError, match="No clean run"):
        resolve_run_id(runtime, None)
    (locations.journal_dir / "20260101-000000.jsonl").write_text("")
    assert resolve_run_id(runtime, None) == "20260101-000000"
    with pytest.raises(JournalError, match="Unknown run"):
        resolve_run_id(runtime, "nope")
