"""The validated, immutable settings of one run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from media_dedup.constants import MEDIA_EXTENSIONS, ColorMode, Locale, Verbosity

_FROZEN = ConfigDict(frozen=True, extra="forbid")
_FIRST_PRINTABLE = 0x20


class GeneralSettings(BaseModel):
    """`[general]` — interface language, log level and colours."""

    model_config = _FROZEN

    locale: Locale = Locale.EN
    verbosity: Verbosity = Verbosity.INFO
    color: ColorMode = ColorMode.AUTO


class FolderSettings(BaseModel):
    """`[folders]` — host paths that steer which copy is kept, never folder names.

    `protected` folders are never modified and always hold the copy kept (identical
    files elsewhere are deleted); `excluded` folders are not analysed at all.
    """

    model_config = _FROZEN

    preferred: tuple[str, ...] = ()
    protected: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()

    @field_validator("preferred", "protected", "excluded")
    @classmethod
    def _no_control_character(cls, paths: tuple[str, ...]) -> tuple[str, ...]:
        r"""Reject paths holding control characters.

        In TOML, `"D:\backup"` silently turns `\b` into a backspace: the folder would
        never match, and a *protected* folder would protect nothing.

        Args:
            paths: Configured paths.

        Returns:
            The paths, unchanged.

        Raises:
            ValueError: A path contains a control character.
        """
        for path in paths:
            if any(ord(char) < _FIRST_PRINTABLE for char in path):
                message = (
                    f"{path!r} contains a control character: write Windows paths "
                    "between 'single quotes' in config.toml"
                )
                raise ValueError(message)
        return paths


class ScanSettings(BaseModel):
    """`[scan]` — which media files are analysed."""

    model_config = _FROZEN

    extensions: tuple[str, ...] = ()

    @field_validator("extensions")
    @classmethod
    def _supported_extensions(cls, extensions: tuple[str, ...]) -> tuple[str, ...]:
        """Normalise `PNG`, `png` or `.png` to `.png` and reject unsupported ones.

        Comma-separated values (`"png,webp"`) are split. Empty means every supported
        extension.

        Args:
            extensions: Configured extensions.

        Returns:
            The lowercase extensions with their dot, without duplicates.

        Raises:
            ValueError: An extension is not a supported media type.
        """
        parts = (part.strip() for item in extensions for part in item.split(","))
        normalized = tuple(
            dict.fromkeys(f".{part.lstrip('.').casefold()}" for part in parts if part)
        )
        unknown = [ext for ext in normalized if ext not in MEDIA_EXTENSIONS]
        if unknown:
            message = (
                f"unsupported extension {', '.join(unknown)}; supported: "
                f"{supported_extensions()}"
            )
            raise ValueError(message)
        return normalized


def supported_extensions() -> str:
    """List every supported media extension, for help texts and error messages.

    Returns:
        The extensions without their dot, sorted and comma-separated.
    """
    return ", ".join(sorted(ext.lstrip(".") for ext in MEDIA_EXTENSIONS))


class CleanSettings(BaseModel):
    """`[clean]` — behaviour of the `clean` command."""

    model_config = _FROZEN

    confirm: bool = True


class Settings(BaseModel):
    """Every setting of the tool, one section per `config.toml` table."""

    model_config = _FROZEN

    general: GeneralSettings = GeneralSettings()
    folders: FolderSettings = FolderSettings()
    scan: ScanSettings = ScanSettings()
    clean: CleanSettings = CleanSettings()
