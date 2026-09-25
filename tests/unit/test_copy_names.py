"""Recognition of copy-like file names."""

from __future__ import annotations

from pathlib import Path

import pytest

from media_dedup.plan.copy_names import looks_like_copy


@pytest.mark.parametrize(
    "name",
    [
        "IMG_0001 (1).jpg",
        "IMG_0001(2).JPG",
        "IMG_0001 - Copie.jpg",
        "IMG_0001 - Copy (3).jpg",
        "IMG_0001_copy.jpg",
        "IMG_0001 copie 2.heic",
        "Copy of IMG_0001.jpg",
        "Copie de IMG_0001.jpg",
        "Kopie van vakantie.jpg",
    ],
)
def test_copy_names_are_recognised(name: str) -> None:
    """Usual Windows, macOS and localized copy names are detected."""
    assert looks_like_copy(Path(name))


@pytest.mark.parametrize(
    "name",
    ["IMG_0001.jpg", "Copyright.jpg", "copier.png", "Photocopy.jpg", "DSC01234.JPG"],
)
def test_original_names_are_not_copies(name: str) -> None:
    """Ordinary camera names, even containing 'copy', are not copies."""
    assert not looks_like_copy(Path(name))
