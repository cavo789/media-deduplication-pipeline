"""The image serves the review on a port Docker publishes on 127.0.0.1, until Ctrl+C."""

from __future__ import annotations

import json
import time
from typing import Final

import pytest

from tests.support.docker import IMAGE, docker

pytestmark = pytest.mark.e2e

_READY: Final = "Review ready on port 8080"
_WAIT_SECONDS: Final = 120
# Run inside the container: its loopback is where Docker forwards the published port.
_FETCH_STATE: Final = (
    "import urllib.request; "
    "print(urllib.request.urlopen('http://127.0.0.1:8080/api/state').read().decode())"
)


def wait_for(container: str, text: str) -> str:
    """Poll the container's logs until `text` appears (or the time is up)."""
    deadline = time.monotonic() + _WAIT_SECONDS
    logs = ""
    while time.monotonic() < deadline:
        logs = docker("logs", container).stdout
        if text in logs:
            break
        time.sleep(1)
    return logs


def test_review_port_is_published_on_loopback(volumes: dict[str, str]) -> None:
    """Docker chooses the host port on 127.0.0.1; Ctrl+C stops the review cleanly."""
    mounts = [
        *("-v", f"{volumes['data']}:/data:ro"),
        *("-v", f"{volumes['reports']}:/reports"),
        *("-v", f"{volumes['cache']}:/cache"),
    ]
    hardening = ["--read-only", "--tmpfs", "/tmp"]  # noqa: S108
    started = docker(
        "run", "--detach", *hardening, "-p", "127.0.0.1::8080", *mounts, IMAGE, "review"
    )
    container = started.stdout.strip()
    try:
        assert started.returncode == 0, started.stderr
        assert _READY in wait_for(container, _READY)
        assert docker("port", container, "8080").stdout.startswith("127.0.0.1:")
        fetched = docker("exec", container, "python", "-c", _FETCH_STATE)
        assert fetched.returncode == 0, fetched.stderr
        assert len(json.loads(fetched.stdout)["series"]) == 1
        docker("kill", "--signal", "INT", container)
        assert docker("wait", container).stdout.strip() == "0"
        assert "Review stopped" in docker("logs", container).stdout
    finally:
        docker("rm", "--force", container)
