"""End-to-end fixtures: the built image, and named volumes holding the demo tree."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from tests.support.demo import build_demo
from tests.support.docker import IMAGE, KINDS, docker

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture(autouse=True)
def image_exists() -> None:
    """Skip when the image is missing (the `e2e` helper builds it first)."""
    if docker("image", "inspect", IMAGE).returncode != 0:
        pytest.skip(f"{IMAGE} is not built")


@pytest.fixture
def volumes(tmp_path: Path) -> Iterator[dict[str, str]]:
    """Named volumes for every mount point, the data one filled with the demo tree.

    Args:
        tmp_path: Pytest temporary directory.

    Yields:
        The volume name of each mount point.
    """
    names = {kind: f"media-dedup-e2e-{kind}-{uuid.uuid4().hex[:8]}" for kind in KINDS}
    build_demo(tmp_path / "demo")
    seed = f"media-dedup-e2e-seed-{uuid.uuid4().hex[:8]}"
    docker("create", "--name", seed, "-v", f"{names['data']}:/data", IMAGE)
    docker("cp", f"{tmp_path / 'demo'}/.", f"{seed}:/data/")
    docker("rm", seed)
    # docker cp writes as root: hand the files to the image's non-root user.
    docker("run", "--rm", "--user", "0", "--entrypoint", "chown", "-v",
           f"{names['data']}:/data", IMAGE, "-R", "1000:1000", "/data")  # fmt: skip
    yield names
    docker("volume", "rm", "--force", *names.values())
