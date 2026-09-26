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
PLAN_CSV_FILE_NAME: Final = "plan.csv"
CZKAWKA_IMAGE: Final = "jlesage/czkawka:v26.09.2"  # the audit's second opinion
CZKAWKA_FILE_NAME: Final = "czkawka.json"
CZKAWKA_OUTPUT_DIR: Final = "/out"
THUMBNAILS_DIR_NAME: Final = "thumbs"
PAIRS_DIR_NAME: Final = "pairs"
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
    """Families of files: media, other files asked for with `--ext`, sidecars."""

    IMAGE = "image"
    RAW = "raw"
    VIDEO = "video"
    OTHER = "other"
    SIDECAR = "sidecar"


class KeepReason(StrEnum):
    """What made the kept copy win: the policy's criteria in order, then a review."""

    PROTECTED = "protected"
    PREFERRED = "preferred"
    HAS_SIDECAR = "has-sidecar"
    NOT_A_COPY = "not-a-copy"
    MEANINGFUL_NAME = "meaningful-name"
    MEANINGFUL_FOLDER = "meaningful-folder"
    OLDEST = "oldest"
    SHORTEST_PATH = "shortest-path"
    ALPHABETICAL = "alphabetical"
    REVIEWED = "reviewed"


class BrokenReason(StrEnum):
    """Why a media file is considered broken."""

    EMPTY = "empty"
    UNREADABLE_IMAGE = "unreadable-image"
    UNREADABLE_RAW = "unreadable-raw"
    UNREADABLE_VIDEO = "unreadable-video"


class ActionKind(StrEnum):
    """What `clean` did to a file — recorded in the journal so `undo` can reverse it."""

    DELETE_DUPLICATE = "delete-duplicate"
    DELETE_EMPTY = "delete-empty"
    QUARANTINE = "quarantine"
    QUARANTINE_NEAR = "quarantine-near"
    QUARANTINE_DUPLICATE = "quarantine-duplicate"
    QUARANTINE_SIDECAR = "quarantine-sidecar"
    QUARANTINE_BURST = "quarantine-burst"


class CleanTier(StrEnum):
    """How far `clean` goes: exact duplicates only, or near duplicates too."""

    EXACT = "exact"
    NEAR = "near"


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
    MAX_GROUPS_IN_REPORT = 500
    PAIR_SAMPLES = 4
    MAX_SAMPLED_PAIRS = 50
    RANDOM_SAMPLE = 30
    MAX_SIMILAR_IN_REPORT = 200
    MAX_ORPHANS_IN_REPORT = 500
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
MEDIA_EXTENSIONS: Final = IMAGE_EXTENSIONS | RAW_EXTENSIONS | VIDEO_EXTENSIONS
# Sidecars hold the metadata or edits of their photo: it is kept; moved once orphan.
SIDECAR_EXTENSIONS: Final = frozenset({".aae", ".thm", ".xmp"})
# System folders that never hold user media (Windows, Synology, desktop trash bins).
EXCLUDED_DIR_NAMES: Final = frozenset(
    {"$recycle.bin", "system volume information", "@eadir", "#recycle", ".trash"},
)
# Software folders, skipped when other files than media are analysed (paths matter).
APP_DIR_NAMES: Final = frozenset(
    {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "site-packages", "windows"}
    | {"__pycache__", "appdata", "programdata", "program files", "program files (x86)"},
)
# Names cameras and apps generate, matched whole (no extension/copy mark, any case).
GENERATED_NAMES: Final = (
    r"_?(IMG|VID|MVI|MOV|SAM|DSC[NF]?|_DSC|PICT|CIMG)[_-]?\d+",
    r"(IMG|VID)[_-]\d{8}[_-]\d{6}([_-]\d+)?",
    r"(IMG|VID|AUD)-\d{8}-WA\d+",
    r"_?MG_\d+",
    r"P\d{7}",
    r"PXL_\d{8}_\d+.*",
    r"\d{8}_\d{6}(_\d+)?",
    r"\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}(-\d+)?",
    r"(GOPR|G[HX]\d{2})\d{4}",
    r"DJI_\d+",
    r"(FB_IMG|received|Snapchat)[_-]\d+",
    r"(Screenshot|Screen Shot|Capture d.écran)([ _-].*)?",
    r"image\d*",
    r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}",
    r"[0-9a-f]{16,}",
)
# Folder names created by devices and apps, not by someone sorting photos.
GENERIC_FOLDERS: Final = (
    r"DCIM",
    r"\d{3}[A-Z0-9_]{5}",
    r"Camera( Roll| Uploads)?",
    r"WhatsApp (Images|Video)",
    r"Sent",
    r"Downloads?|Téléchargements",
    r"Screenshots|Captures d.écran",
    r"(New folder|Nouveau dossier)( \(\d+\))?",
    r"Import(s|ed)?|Temp|tmp",
)
