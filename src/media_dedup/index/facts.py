"""What the index remembers about one file version."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from media_dedup.constants import BrokenReason
    from media_dedup.scan.models import VisualFacts


@dataclass(frozen=True, slots=True)
class FileFacts:
    """Facts computed for a file at a given size and modification time."""

    partial_digest: str | None = None
    full_digest: str | None = None
    integrity_checked: bool = False
    broken_reason: BrokenReason | None = None
    broken_detail: str = ""
    visual_checked: bool = False
    visual: VisualFacts | None = None

    def with_partial(self, digest: str) -> FileFacts:
        """Return a copy holding the partial digest.

        Args:
            digest: Partial SHA-256.

        Returns:
            The updated facts.
        """
        return replace(self, partial_digest=digest)

    def with_full(self, digest: str) -> FileFacts:
        """Return a copy holding the full digest.

        Args:
            digest: Full SHA-256.

        Returns:
            The updated facts.
        """
        return replace(self, full_digest=digest)

    def with_integrity(self, reason: BrokenReason | None, detail: str) -> FileFacts:
        """Return a copy holding the outcome of an integrity check.

        Args:
            reason: Why the file is broken, or None when healthy.
            detail: Decoder message, empty when healthy.

        Returns:
            The updated facts.
        """
        return replace(
            self,
            integrity_checked=True,
            broken_reason=reason,
            broken_detail=detail,
        )

    def with_visual(self, visual: VisualFacts | None) -> FileFacts:
        """Return a copy holding what an image looks like (None when unreadable).

        Args:
            visual: The visual facts computed while decoding the image.

        Returns:
            The updated facts.
        """
        return replace(self, visual_checked=True, visual=visual)
