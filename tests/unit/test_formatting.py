"""Human-readable sizes and counts, in the active language."""

from __future__ import annotations

import pytest

from media_dedup.console.formatting import human_duration, human_number, human_size
from media_dedup.constants import Locale
from media_dedup.i18n import install


@pytest.mark.parametrize(
    ("size", "text"),
    [
        (0, "0 B"),
        (1023, "1,023 B"),
        (1536, "1.5 KB"),
        (5 * 1024**3, "5.0 GB"),
        (3 * 1024**5, "3,072.0 TB"),
    ],
)
def test_human_size(size: int, text: str) -> None:
    """Sizes use binary units with one decimal."""
    assert human_size(size) == text


def test_numbers_follow_the_language() -> None:
    """English groups thousands with commas, French with points and a decimal comma."""
    assert human_number(67947) == "67,947"
    install(Locale.FR)
    assert human_number(67947) == "67.947"
    assert human_number(1234567.25, 1) == "1.234.567,2"
    assert human_size(int(44.3 * 1024**3)) == "44,3 Go"


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(0.4, "0 s"), (12.3, "12 s"), (185, "3 min 05 s"), (3725, "1 h 02 min")],
)
def test_human_duration(seconds: float, text: str) -> None:
    """Durations read like people say them; seconds vanish beyond one hour."""
    assert human_duration(seconds) == text
