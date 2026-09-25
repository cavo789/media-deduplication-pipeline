"""Human-friendly rendering of sizes and counts, following the active language."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

from media_dedup.constants import Locale
from media_dedup.i18n import _, active_locale

_STEP: Final = 1024.0
_SIZE_DECIMALS: Final = 1
_SECONDS_PER_MINUTE: Final = 60

# (thousands separator, decimal separator) per language.
_SEPARATORS: Final = MappingProxyType(
    {
        Locale.EN: (",", "."),
        Locale.FR: (".", ","),
    },
)


def human_number(
    value: float,
    decimals: int = 0,
    locale: Locale | None = None,
) -> str:
    """Render a number with the thousands and decimal separators of the language.

    Args:
        value: The number.
        decimals: Digits after the decimal separator.
        locale: The language; the active one by default. Code running outside the
            main context (e.g. Rich's refresh thread) must pass it explicitly.

    Returns:
        `67,947` in English, `67.947` in French; `44.3` / `44,3` with one decimal.
    """
    thousands, decimal = _SEPARATORS[locale or active_locale()]
    text = f"{value:,.{decimals}f}"
    return text.translate(str.maketrans(",.", thousands + decimal))


def human_size(size: int) -> str:
    """Render a byte count with a binary unit, e.g. `38.2 GB` (`38,2 Go` in French).

    Args:
        size: Number of bytes.

    Returns:
        The rounded size with its translated unit.
    """
    units = _units()
    value = float(size)
    if abs(value) < _STEP:
        return f"{human_number(value)} {units[0]}"
    for unit in units[1:-1]:
        value /= _STEP
        if abs(value) < _STEP:
            return f"{human_number(value, _SIZE_DECIMALS)} {unit}"
    return f"{human_number(value / _STEP, _SIZE_DECIMALS)} {units[-1]}"


def human_duration(seconds: float) -> str:
    """Render a duration the way people say it: `12 s`, `3 min 05 s`, `1 h 02 min`.

    Args:
        seconds: The duration.

    Returns:
        The rounded duration (seconds are dropped beyond one hour).
    """
    minutes, secs = divmod(round(seconds), _SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, _SECONDS_PER_MINUTE)
    if hours:
        return f"{hours} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {secs:02d} s"
    return f"{secs} s"


def _units() -> tuple[str, ...]:
    """The translated size units, smallest first (French uses octets: `Ko`, `Go`).

    Returns:
        Bytes, then kilo-, mega-, giga- and terabytes.
    """
    return (_("B"), _("KB"), _("MB"), _("GB"), _("TB"))
