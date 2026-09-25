"""Persist `FileFacts` in SQLite by path; a size or mtime change invalidates them."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Final, Self

from media_dedup.constants import BrokenReason
from media_dedup.index.facts import FileFacts

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.scan.models import MediaFile

_SCHEMA_VERSION: Final = 1
_IN_MEMORY: Final = ":memory:"
_SCHEMA: Final = """
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
_SELECT: Final = (
    "SELECT size, mtime_ns, partial_digest, full_digest, integrity_checked,"
    " broken_reason, broken_detail FROM files WHERE path = ?"
)
_UPSERT: Final = (
    "INSERT OR REPLACE INTO files (path, size, mtime_ns, partial_digest, full_digest,"
    " integrity_checked, broken_reason, broken_detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
_SIZE, _MTIME, _PARTIAL, _FULL, _CHECKED, _REASON, _DETAIL = range(7)


class FactsRepository:
    """Cache of digests and integrity checks; a stale entry reads as empty facts."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Wrap an open connection and make sure the schema exists.

        Args:
            connection: SQLite connection, owned by the repository from now on.
        """
        self._connection = connection
        self._connection.execute(_SCHEMA)
        self._connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    @classmethod
    def open(cls, index_file: Path | None) -> Self:
        """Open the index file, or an in-memory index when nothing persists.

        Args:
            index_file: SQLite file, or None for a throw-away index.

        Returns:
            The repository.
        """
        target = str(index_file) if index_file is not None else _IN_MEMORY
        return cls(sqlite3.connect(target))

    def __enter__(self) -> Self:
        """Use the repository as a context manager.

        Returns:
            The repository itself.
        """
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Commit and close the connection, whether or not an exception occurred.

        Args:
            *exc_info: Exception details from the `with` statement (unused).
        """
        self._connection.commit()
        self._connection.close()

    def get(self, file: MediaFile) -> FileFacts:
        """Return the facts known for this exact version of `file`.

        Args:
            file: The file, with the size and mtime seen by the scan.

        Returns:
            The cached facts, or empty facts when unknown or stale.
        """
        row = self._connection.execute(_SELECT, (str(file.path),)).fetchone()
        if row is None or (row[_SIZE], row[_MTIME]) != (file.size, file.mtime_ns):
            return FileFacts()
        reason = row[_REASON]
        return FileFacts(
            partial_digest=row[_PARTIAL],
            full_digest=row[_FULL],
            integrity_checked=bool(row[_CHECKED]),
            broken_reason=BrokenReason(reason) if reason is not None else None,
            broken_detail=row[_DETAIL],
        )

    def put(self, file: MediaFile, facts: FileFacts) -> None:
        """Store the facts of this version of `file`.

        Args:
            file: The file they describe.
            facts: The facts to remember.
        """
        reason = facts.broken_reason.value if facts.broken_reason is not None else None
        row = (
            str(file.path),
            file.size,
            file.mtime_ns,
            facts.partial_digest,
            facts.full_digest,
            int(facts.integrity_checked),
            reason,
            facts.broken_detail,
        )
        self._connection.execute(_UPSERT, row)
