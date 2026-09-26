"""Domain exceptions: each carries a user-facing message and an optional tip."""

from __future__ import annotations


class MediaDedupError(Exception):
    """Base class of every error the CLI reports to the user without a traceback."""

    def __init__(self, message: str, tip: str | None = None) -> None:
        """Store the translated message and an optional 💡 tip.

        Args:
            message: What went wrong, already translated.
            tip: How to fix it, already translated.
        """
        super().__init__(message)
        self.message = message
        self.tip = tip


class ConfigError(MediaDedupError):
    """The configuration file or an override is invalid."""


class MountError(MediaDedupError):
    """A mount point is missing, read-only when it must be writable, or empty."""


class JournalError(MediaDedupError):
    """A journal cannot be found or read."""


class CrossCheckError(MediaDedupError):
    """Czkawka results are missing, unreadable, or cover other folders."""


class DecisionsError(MediaDedupError):
    """A decisions file is missing, invalid, or made for another audit."""
