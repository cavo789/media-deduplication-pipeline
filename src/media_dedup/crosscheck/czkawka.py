"""Czkawka's side: the command media-dedup suggests, and the JSON results it writes.

`czkawka_cli dup -C <file>` (version 12) writes `{"<size>": [[{"path": ...}, ...]]}`:
groups of identical files, by size. Its paths are those of its own container, so the
command reuses media-dedup's mount points.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from media_dedup.constants import CZKAWKA_FILE_NAME, CZKAWKA_IMAGE, CZKAWKA_OUTPUT_DIR
from media_dedup.errors import CrossCheckError
from media_dedup.i18n import _

if TYPE_CHECKING:
    from collections.abc import Sequence

type Group = frozenset[Path]


class _Entry(BaseModel):
    """One file of a Czkawka group; the other fields (size, hash, date) are ignored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    path: str


_RESULTS = TypeAdapter(dict[str, list[list[_Entry]]])


def read_czkawka_groups(results: Path) -> tuple[Group, ...]:
    """Read the duplicate groups Czkawka found.

    Args:
        results: The JSON file written by `czkawka_cli dup -C`.

    Returns:
        One set of container paths per group.

    Raises:
        CrossCheckError: The file cannot be read or is not Czkawka's JSON.
    """
    try:
        by_size = _RESULTS.validate_json(results.read_bytes())
    except (OSError, ValidationError) as exc:
        raise CrossCheckError(
            _("{path} is not a Czkawka result file.").format(path=results),
            _("Run the Czkawka command again; it writes this file with -C."),
        ) from exc
    return tuple(
        frozenset(Path(entry.path) for entry in group)
        for groups in by_size.values()
        for group in groups
    )


@dataclass(frozen=True, slots=True)
class CzkawkaCommand:
    """Everything Czkawka needs to see the same files as media-dedup."""

    mounts: tuple[tuple[str, Path], ...]
    output_dir: str
    scope: CzkawkaScope

    def render(self) -> str:
        """Build the `docker run` line, ready to paste in PowerShell or bash.

        Returns:
            The command, on one line.
        """
        volumes = [f'-v "{host}:{point}:ro"' for host, point in self.mounts]
        volumes.append(f'-v "{self.output_dir}:{CZKAWKA_OUTPUT_DIR}"')
        results = f"{CZKAWKA_OUTPUT_DIR}/{CZKAWKA_FILE_NAME}"
        return " ".join(
            (
                "docker run --rm",
                *volumes,
                CZKAWKA_IMAGE,
                f"czkawka_cli dup -d {self.scope.data_dir} -m 1 -W -N",
                f"-x {','.join(self.scope.extensions)}",
                *(f'-e "{folder}"' for folder in self.scope.excluded),
                f"-C {results}",
            )
        )


@dataclass(frozen=True, slots=True)
class CzkawkaScope:
    """What media-dedup analyses: the data directory, the extensions, the exclusions."""

    data_dir: Path
    extensions: Sequence[str]
    excluded: tuple[Path, ...] = ()
