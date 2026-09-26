"""Integration fixtures: the command line on the demo tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from media_dedup.paths.mount_kind import MountKind
from tests.support.demo import build_demo

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations


@pytest.fixture
def cli(locations: Locations, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    """A runner whose mount points are the test's temporary folders.

    Args:
        locations: The test mount points.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        The runner, the demo tree in its data folder.
    """
    for kind in MountKind:
        monkeypatch.setenv(
            f"MEDIA_DEDUP_{kind.value.upper()}_DIR", str(locations.path_of(kind))
        )
    build_demo(locations.data_dir)
    return CliRunner()
