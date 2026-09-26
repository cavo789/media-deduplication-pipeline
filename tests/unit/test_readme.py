"""The READMEs' Czkawka command keeps the same scope as media-dedup."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from media_dedup.constants import MEDIA_EXTENSIONS

ROOT = Path(__file__).resolve().parents[2]
CZKAWKA_EXTENSIONS = re.compile(r"^\s*-x (?P<list>[a-z0-9,]+)$", re.MULTILINE)


@pytest.mark.parametrize("readme", ["README.md", "README_FR.md"])
def test_czkawka_scans_the_same_extensions(readme: str) -> None:
    """A new extension in the code must be added to the documented command too."""
    found = CZKAWKA_EXTENSIONS.search((ROOT / readme).read_text(encoding="utf-8"))
    assert found is not None
    expected = {extension.lstrip(".") for extension in MEDIA_EXTENSIONS}
    assert set(found["list"].split(",")) == expected
