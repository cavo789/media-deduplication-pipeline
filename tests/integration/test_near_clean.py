"""Near duplicates and bursts, from the command line: shown, moved only when asked."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from tests.support.cli import run

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from typer.testing import CliRunner

    from media_dedup.paths.locations import Locations

WHATSAPP = "c/Users/Public/Pictures/WhatsApp/IMG-20210705-WA0001.jpg"
EMAIL = "d/backup/email/Plage (petite).jpg"
KEPT = "c/Family Photos/2021/Plage.jpg"
BURST = "c/Family Photos/Rafale"


def digest(path: Path) -> str:
    """SHA-256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_audit_shows_near_duplicates_and_bursts(
    cli: CliRunner, locations: Locations
) -> None:
    """Counted in the summary, explained in a tip, shown side by side in the report."""
    output = run(cli, "audit").output
    assert "Near duplicates (moved only with --tier near)" in output
    assert "Burst series (moved only if set aside with 'review')" in output
    assert "media-dedup review" in output
    assert "clean --tier near" in output
    report = next(locations.reports_dir.glob("*-audit/report.html")).read_text()
    assert "IMG-20210705-WA0001.jpg" in report
    assert "⭐ sharpest" in report


def test_near_duplicates_move_only_with_the_tier_and_come_back(
    cli: CliRunner, locations: Locations
) -> None:
    """A plain clean keeps them; --tier near quarantines them; undo restores them."""
    data = locations.data_dir
    before = {name: digest(data / name) for name in (WHATSAPP, EMAIL)}
    assert run(cli, "clean", "--yes").exit_code == 0
    assert all((data / name).is_file() for name in before)
    assert run(cli, "undo").exit_code == 0
    near = run(cli, "clean", "--yes", "--tier", "near")
    assert near.exit_code == 0, near.output
    assert not any((data / name).exists() for name in before)
    assert (data / KEPT).is_file()
    assert all(path.is_file() for path in (data / BURST).iterdir())
    quarantined = list(locations.quarantine_dir.rglob("*.jpg"))
    assert {path.name for path in quarantined} >= {
        "IMG-20210705-WA0001.jpg",
        "Plage (petite).jpg",
    }
    assert run(cli, "undo").exit_code == 0
    assert {name: digest(data / name) for name in before} == before


def test_the_near_tier_needs_a_quarantine(
    cli: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refused before the long analysis, with a tip."""
    monkeypatch.delenv("MEDIA_DEDUP_QUARANTINE_DIR")
    result = run(cli, "clean", "--yes", "--tier", "near")
    assert result.exit_code == 1
    assert "/quarantine" in result.output
    assert "Audit summary" not in result.output
