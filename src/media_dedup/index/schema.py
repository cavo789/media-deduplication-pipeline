"""The index table, and how older index files are brought up to date.

Version 2 adds what images look like. An index written by version 1 keeps its digests
and integrity results; its images are decoded once more to fill the new columns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import sqlite3

SCHEMA_VERSION: Final = 2
_CREATE: Final = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    partial_digest TEXT,
    full_digest TEXT,
    integrity_checked INTEGER NOT NULL DEFAULT 0,
    broken_reason TEXT,
    broken_detail TEXT NOT NULL DEFAULT ''
)
"""
# Added by version 2. Hashes are stored in hexadecimal: SQLite integers are signed.
VISUAL_COLUMNS: Final = (
    ("visual_checked", "INTEGER NOT NULL DEFAULT 0"),
    ("dhash", "TEXT"),
    ("phash", "TEXT"),
    ("width", "INTEGER"),
    ("height", "INTEGER"),
    ("sharpness", "REAL"),
    ("taken_at", "TEXT"),
    ("camera", "TEXT"),
)
SELECT: Final = (
    "SELECT size, mtime_ns, partial_digest, full_digest, integrity_checked,"
    " broken_reason, broken_detail, visual_checked, dhash, phash, width, height,"
    " sharpness, taken_at, camera FROM files WHERE path = ?"
)
UPSERT: Final = (
    "INSERT OR REPLACE INTO files (path, size, mtime_ns, partial_digest, full_digest,"
    " integrity_checked, broken_reason, broken_detail, visual_checked, dhash, phash,"
    " width, height, sharpness, taken_at, camera)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def prepare(connection: sqlite3.Connection) -> None:
    """Create the table, or add the columns an older index lacks.

    Args:
        connection: An open SQLite connection.
    """
    connection.execute(_CREATE)
    existing = {row[1] for row in connection.execute("PRAGMA table_info(files)")}
    for name, definition in VISUAL_COLUMNS:
        if name not in existing:
            connection.execute(f"ALTER TABLE files ADD COLUMN {name} {definition}")
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
