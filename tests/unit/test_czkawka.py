"""Czkawka's side: the suggested command and the JSON results it writes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from media_dedup.constants import CZKAWKA_IMAGE
from media_dedup.crosscheck.czkawka import (
    CzkawkaCommand,
    CzkawkaScope,
    read_czkawka_groups,
)
from media_dedup.errors import CrossCheckError

# The shape czkawka_cli 12 writes with -C (captured from a real run, fields trimmed).
RESULTS = {
    "833851": [
        [
            {"path": "/data/c/Web/Screen/img101.jpg", "size": 833851, "hash": "f3"},
            {"path": "/data/c/Web/ThemeA/img21.jpg", "size": 833851, "hash": "f3"},
        ]
    ],
    "1602752": [
        [
            {"path": "/data/c/Web/Spotlight/img14.jpg", "size": 1602752},
            {"path": "/data/c/Web/Windows/img0.jpg", "size": 1602752},
        ]
    ],
}


def test_groups_are_read_by_path(tmp_path: Path) -> None:
    """Every group becomes a set of container paths; other fields are ignored."""
    results = tmp_path / "czkawka.json"
    results.write_text(json.dumps(RESULTS))
    groups = read_czkawka_groups(results)
    assert len(groups) == 2
    assert (
        frozenset(
            {
                Path("/data/c/Web/Screen/img101.jpg"),
                Path("/data/c/Web/ThemeA/img21.jpg"),
            }
        )
        in groups
    )


@pytest.mark.parametrize("content", ["not json", '{"1": [["no path"]]}', "[]"])
def test_other_files_are_refused(tmp_path: Path, content: str) -> None:
    """Anything but Czkawka's JSON is an explained error."""
    results = tmp_path / "czkawka.json"
    results.write_text(content)
    with pytest.raises(CrossCheckError) as caught:
        read_czkawka_groups(results)
    assert caught.value.tip is not None


def test_the_command_sees_what_media_dedup_sees() -> None:
    """Same mounts (read-only), same extensions, same exclusions, every size."""
    command = CzkawkaCommand(
        mounts=(("C:\\Photos", Path("/data/c/Photos")),),
        output_dir="C:\\Users\\me\\media-dedup\\reports",
        scope=CzkawkaScope(
            data_dir=Path("/data"),
            extensions=("jpg", "mp4"),
            excluded=(Path("/data/c/Photos/Backup"),),
        ),
    ).render()
    assert command == (
        'docker run --rm -v "C:\\Photos:/data/c/Photos:ro" '
        '-v "C:\\Users\\me\\media-dedup\\reports:/out" '
        f"{CZKAWKA_IMAGE} czkawka_cli dup -d /data -m 1 -W -N -x jpg,mp4 "
        '-e "/data/c/Photos/Backup" -C /out/czkawka.json'
    )
