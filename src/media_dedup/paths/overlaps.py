r"""Detect a host folder mounted twice under the data directory.

`-v "C:\Photos:/data/c/Photos" -v "C:\photos\2019:/data/c/photos/2019"` shows every
file of `C:\Photos\2019` under two container paths: each would look like a duplicate
of itself, and deleting "the copy" would delete the only one. Windows ignores case,
the container does not, so the Windows sources are what must be compared.

A folder mounted inside its parent's mount point, at the same place
(`C:\Photos\2019` on `/data/c/Photos/2019`), is the same path: it is fine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class Overlap:
    r"""A Windows folder reachable through two container paths."""

    folder: str
    first: Path
    second: Path


def mount_overlaps(sources: Iterable[tuple[Path, str]]) -> tuple[Overlap, ...]:
    r"""List the Windows folders visible under two different mount points.

    Args:
        sources: Mount points and the Windows folder each comes from.

    Returns:
        One overlap per inner mount reachable through another mount, sorted.
    """
    mounts = sorted(set(sources))
    overlaps = {
        overlap
        for outer in mounts
        for inner in mounts
        if inner != outer and (overlap := _overlap(outer, inner)) is not None
    }
    return tuple(sorted(overlaps, key=lambda item: (item.second, item.first)))


def _overlap(outer: tuple[Path, str], inner: tuple[Path, str]) -> Overlap | None:
    r"""Tell whether `inner`'s folder is also visible, elsewhere, through `outer`.

    Args:
        outer: A mount point and its Windows folder.
        inner: Another mount point and its Windows folder.

    Returns:
        The overlap, or None when the folders are unrelated or the paths coincide.
    """
    outer_point, outer_folder = outer
    inner_point, inner_folder = inner
    outer_parts = _folded(PureWindowsPath(outer_folder).parts)
    inner_parts = PureWindowsPath(inner_folder).parts
    if _folded(inner_parts[: len(outer_parts)]) != outer_parts:
        return None
    below = inner_parts[len(outer_parts) :]
    if not below and inner_point < outer_point:
        return None  # the same folder twice: reported once, from the other side
    if inner_point.is_relative_to(outer_point) and _folded(
        inner_point.relative_to(outer_point).parts
    ) == _folded(below):
        return None
    return Overlap(inner_folder, outer_point.joinpath(*below), inner_point)


def _folded(parts: Iterable[str]) -> tuple[str, ...]:
    """Lower-case path parts the way Windows compares them.

    Args:
        parts: Path components.

    Returns:
        The case-folded components.
    """
    return tuple(part.casefold() for part in parts)
