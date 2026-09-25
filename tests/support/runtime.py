"""Build a `Runtime` rooted in a temporary directory, with in-process image workers."""

from __future__ import annotations

import io
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import TYPE_CHECKING, Final

from rich.console import Console

from media_dedup.config.loader import load_settings
from media_dedup.console.output import Output
from media_dedup.paths.locations import Locations
from media_dedup.paths.mount_kind import MountKind
from media_dedup.paths.mounts import MountTable
from media_dedup.scan.image_check import prepare_image_worker
from media_dedup.services.runtime import Runtime

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.config.layers import Layer

CONSOLE_WIDTH: Final = 200


def thread_pool() -> Executor:
    """A single in-process worker: covered by coverage, deterministic order.

    Returns:
        The executor.
    """
    return ThreadPoolExecutor(max_workers=1, initializer=prepare_image_worker)


def make_locations(base: Path, *missing: MountKind) -> Locations:
    """Create every mount point below `base`, except the `missing` ones.

    Args:
        base: Temporary directory.
        *missing: Mount points left unset (hence not persistent).

    Returns:
        Explicit locations, trusted as persistent.
    """
    values: dict[str, Path] = {}
    for kind in MountKind:
        if kind in missing:
            continue
        folder = base / kind.value
        folder.mkdir(parents=True, exist_ok=True)
        values[f"{kind.value}_dir"] = folder
    return Locations.model_validate(values)


def make_runtime(locations: Locations, cli: Layer | None = None) -> Runtime:
    """Build a runtime writing its output to memory.

    Args:
        locations: Mount points.
        cli: Command-line overrides.

    Returns:
        The runtime.
    """
    console = Console(file=io.StringIO(), width=CONSOLE_WIDTH, no_color=True)
    return Runtime(
        loaded=load_settings(locations, cli),
        locations=locations,
        mounts=MountTable(frozenset()),
        output=Output(console),
        cli_layer=cli or {},
        executor_factory=thread_pool,
    )


def output_of(runtime: Runtime) -> str:
    """Return everything printed so far.

    Args:
        runtime: A runtime built by `make_runtime`.

    Returns:
        The captured console text.
    """
    stream = runtime.output.console.file
    return stream.getvalue() if isinstance(stream, io.StringIO) else ""
