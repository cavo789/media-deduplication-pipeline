"""Drive the docker CLI from the end-to-end tests."""

from __future__ import annotations

import subprocess
from typing import Final

IMAGE: Final = "media-dedup:latest"
KINDS: Final = ("data", "journal", "quarantine", "reports", "cache")


def docker(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a docker CLI command and capture its output.

    Args:
        *args: Arguments after `docker`.

    Returns:
        The completed process.
    """
    command = ["docker", *args]
    # Trusted, fixed arguments built by the tests themselves.
    return subprocess.run(  # noqa: S603
        command, capture_output=True, text=True, check=False
    )


def run_image(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a container to completion, then read its output from the logs.

    Some Docker setups (Docker Desktop through a mounted socket) cut the attached
    output after about a second; the logs are always complete.

    Args:
        *args: Arguments after `docker run`: options, image, command.

    Returns:
        The exit code and the container's output.
    """
    started = docker("run", "--detach", *args)
    container = started.stdout.strip()
    if started.returncode != 0:
        return started
    code = docker("wait", container).stdout.strip()
    logs = docker("logs", container)
    docker("rm", container)
    return subprocess.CompletedProcess(args, int(code), logs.stdout, logs.stderr)


def tool(volumes: dict[str, str], *args: str, read_only_data: bool = False) -> str:
    """Run the image with every mount point.

    Args:
        volumes: Volume name per mount point.
        *args: The media-dedup command line.
        read_only_data: Mount the data volume with `:ro`.

    Returns:
        The exit code, a newline, then the output.
    """
    mounts = []
    for kind, name in volumes.items():
        suffix = ":ro" if kind == "data" and read_only_data else ""
        mounts += ["-v", f"{name}:/{kind}{suffix}"]
    # --read-only: the image must work with an immutable root filesystem (the tmpfs
    # is inside the container, not a host temporary file).
    hardening = ["--read-only", "--tmpfs", "/tmp"]  # noqa: S108
    result = run_image(*hardening, *mounts, IMAGE, *args)
    return f"{result.returncode}\n{result.stdout}{result.stderr}"
