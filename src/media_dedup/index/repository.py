"""Persist `FileFacts` in SQLite by path; a size or mtime change invalidates them."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Final, Self

from media_dedup.constants import BrokenReason
from media_dedup.index.facts import FileFacts
from media_dedup.index.schema import SELECT, UPSERT, prepare
from media_dedup.scan.models import VisualFacts

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from media_dedup.scan.models import MediaFile

_IN_MEMORY: Final = ":memory:"
_SIZE, _MTIME, _PARTIAL, _FULL, _CHECKED, _REASON, _DETAIL, _VISUAL = range(8)
_HEX: Final = 16


class FactsRepository:
    """Cache of digests and integrity checks; a stale entry reads as empty facts."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Wrap an open connection and make sure the schema exists.

        Args:
            connection: SQLite connection, owned by the repository from now on.
        """
        self._connection = connection
        prepare(connection)

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
        row = self._connection.execute(SELECT, (str(file.path),)).fetchone()
        if row is None or (row[_SIZE], row[_MTIME]) != (file.size, file.mtime_ns):
            return FileFacts()
        reason = row[_REASON]
        return FileFacts(
            partial_digest=row[_PARTIAL],
            full_digest=row[_FULL],
            integrity_checked=bool(row[_CHECKED]),
            broken_reason=BrokenReason(reason) if reason is not None else None,
            broken_detail=row[_DETAIL],
            visual_checked=bool(row[_VISUAL]),
            visual=_visual_of(row[_VISUAL + 1 :]),
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
            int(facts.visual_checked),
            *_visual_row(facts.visual),
        )
        self._connection.execute(UPSERT, row)


def _visual_row(visual: VisualFacts | None) -> tuple[object, ...]:
    """Flatten visual facts into the version 2 columns.

    Args:
        visual: The facts, or None.

    Returns:
        dhash, phash, width, height, sharpness, taken_at, camera.
    """
    if visual is None:
        return (None,) * 7
    return (
        f"{visual.dhash:016x}",
        f"{visual.phash:016x}",
        visual.width,
        visual.height,
        visual.sharpness,
        visual.taken_at,
        visual.camera,
    )


def _visual_of(values: Sequence[object]) -> VisualFacts | None:
    """Rebuild visual facts from the version 2 columns.

    Args:
        values: dhash, phash, width, height, sharpness, taken_at, camera.

    Returns:
        The facts, or None when the image has none.
    """
    dhash, phash, width, height, sharpness, taken_at, camera = values
    if not isinstance(dhash, str) or not isinstance(phash, str):
        return None
    return VisualFacts(
        dhash=int(dhash, _HEX),
        phash=int(phash, _HEX),
        width=int(str(width)),
        height=int(str(height)),
        sharpness=float(str(sharpness)),
        taken_at=taken_at if isinstance(taken_at, str) else None,
        camera=camera if isinstance(camera, str) else None,
    )
