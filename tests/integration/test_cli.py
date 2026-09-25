"""The command line, end to end in-process (Typer's CliRunner)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from media_dedup.__main__ import main
from media_dedup.cli.app import build_app
from media_dedup.constants import Locale
from media_dedup.i18n import install
from media_dedup.paths.mount_kind import MountKind
from tests.support.demo import build_demo

if TYPE_CHECKING:
    from typer.testing import Result

    from media_dedup.paths.locations import Locations


@pytest.fixture
def cli(locations: Locations, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """A runner whose mount points are the test's temporary folders.

    Args:
        locations: The test mount points.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        The runner.
    """
    for kind in MountKind:
        monkeypatch.setenv(
            f"MEDIA_DEDUP_{kind.value.upper()}_DIR", str(locations.path_of(kind))
        )
    build_demo(locations.data_dir)
    return CliRunner()


def run(runner: CliRunner, *args: str) -> Result:
    """Invoke the CLI with `args`."""
    return runner.invoke(build_app(), list(args), catch_exceptions=False)


def test_help_is_translated() -> None:
    """The help follows the installed locale."""
    install(Locale.FR)
    result = CliRunner().invoke(build_app(), ["--help"])
    assert "Trouve et nettoie" in result.output
    # Examples stay on one line each: a PowerShell copy/paste must be one command.
    assert 'docker run --rm -it -v "${PWD}:/data/current:ro" media-dedup audit' in (
        result.output
    )


def test_version() -> None:
    """--version prints the package version."""
    assert run(CliRunner(), "--version").output.startswith("media-dedup ")


def test_audit_clean_history_undo(cli: CliRunner, locations: Locations) -> None:
    """The full cycle through the CLI, with the config file created on first run."""
    audit = run(cli, "audit")
    assert audit.exit_code == 0, audit.output
    assert "Audit summary" in audit.output
    assert locations.config_file.is_file()
    clean = run(
        cli, "--verbosity", "warning", "clean", "--yes", "--prefer", "C:\\Family Photos"
    )
    assert clean.exit_code == 0, clean.output
    assert "media-dedup undo" in clean.output
    history = run(cli, "history")
    assert "Clean runs" in history.output
    undo = run(cli, "undo")
    assert undo.exit_code == 0, undo.output
    assert "Undo" in undo.output


def test_clean_needs_confirmation_or_yes(cli: CliRunner) -> None:
    """Without a terminal and without --yes, clean refuses and changes nothing."""
    result = run(cli, "clean")
    assert result.exit_code == 1
    assert "--yes" in result.output


def test_reports_purge_and_config(cli: CliRunner) -> None:
    """Reports are listed and pruned, the quarantine purged, the config explained."""
    run(cli, "audit")
    run(cli, "clean", "--yes")
    reports = run(cli, "reports", "--prune", "1")
    assert "1 report deleted." in reports.output
    purge = run(cli, "purge", "--yes")
    assert "Quarantine purged" in purge.output
    assert "The quarantine is empty." in run(cli, "purge").output
    config = run(cli, "--locale", "fr", "config")
    assert "general.locale" in config.output
    assert "command line" in config.output


def test_errors_are_explained(cli: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Domain errors print a message and a tip, then exit with code 1."""
    assert run(cli, "undo", "unknown-run").exit_code == 1
    assert run(cli, "purge", "unknown-run").exit_code == 1
    monkeypatch.setenv("MEDIA_DEDUP_GENERAL__LOCALE", "klingon")
    broken = run(cli, "config")
    assert broken.exit_code == 1
    assert "general.locale" in broken.output


def test_main_installs_the_locale_before_building_the_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`media-dedup --locale fr --help` shows the French help (entry point)."""
    monkeypatch.setattr("sys.argv", ["media-dedup", "--locale", "fr", "--help"])
    with pytest.raises(SystemExit) as caught:
        main()
    assert caught.value.code == 0
    assert "Trouve et nettoie" in capsys.readouterr().out


def test_ext_limits_the_audit_to_some_extensions(cli: CliRunner) -> None:
    """`--ext` analyses only the extensions asked for, says so, and rejects typos."""
    result = run(cli, "audit", "--ext", "PNG", "--ext", ".webp,png")
    assert result.exit_code == 0, result.output
    assert "Only these extensions are analysed: .png, .webp." in result.output
    assert re.search(r"Media files scanned\s*│\s*1 │", result.output)
    typo = run(cli, "audit", "--ext", "jpgg")
    assert typo.exit_code == 1
    assert ".jpgg; supported: 3g2" in typo.output
    help_text = " ".join(run(cli, "audit", "--help").output.replace("│", " ").split())
    assert "Default: every supported extension: 3g2, 3gp, arw," in help_text
