"""Project-wide constants and enumerations: the single home of every fixed value."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Final

APP_NAME: Final = "media-dedup"
ENV_PREFIX: Final = "MEDIA_DEDUP_"
GETTEXT_DOMAIN: Final = "media_dedup"
CONFIG_FILE_NAME: Final = "config.toml"
INDEX_FILE_NAME: Final = "index.sqlite"
JOURNAL_SUFFIX: Final = ".jsonl"
REPORT_FILE_NAME: Final = "report.html"
REPORT_INDEX_FILE_NAME: Final = "index.html"
SUMMARY_FILE_NAME: Final = "summary.json"
THUMBNAILS_DIR_NAME: Final = "thumbs"
MOUNTINFO_PATH: Final = "/proc/self/mountinfo"
FFPROBE_BINARY: Final = "ffprobe"


class Locale(StrEnum):
    """Languages the interface is translated into."""

    EN = "en"
    FR = "fr"


class Verbosity(StrEnum):
    """Log levels, from the quietest to the most detailed."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


class ColorMode(StrEnum):
    """When to emit ANSI colours."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


class MediaKind(StrEnum):
    """Families of media files the tool knows how to handle."""

    IMAGE = "image"
    RAW = "raw"
    VIDEO = "video"


class BrokenReason(StrEnum):
    """Why a media file is considered broken."""

    EMPTY = "empty"
    UNREADABLE_IMAGE = "unreadable-image"
    UNREADABLE_VIDEO = "unreadable-video"


class ActionKind(StrEnum):
    """What `clean` did to a file — recorded in the journal so `undo` can reverse it."""

    DELETE_DUPLICATE = "delete-duplicate"
    DELETE_EMPTY = "delete-empty"
    QUARANTINE = "quarantine"


class Phase(StrEnum):
    """Which command wrote a journal entry."""

    CLEAN = "clean"
    UNDO = "undo"


class Status(StrEnum):
    """Write-ahead state of a journal entry: `pending` before acting, `done` after."""

    PENDING = "pending"
    DONE = "done"


class RunKind(StrEnum):
    """Which command produced a report."""

    AUDIT = "audit"
    CLEAN = "clean"


class ExitCode(IntEnum):
    """Process exit codes."""

    OK = 0
    FAILURE = 1
    USAGE = 2


class Sizes(IntEnum):
    """Byte counts and limits used by the scanner and the reports."""

    HASH_CHUNK = 1024 * 1024
    PARTIAL_HASH = 64 * 1024
    THUMBNAIL_EDGE = 160
    JPEG_DRAFT_DIVISOR = 8
    MAX_GROUPS_IN_REPORT = 500
    IO_CONCURRENCY = 16


IMAGE_EXTENSIONS: Final = frozenset(
    {".avif", ".bmp", ".gif", ".heic", ".heif", ".jpe", ".jpeg", ".jpg"}
    | {".png", ".tif", ".tiff", ".webp"},
)
RAW_EXTENSIONS: Final = frozenset(
    {".arw", ".cr2", ".cr3", ".dng", ".nef", ".orf", ".pef", ".raf", ".rw2", ".srw"},
)
VIDEO_EXTENSIONS: Final = frozenset(
    {".3g2", ".3gp", ".avi", ".flv", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4"}
    | {".mpeg", ".mpg", ".mts", ".ts", ".webm", ".wmv"},
)
# Sidecars carry metadata or edits of a sibling photo: never touched (see .todos/).
SIDECAR_EXTENSIONS: Final = frozenset({".aae", ".thm", ".xmp"})
# System folders that never hold user media (Windows, Synology, desktop trash bins).
EXCLUDED_DIR_NAMES: Final = frozenset(
    {"$recycle.bin", "system volume information", "@eadir", "#recycle", ".trash"},
)
