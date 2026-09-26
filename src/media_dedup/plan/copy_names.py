"""Recognise file names that look like copies: `IMG (1).jpg`, `IMG - Copie.jpg`, ..."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

_COPY_WORDS: Final = "copy|copie|kopie|copia|kopia|kopio"
_COPY_PATTERNS: Final = (
    # A number between brackets at the end, as Windows names a second copy.
    re.compile(r"\(\d+\)$"),
    # Matches: IMG - Copy / IMG_copie / IMG copy 2
    re.compile(rf"[\s_-]+({_COPY_WORDS})(\s*\d+)?$", re.IGNORECASE),
    # Matches: Copy of IMG / Copie de IMG / Kopie van IMG
    re.compile(rf"^({_COPY_WORDS})\s+(of|de|van|di|von)\s", re.IGNORECASE),
)


def looks_like_copy(path: Path) -> bool:
    """Tell whether the file name follows a usual "copy" naming pattern.

    Args:
        path: File to test.

    Returns:
        True when the name (without extension) looks like a copy.
    """
    stem = path.stem.strip()
    return any(pattern.search(stem) for pattern in _COPY_PATTERNS)


def without_copy_marks(stem: str) -> str:
    """Remove the "copy" marks from a file name, to judge the name itself.

    Args:
        stem: A file name without its extension, e.g. `Copie de IMG_0001 (2)`.

    Returns:
        The name without its copy marks, e.g. `IMG_0001`.
    """
    name = stem.strip()
    for pattern in _COPY_PATTERNS:
        name = pattern.sub("", name).strip()
    return name
