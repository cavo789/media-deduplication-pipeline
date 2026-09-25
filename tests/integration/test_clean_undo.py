"""Clean then undo on real files: nothing is ever lost."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from media_dedup.actions.journal import journal_file, read_journal
from media_dedup.constants import Phase, Status
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.clean import CleanService
from media_dedup.services.undo import resolve_run_id, undo_run
from tests.support.demo import build_demo
from tests.support.runtime import make_runtime

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.paths.locations import Locations
    from media_dedup.services.runtime import Runtime

type Manifest = dict[str, tuple[str, int]]


def manifest(root: Path) -> Manifest:
    """SHA-256 and mtime of every file below `root`."""
    return {
        str(path.relative_to(root)): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mtime_ns,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def clean(runtime: Runtime) -> str:
    """Audit then clean; return the run identifier."""
    findings = AuditService(runtime, NullProgress()).run()
    service = CleanService(runtime, NullProgress())
    service.ensure_ready()
    run_id, _outcome = service.execute(service.feasible(findings.plan))
    return run_id


def test_clean_then_undo_restores_everything(locations: Locations) -> None:
    """After clean + undo, every byte and every modification time is back."""
    build_demo(locations.data_dir)
    before = manifest(locations.data_dir)
    runtime = make_runtime(locations)
    run_id = clean(runtime)
    after = manifest(locations.data_dir)
    assert len(after) < len(before)
    assert set(after) < set(before)
    assert any((locations.quarantine_dir / run_id).rglob("*.jpg"))
    assert "c/Family Photos/Rafale/IMG_200.jpg" in after
    outcome = undo_run(runtime, resolve_run_id(runtime, None), NullProgress())
    assert not outcome.failed
    assert manifest(locations.data_dir) == before
    assert not any((locations.quarantine_dir / run_id).rglob("*.jpg"))


def test_every_action_is_journaled_before_and_after(locations: Locations) -> None:
    """Each action has a `pending` line followed by a `done` line."""
    build_demo(locations.data_dir)
    run_id = clean(make_runtime(locations))
    entries = read_journal(journal_file(locations.journal_dir, run_id))
    pending = [e.seq for e in entries if e.status is Status.PENDING]
    done = [e.seq for e in entries if e.status is Status.DONE]
    assert pending == done
    assert all(e.phase is Phase.CLEAN for e in entries)


def test_undo_twice_changes_nothing(locations: Locations) -> None:
    """A second undo finds every file back already and skips them."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    run_id = clean(runtime)
    undo_run(runtime, run_id, NullProgress())
    again = undo_run(runtime, run_id, NullProgress())
    assert again.done == 0
    assert not again.failed


def test_changed_keeper_blocks_the_deletion(locations: Locations) -> None:
    """If the kept copy changed after the audit, its duplicates are not deleted."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    decision = findings.plan.decisions[0]
    decision.keeper.path.write_bytes(b"edited after the audit")
    service = CleanService(runtime, NullProgress())
    _run_id, outcome = service.execute(findings.plan)
    skipped = {incident.path for incident in outcome.skipped}
    assert {file.path for file in decision.removable} <= skipped
    assert all(file.path.exists() for file in decision.removable)


def test_undo_skips_when_the_kept_copy_is_gone(locations: Locations) -> None:
    """A deleted duplicate cannot be rebuilt once its keeper disappeared."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    keeper = findings.plan.decisions[0].keeper.path
    run_id, _outcome = CleanService(runtime, NullProgress()).execute(findings.plan)
    keeper.unlink()
    outcome = undo_run(runtime, run_id, NullProgress())
    assert any("gone" in incident.reason for incident in outcome.skipped)
