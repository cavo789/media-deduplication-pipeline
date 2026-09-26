"""The real image: read-only audit, refused :ro clean, clean, undo (run with `e2e`)."""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from typing import TYPE_CHECKING, Final

import pytest

from tests.support.demo import build_demo

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

IMAGE: Final = "media-dedup:latest"
KINDS: Final = ("data", "journal", "quarantine", "reports", "cache")
MANIFEST_SCRIPT: Final = (
    "import hashlib, json, pathlib; root = pathlib.Path('/data'); print(json.dumps({"
    "str(p.relative_to(root)): [hashlib.sha256(p.read_bytes()).hexdigest(), "
    "p.stat().st_mtime_ns] for p in sorted(root.rglob('*')) if p.is_file()}))"
)

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        shutil.which("docker") is None, reason="docker is not available"
    ),
]


def docker(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a docker CLI command and capture its output."""
    command = ["docker", *args]
    # Trusted, fixed arguments built by the tests themselves.
    return subprocess.run(  # noqa: S603
        command, capture_output=True, text=True, check=False
    )


def run_image(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a container to completion, then read its output from the logs.

    Some Docker setups (Docker Desktop through a mounted socket) cut the attached
    output after about a second; the logs are always complete.
    """
    started = docker("run", "--detach", *args)
    container = started.stdout.strip()
    if started.returncode != 0:
        return started
    code = docker("wait", container).stdout.strip()
    logs = docker("logs", container)
    docker("rm", container)
    return subprocess.CompletedProcess(args, int(code), logs.stdout, logs.stderr)


@pytest.fixture
def volumes(tmp_path: Path) -> Iterator[dict[str, str]]:
    """Named volumes for every mount point, the data one filled with the demo tree."""
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


def tool(volumes: dict[str, str], *args: str, read_only_data: bool = False) -> str:
    """Run the image with every mount point; return its exit code, then its output."""
    mounts = []
    for kind, name in volumes.items():
        suffix = ":ro" if kind == "data" and read_only_data else ""
        mounts += ["-v", f"{name}:/{kind}{suffix}"]
    # --read-only: the image must work with an immutable root filesystem (the tmpfs
    # is inside the container, not a host temporary file).
    hardening = ["--read-only", "--tmpfs", "/tmp"]  # noqa: S108
    result = run_image(*hardening, *mounts, IMAGE, *args)
    return f"{result.returncode}\n{result.stdout}{result.stderr}"


def manifest(volumes: dict[str, str]) -> dict[str, list[object]]:
    """SHA-256 and mtime of every file of the data volume."""
    data = f"{volumes['data']}:/data:ro"
    result = run_image(
        "--entrypoint",
        "python",
        "-v",
        data,
        IMAGE,
        "-c",
        MANIFEST_SCRIPT,
    )
    return dict(json.loads(result.stdout))


@pytest.fixture(autouse=True)
def image_exists() -> None:
    """Skip when the image is missing (the `e2e` helper builds it first)."""
    if docker("image", "inspect", IMAGE).returncode != 0:
        pytest.skip(f"{IMAGE} is not built")


def test_audit_clean_undo_cycle(volumes: dict[str, str]) -> None:
    """Audit on :ro, clean refused on :ro, clean for real, undo restores everything."""
    before = manifest(volumes)
    audit = tool(volumes, "audit", read_only_data=True)
    assert audit.startswith("0\n"), audit
    assert "Audit summary" in audit
    assert manifest(volumes) == before
    refused = tool(volumes, "clean", "--yes", read_only_data=True)
    assert refused.startswith("1\n"), refused
    assert "read-only" in refused
    clean = tool(volumes, "clean", "--yes")
    assert clean.startswith("0\n"), clean
    after = manifest(volumes)
    assert set(after) < set(before)
    undo = tool(volumes, "undo")
    assert undo.startswith("0\n"), undo
    assert manifest(volumes) == before
    reports = tool(volumes, "reports")
    assert "-audit" in reports
    assert "-clean" in reports
