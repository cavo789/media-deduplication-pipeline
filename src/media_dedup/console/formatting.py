"""Human-friendly rendering of sizes and counts."""

from __future__ import annotations

from typing import Final

_UNITS: Final = ("B", "KB", "MB", "GB", "TB")
_STEP: Final = 1024.0


def human_size(size: int) -> str:
    """Render a byte count with a binary unit, e.g. `38.2 GB`.

    Args:
        size: Number of bytes.

    Returns:
        The rounded size with its unit.
    """
    value = float(size)
    for unit in _UNITS[:-1]:
        if abs(value) < _STEP:
            return f"{value:.0f} {unit}" if unit == _UNITS[0] else f"{value:.1f} {unit}"
        value /= _STEP
    return f"{value:.1f} {_UNITS[-1]}"
