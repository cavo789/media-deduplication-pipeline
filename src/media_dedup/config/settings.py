"""The validated, immutable settings of one run."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, field_validator

from media_dedup.constants import (
    GENERATED_NAMES,
    GENERIC_FOLDERS,
    MEDIA_EXTENSIONS,
    SIDECAR_EXTENSIONS,
    ColorMode,
    Locale,
    Verbosity,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")
_FIRST_PRINTABLE = 0x20
_EXTENSION = re.compile(r"\.[\w-]+")


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
    """`[scan]` — which files are analysed: photos, RAW and videos, or those asked for.

    Any extension may be asked for (`pdf`, `docx`): such files are only compared byte
    for byte, never decoded, and their copies are moved to the quarantine.
    """

    model_config = _FROZEN

    extensions: tuple[str, ...] = ()

    @field_validator("extensions")
    @classmethod
    def _valid_extensions(cls, extensions: tuple[str, ...]) -> tuple[str, ...]:
        """Normalise `PNG`, `png` or `.png` to `.png` and reject invalid ones.

        Comma-separated values (`"png,webp"`) are split. Empty means every media
        extension. Sidecars are refused: they follow the photo of the same name.

        Args:
            extensions: Configured extensions.

        Returns:
            The lowercase extensions with their dot, without duplicates.

        Raises:
            ValueError: An extension is malformed or is a sidecar's.
        """
        parts = (part.strip() for item in extensions for part in item.split(","))
        normalized = tuple(
            dict.fromkeys(f".{part.lstrip('.').casefold()}" for part in parts if part)
        )
        malformed = [ext for ext in normalized if not _EXTENSION.fullmatch(ext)]
        if malformed:
            message = (
                f"invalid extension {', '.join(malformed)}: letters, digits, '-' and "
                "'_' only, such as pdf"
            )
            raise ValueError(message)
        sidecars = [ext for ext in normalized if ext in SIDECAR_EXTENSIONS]
        if sidecars:
            message = (
                f"{', '.join(sidecars)}: sidecars follow the photo of the same name, "
                "they are not analysed on their own"
            )
            raise ValueError(message)
        return normalized

    @property
    def other_files(self) -> tuple[str, ...]:
        """The extensions asked for that are not photos, RAW files or videos.

        Returns:
            Those extensions, in the configured order.
        """
        return tuple(ext for ext in self.extensions if ext not in MEDIA_EXTENSIONS)


def supported_extensions() -> str:
    """List every media extension (the default scope), for help texts.

    Returns:
        The extensions without their dot, sorted and comma-separated.
    """
    return ", ".join(sorted(ext.lstrip(".") for ext in MEDIA_EXTENSIONS))


class KeepSettings(BaseModel):
    r"""`[keep]` — names that say nothing, so that another copy's name is kept instead.

    Regular expressions matching the whole name, case ignored: file names without
    extension (`IMG_\d+`) and folder names (`DCIM`). An empty list disables the rule.
    """

    model_config = _FROZEN

    generated_names: tuple[str, ...] = GENERATED_NAMES
    generic_folders: tuple[str, ...] = GENERIC_FOLDERS

    @field_validator("generated_names", "generic_folders")
    @classmethod
    def _valid_patterns(cls, patterns: tuple[str, ...]) -> tuple[str, ...]:
        """Reject patterns that are not valid regular expressions.

        Args:
            patterns: Configured patterns.

        Returns:
            The patterns, unchanged.

        Raises:
            ValueError: A pattern does not compile.
        """
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                message = f"{pattern!r} is not a valid regular expression: {exc}"
                raise ValueError(message) from exc
        return patterns


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
    keep: KeepSettings = KeepSettings()
    clean: CleanSettings = CleanSettings()
