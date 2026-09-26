"""`review` then `clean --decisions`: burst shots set aside go to the quarantine."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from media_dedup.paths.mount_kind import MountKind
from media_dedup.services import reviewing
from tests.support.cli import run

if TYPE_CHECKING:
    from collections.abc import Callable

    from media_dedup.paths.locations import Locations
    from media_dedup.review.app import ReviewApp
    from tests.support.media import MediaFactory

RAFALE = "C:\\Family Photos\\Rafale"
BLURRED = "c/Family Photos/Rafale/IMG_202.jpg"
DEMO_ROOTS = ["C:\\", "D:\\"]
PORT = 4242


def shots(*ranks: int) -> list[str]:
    """Host paths of the demo burst's shots."""
    return [f"{RAFALE}\\IMG_20{rank}.jpg" for rank in ranks]


def write_decisions(
    locations: Locations, kept: list[str], discarded: list[str]
) -> None:
    """The decisions file `review` writes for one series."""
    bursts = [{"kept": kept, "discarded": discarded}]
    decisions = {"version": 1, "roots": DEMO_ROOTS, "bursts": bursts}
    (locations.reports_dir / "decisions.json").write_text(json.dumps(decisions))


def test_shots_set_aside_are_moved_and_come_back(
    cli: CliRunner, locations: Locations
) -> None:
    """Quarantined, never deleted; the other shots stay; undo restores."""
    data = locations.data_dir
    write_decisions(locations, shots(0, 1, 3), shots(2))
    result = run(cli, "clean", "--yes", "--decisions", "decisions.json")
    assert result.exit_code == 0, result.output
    assert "burst series reviewed: 1, shots set aside: 1" in result.output
    assert not (data / BLURRED).exists()
    assert [p.name for p in locations.quarantine_dir.rglob("IMG_202.jpg")]
    assert (data / "c/Family Photos/Rafale/IMG_201.jpg").is_file()
    assert run(cli, "undo").exit_code == 0
    assert (data / BLURRED).is_file()


type Case = tuple[list[str], list[str], str]  # discarded, options, error
STALE: Case = (["C:\\elsewhere.jpg"], [], "no longer matches the audit")
PROTECTED: Case = (shots(2), ["--protect", RAFALE], "is in a protected folder")


@pytest.mark.parametrize("case", [STALE, PROTECTED])
def test_stale_or_protected_shots_are_refused(
    cli: CliRunner, locations: Locations, case: Case
) -> None:
    """Nothing is cleaned: the whole file is refused."""
    discarded, options, error = case
    write_decisions(locations, shots(0), discarded)
    result = run(cli, "clean", "--yes", "--decisions", "decisions.json", *options)
    assert result.exit_code == 1
    assert error in result.output
    assert (locations.data_dir / BLURRED).is_file()


def test_shots_set_aside_need_a_quarantine(
    cli: CliRunner, locations: Locations, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refused before the audit, with a tip."""
    write_decisions(locations, shots(0), shots(2))
    monkeypatch.delenv("MEDIA_DEDUP_QUARANTINE_DIR")
    result = run(cli, "clean", "--yes", "--decisions", "decisions.json")
    assert result.exit_code == 1
    assert "Burst shots you set aside go to /quarantine" in result.output
    assert "Audit summary" not in result.output


def fake_server(action: Callable[[ReviewApp], None]) -> object:
    """A server that says it is ready, lets `action` act, then gets Ctrl+C."""

    async def serve(app: ReviewApp, _port: int, ready: Callable[[int], None]) -> None:
        ready(PORT)
        action(app)
        raise KeyboardInterrupt

    return serve


def test_the_review_command_serves_until_ctrl_c(
    cli: CliRunner, locations: Locations, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Where to open it, the page translated, each choice saved, then what to do."""
    pages: list[bytes] = []

    def choose(app: ReviewApp) -> None:
        pages.append(app.page)
        app.session.decide(0, frozenset({2}))

    monkeypatch.setattr(reviewing, "run_server", fake_server(choose))
    result = run(cli, "review")
    assert result.exit_code == 0, result.output
    assert f"Review ready on port {PORT}" in result.output
    assert "docker port" in result.output
    assert "shots set aside: 1" in result.output
    assert "--decisions decisions.json" in result.output
    assert b"Burst series review" in pages[0]
    saved = json.loads((locations.reports_dir / "decisions.json").read_text())
    assert saved["bursts"][0]["discarded"] == shots(2)


def test_the_review_needs_somewhere_to_save(
    cli: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without /reports the decisions would be lost: refused before the audit."""
    monkeypatch.delenv("MEDIA_DEDUP_REPORTS_DIR")
    result = run(cli, "review")
    assert result.exit_code == 1
    assert "The decisions are saved in /reports" in result.output
    assert "Audit summary" not in result.output


def test_no_burst_nothing_to_review(
    locations: Locations, media: MediaFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tree without bursts: said at once, no server."""
    media.image("c/Photos/alone.jpg")
    for kind in MountKind:
        path = locations.path_of(kind)
        monkeypatch.setenv(f"MEDIA_DEDUP_{kind.value.upper()}_DIR", str(path))
    monkeypatch.setattr(reviewing, "run_server", fake_server(lambda _app: None))
    result = run(
        CliRunner(), "review", "--decisions", str(locations.cache_dir / "d.json")
    )
    assert result.exit_code == 0, result.output
    assert "No burst series: nothing to review." in result.output
