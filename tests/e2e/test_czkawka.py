"""The second opinion for real: the printed command, run with the Czkawka image."""

from __future__ import annotations

import shlex
import shutil
from pathlib import Path

import pytest

from media_dedup.constants import CZKAWKA_IMAGE, MEDIA_EXTENSIONS
from media_dedup.crosscheck.czkawka import CzkawkaCommand, CzkawkaScope
from tests.support.docker import docker, run_image, tool

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        shutil.which("docker") is None, reason="docker is not available"
    ),
]


@pytest.fixture(autouse=True)
def czkawka_image() -> None:
    """Pull the pinned Czkawka image (about 500 MB), or skip when offline."""
    present = docker("image", "inspect", CZKAWKA_IMAGE).returncode == 0
    if not present and docker("pull", CZKAWKA_IMAGE).returncode != 0:
        pytest.skip(f"{CZKAWKA_IMAGE} cannot be pulled")


def test_czkawka_agrees_on_the_demo_tree(volumes: dict[str, str]) -> None:
    """Audit, run the rendered Czkawka command, then crosscheck: they agree."""
    audit = tool(volumes, "audit", read_only_data=True)
    assert audit.startswith("0\n"), audit
    extensions = sorted(extension.lstrip(".") for extension in MEDIA_EXTENSIONS)
    command = CzkawkaCommand(
        mounts=((volumes["data"], Path("/data")),),
        output_dir=volumes["reports"],
        scope=CzkawkaScope(Path("/data"), extensions),
    ).render()
    arguments = shlex.split(command)
    assert arguments[:3] == ["docker", "run", "--rm"]
    czkawka = run_image(*arguments[3:])
    assert czkawka.returncode == 0, czkawka.stdout + czkawka.stderr
    verdict = tool(volumes, "crosscheck", read_only_data=True)
    assert verdict.startswith("0\n"), verdict
    assert "Czkawka agrees" in verdict
