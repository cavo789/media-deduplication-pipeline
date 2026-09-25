"""Names of the container mount points."""

from __future__ import annotations

from enum import StrEnum


class MountKind(StrEnum):
    """Each mount point of the container, named after its `<name>_dir` field."""

    DATA = "data"
    CONFIG = "config"
    JOURNAL = "journal"
    QUARANTINE = "quarantine"
    REPORTS = "reports"
    CACHE = "cache"
