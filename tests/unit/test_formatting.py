"""Human-readable sizes."""

from __future__ import annotations

import pytest

from media_dedup.console.formatting import human_size


@pytest.mark.parametrize(
    ("size", "text"),
    [
        (0, "0 B"),
        (1023, "1023 B"),
        (1536, "1.5 KB"),
        (5 * 1024**3, "5.0 GB"),
        (3 * 1024**5, "3072.0 TB"),
    ],
)
def test_human_size(size: int, text: str) -> None:
    """Sizes use binary units with one decimal."""
    assert human_size(size) == text
