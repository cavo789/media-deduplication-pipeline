"""Mount points the container cannot write to: explained up front, never a traceback."""

from __future__ import annotations

import errno
import os
from typing import TYPE_CHECKING, Final

import pytest

from media_dedup.constants import RunKind
from media_dedup.errors import MountError
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.views import ReportRecord
from media_dedup.report.writer import ReportWriter
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.clean import CleanService
from media_dedup.services.reporting import write_report
from media_dedup.services.writable import ensure_writable
from tests.support.cli import run
from tests.support.demo import build_demo
from tests.support.runtime import make_locations, make_runtime

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from typer.testing import CliRunner

    from media_dedup.paths.locations import Locations

    type Lock = Callable[..., None]

pytestmark = pytest.mark.skipif(os.geteuid() == 0, reason="root writes to any folder")

_READ_ONLY: Final = 0o555
_WRITABLE: Final = 0o755


@pytest.fixture
def lock(locations: Locations) -> Iterator[Lock]:
    """Make mount points read-only for the test user, until the test ends.

    Args:
        locations: The test mount points.

    Yields:
        A function locking the given mount points.
    """
    locked: list[Path] = []

    def lock_kinds(*kinds: MountKind) -> None:
        for kind in kinds:
            folder = locations.path_of(kind)
            folder.chmod(_READ_ONLY)
            locked.append(folder)

    yield lock_kinds
    for folder in locked:
        folder.chmod(_WRITABLE)


def _fail_with(error: OSError) -> Callable[[ReportWriter, ReportRecord], Path]:
    """Build a `ReportWriter.write` replacement raising `error`.

    Args:
        error: What writing the report raises.

    Returns:
        The replacement.
    """

    def write(_writer: ReportWriter, _record: ReportRecord) -> Path:
        raise error

    return write


def test_audit_refuses_before_the_analysis(cli: CliRunner, lock: Lock) -> None:
    """Unwritable cache and reports: one message naming both, and the fix."""
    lock(MountKind.CACHE, MountKind.REPORTS)
    result = run(cli, "audit")
    assert result.exit_code == 1, result.output
    assert "cannot write to" in result.output
    assert "Create the folders yourself" in result.output
    assert "--user" in result.output
    assert "Audit summary" not in result.output


def test_a_late_report_failure_is_a_warning(
    cli: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The audit summary stays on screen when only the report cannot be written."""
    denied = PermissionError(errno.EACCES, "Permission denied", "/reports/x")
    monkeypatch.setattr(ReportWriter, "write", _fail_with(denied))
    result = run(cli, "audit")
    assert result.exit_code == 0, result.output
    assert "Audit summary" in result.output
    assert "could not be written" in result.output
    assert "--user" in result.output


def test_a_full_disk_gets_no_permission_tip(
    locations: Locations, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a permission error suggests to create the folder as oneself."""
    build_demo(locations.data_dir)
    runtime = make_runtime(locations)
    findings = AuditService(runtime, NullProgress()).run()
    full = OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(ReportWriter, "write", _fail_with(full))
    with pytest.raises(MountError, match="No space left") as caught:
        write_report(runtime, ReportRecord(RunKind.AUDIT, findings))
    assert caught.value.tip is None


def test_config_folder_unwritable_is_a_warning(cli: CliRunner, lock: Lock) -> None:
    """No config.toml can be created: the command still runs with the defaults."""
    lock(MountKind.CONFIG)
    result = run(cli, "audit")
    assert result.exit_code == 0, result.output
    assert "No config.toml created" in result.output
    assert "Audit summary" in result.output


def test_clean_and_undo_refuse_an_unwritable_journal(
    locations: Locations, lock: Lock
) -> None:
    """The journal is checked with the other mounts `clean` and `undo` need."""
    lock(MountKind.JOURNAL)
    with pytest.raises(MountError, match="cannot write") as caught:
        CleanService(make_runtime(locations), NullProgress()).ensure_ready()
    assert caught.value.tip is not None
    assert "Create the folder yourself" in caught.value.tip


def test_read_only_mount_gets_the_ro_tip(
    locations: Locations, lock: Lock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `:ro` mount is fixed by removing `:ro`, not by changing its owner."""
    monkeypatch.setattr("media_dedup.services.writable.is_read_only", lambda _: True)
    lock(MountKind.QUARANTINE)
    with pytest.raises(MountError) as caught:
        ensure_writable(make_runtime(locations), MountKind.QUARANTINE)
    assert caught.value.tip is not None
    assert ":ro" in caught.value.tip


def test_purge_and_reports_refuse(cli: CliRunner, lock: Lock) -> None:
    """Both commands delete or write in their mount point: checked first."""
    lock(MountKind.QUARANTINE, MountKind.REPORTS)
    for result in (run(cli, "purge", "--yes"), run(cli, "reports")):
        assert result.exit_code == 1, result.output
        assert "cannot write to" in result.output


def test_mounts_that_do_not_persist_are_not_checked(tmp_path: Path) -> None:
    """Nothing is written to a mount point that is not mounted."""
    runtime = make_runtime(make_locations(tmp_path, MountKind.REPORTS))
    ensure_writable(runtime, MountKind.REPORTS)
