"""Build the settings of a run: defaults < config.toml < environment < command line."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import ValidationError

from media_dedup.config.layers import (
    Layer,
    merge_layers,
    read_env_layer,
    read_file_layer,
)
from media_dedup.config.settings import Settings
from media_dedup.errors import ConfigError
from media_dedup.i18n import _
from media_dedup.i18n.templates import translated_environment

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.constants import Locale
    from media_dedup.paths.locations import Locations

_TEMPLATE_PACKAGE = "media_dedup.config"
_TEMPLATE_NAME = "config.toml.j2"


class Origin(StrEnum):
    """Where an effective setting comes from (shown by the `config` command)."""

    DEFAULT = "default"
    FILE = "file"
    ENV = "env"
    CLI = "cli"


@dataclass(frozen=True, slots=True)
class LoadedSettings:
    """Validated settings plus the raw layers they were merged from."""

    settings: Settings
    layers: dict[Origin, Layer] = field(default_factory=dict[Origin, Layer])

    def origin_of(self, section: str, key: str) -> Origin:
        """Tell which layer provided a setting.

        Args:
            section: TOML table, e.g. `general`.
            key: Key in the table, e.g. `locale`.

        Returns:
            One of the `Origin` values.
        """
        for origin in (Origin.CLI, Origin.ENV, Origin.FILE):
            if key in self.layers.get(origin, {}).get(section, {}):
                return origin
        return Origin.DEFAULT


def load_settings(locations: Locations, cli: Layer | None = None) -> LoadedSettings:
    """Load and validate the settings of this run.

    Args:
        locations: Mount points, giving the configuration file path.
        cli: Overrides typed on the command line, by section.

    Returns:
        The validated settings and their layers.

    Raises:
        ConfigError: A value is invalid; the message names the offending key.
    """
    layers = {
        Origin.FILE: read_file_layer(locations.config_file),
        Origin.ENV: read_env_layer(os.environ),
        Origin.CLI: cli or {},
    }
    merged = merge_layers(layers[Origin.FILE], layers[Origin.ENV], layers[Origin.CLI])
    try:
        settings = Settings.model_validate(merged)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        message = _("Invalid configuration ({details}).").format(details=details)
        tip = _(
            "Run 'media-dedup config' to see every setting and where it comes from."
        )
        raise ConfigError(message, tip) from exc
    return LoadedSettings(settings, layers)


def write_default_config(config_file: Path, locale: Locale) -> bool:
    """Create a commented `config.toml` when none exists yet.

    The comments are written in the active language, and `general.locale` is set to
    `locale`: a file created with `--locale fr` keeps the next runs in French.

    Args:
        config_file: Where the configuration file belongs.
        locale: The language of this run, stored in the file.

    Returns:
        True when the file was created.
    """
    if config_file.exists() or not config_file.parent.is_dir():
        return False
    environment = translated_environment(_TEMPLATE_PACKAGE, escaped=())
    text = environment.get_template(_TEMPLATE_NAME).render(locale=locale.value)
    config_file.write_text(text, encoding="utf-8")
    return True
