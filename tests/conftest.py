"""Shared fixtures: an isolated set of mount points and a media factory inside it."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from media_dedup.constants import Locale
from media_dedup.i18n import install
from tests.support.media import MediaFactory
from tests.support.runtime import make_locations

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from media_dedup.paths.locations import Locations


@pytest.fixture(autouse=True)
def english() -> Iterator[None]:
    """Run every test in English, whatever a previous test installed."""
    install(Locale.EN)
    yield
    install(Locale.EN)


@pytest.fixture
def locations(tmp_path: Path) -> Locations:
    """Every mount point, explicit and persistent, below `tmp_path`.

    Args:
        tmp_path: Pytest temporary directory.

    Returns:
        The locations.
    """
    return make_locations(tmp_path)


@pytest.fixture
def media(locations: Locations) -> MediaFactory:
    """A media factory writing into the data mount point.

    Args:
        locations: The test mount points.

    Returns:
        The factory.
    """
    return MediaFactory(locations.data_dir)
