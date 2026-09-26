"""The real image: read-only audit, refused :ro clean, clean, undo (run with `e2e`)."""

from __future__ import annotations

import json
import shutil
from typing import Final

import pytest

from tests.support.docker import IMAGE, run_image, tool

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
