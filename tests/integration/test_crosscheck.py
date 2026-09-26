"""The second opinion, from the command line: audit tip, crosscheck, clean verdict."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from media_dedup.constants import CZKAWKA_FILE_NAME
from media_dedup.report.index_page import load_summaries
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from tests.support.cli import run
from tests.support.runtime import make_runtime

if TYPE_CHECKING:
    from collections.abc import Iterable

    import pytest
    from typer.testing import CliRunner

    from media_dedup.paths.locations import Locations


def write_czkawka(locations: Locations, groups: Iterable[Iterable[Path]]) -> None:
    """Write results the way czkawka_cli dup -C does."""
    by_size = {
        str(index): [[{"path": str(path), "size": index} for path in group]]
        for index, group in enumerate(groups, start=1)
    }
    (locations.reports_dir / CZKAWKA_FILE_NAME).write_text(json.dumps(by_size))


def media_dedup_groups(locations: Locations) -> list[list[Path]]:
    """The groups media-dedup finds on the demo tree."""
    findings = AuditService(make_runtime(locations), NullProgress()).run()
    return [[file.path for file in group.files] for group in findings.groups]


def test_the_audit_prints_the_czkawka_command(cli: CliRunner) -> None:
    """With duplicates, the audit suggests the command for a second opinion."""
    output = run(cli, "audit").output
    assert "Second opinion" in output
    assert "czkawka_cli dup -d " in output
    assert "-C /out/czkawka.json" in output


def test_crosscheck_agrees_and_reports_it(cli: CliRunner, locations: Locations) -> None:
    """Same groups, plus files media-dedup leaves out: agreement, in the report too."""
    groups = media_dedup_groups(locations)
    data = locations.data_dir
    sidecars = [data / "c/Family Photos/2019/Vacances/IMG_0001.xmp", data / "x.xmp"]
    write_czkawka(locations, [*groups, sidecars])
    result = run(cli, "crosscheck")
    assert result.exit_code == 0, result.output
    assert "Czkawka agrees" in result.output
    assert "other file types: 2" in result.output
    verdict = load_summaries(locations.reports_dir)[0].crosscheck
    assert verdict is not None
    assert verdict.agrees
    assert verdict.set_aside == 2


def test_crosscheck_lists_disagreements(cli: CliRunner, locations: Locations) -> None:
    """A group only Czkawka found is shown, with its paths."""
    data = locations.data_dir
    extra = [data / "c/Family Photos/Rafale/IMG_2001.jpg", data / "c/other.jpg"]
    write_czkawka(locations, [*media_dedup_groups(locations), extra])
    output = run(cli, "crosscheck").output
    assert "Czkawka disagrees on 1 group" in output
    assert "only Czkawka" in output


def test_crosscheck_needs_results_and_a_reports_mount(
    cli: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without results: the command to run; without /reports: a mount error."""
    missing = run(cli, "crosscheck")
    assert missing.exit_code == 1
    assert "czkawka_cli dup" in missing.output
    monkeypatch.delenv("MEDIA_DEDUP_REPORTS_DIR")
    unmounted = run(cli, "crosscheck")
    assert unmounted.exit_code == 1
    assert "/reports" in unmounted.output


def test_clean_shows_the_verdict_but_never_needs_it(
    cli: CliRunner, locations: Locations
) -> None:
    """No results is said; results of other folders are a warning: the clean runs."""
    assert "Not cross-checked" in run(cli, "clean", "--yes").output
    assert run(cli, "undo").exit_code == 0
    write_czkawka(locations, [[Path("/elsewhere/a.jpg"), Path("/elsewhere/b.jpg")]])
    result = run(cli, "clean", "--yes")
    assert result.exit_code == 0, result.output
    assert "cover other folders" in result.output
