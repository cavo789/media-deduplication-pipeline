"""Sidecars: small files (.xmp, .aae, .thm) holding the metadata or edits of a photo.

A sidecar belongs to the files of its folder sharing its name: `IMG_1.xmp` to
`IMG_1.CR2` (same name without extension) and `IMG_1.CR2.xmp` to `IMG_1.CR2` (the
whole name, as darktable writes it). Once none of them is left, it is an orphan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import TYPE_CHECKING

from media_dedup.constants import SIDECAR_EXTENSIONS

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from media_dedup.scan.models import MediaFile


@dataclass(frozen=True, slots=True)
class Sidecar:
    """A sidecar and the names of the files it belongs to, as the scan listed them."""

    file: MediaFile
    companions: frozenset[str]

    def is_orphan_without(self, removed: frozenset[Path]) -> bool:
        """Tell whether the sidecar is an orphan once `removed` files are gone.

        Args:
            removed: Files the plan deletes or moves.

        Returns:
            True when none of its files is left next to it.
        """
        folder = self.file.path.parent
        return all(folder / name in removed for name in self.companions)


def is_sidecar(name: str) -> bool:
    """Tell whether a file name is a sidecar's, case-insensitively.

    Args:
        name: A file name.

    Returns:
        True for `.xmp`, `.aae` and `.thm` files.
    """
    return PurePath(name).suffix.casefold() in SIDECAR_EXTENSIONS


def companions_of(sidecar: Path, names: Iterable[str]) -> frozenset[str]:
    """Return the names, among `names`, of the files `sidecar` belongs to.

    Args:
        sidecar: The sidecar.
        names: Names of the other entries of its folder (not subfolders).

    Returns:
        The names sharing its name, other sidecars excepted.
    """
    key = sidecar.stem.casefold()
    return frozenset(
        name
        for name in names
        if not is_sidecar(name)
        and key in {name.casefold(), PurePath(name).stem.casefold()}
    )


def accompanied(sidecars: Iterable[Sidecar]) -> frozenset[Path]:
    """Return the files that have a sidecar next to them.

    Args:
        sidecars: The sidecars the walk listed.

    Returns:
        The paths of the files they belong to.
    """
    return frozenset(
        sidecar.file.path.parent / name
        for sidecar in sidecars
        for name in sidecar.companions
    )
