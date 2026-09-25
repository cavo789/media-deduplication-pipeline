"""Folder pairs: which folder keeps its copies, which one loses them, and the gain."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from media_dedup.plan.models import KeepDecision


@dataclass(frozen=True, slots=True)
class FolderPair:
    """Two folders sharing identical files: the fastest way to sanity-check a clean."""

    kept_in: Path
    removed_from: Path
    files: int
    size: int


def folder_pairs(decisions: Iterable[KeepDecision]) -> tuple[FolderPair, ...]:
    """Group the copies to delete by (kept folder, folder losing the copy).

    Args:
        decisions: The keep decisions of a plan.

    Returns:
        The pairs, the most space freed first.
    """
    counts: Counter[tuple[Path, Path]] = Counter()
    sizes: Counter[tuple[Path, Path]] = Counter()
    for decision in decisions:
        for file in decision.removable:
            pair = (decision.keeper.path.parent, file.path.parent)
            counts[pair] += 1
            sizes[pair] += decision.size
    pairs = (FolderPair(*pair, counts[pair], sizes[pair]) for pair in counts)
    return tuple(sorted(pairs, key=lambda pair: (-pair.size, -pair.files)))
