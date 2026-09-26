"""The raw layers settings are merged from: file, environment, command line."""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING, Final, get_origin

from pydantic import BaseModel

from media_dedup.config.settings import Settings
from media_dedup.constants import ENV_PREFIX
from media_dedup.errors import ConfigError
from media_dedup.i18n import _

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

type Layer = dict[str, dict[str, object]]
_ENV_SEPARATOR = "__"
# Every `config.toml` table, so that each one is overridable from the environment.
_SECTIONS: Final[dict[str, type[BaseModel]]] = {
    name: field.annotation
    for name, field in Settings.model_fields.items()
    if isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel)
}


def read_file_layer(config_file: Path) -> Layer:
    """Read `config.toml`; a missing file is an empty layer.

    Args:
        config_file: Path of the configuration file.

    Returns:
        The file's tables, as parsed.

    Raises:
        ConfigError: The file exists but is not valid TOML.
    """
    if not config_file.is_file():
        return {}
    try:
        with config_file.open("rb") as stream:
            return tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        message = _("The configuration file {path} is not valid TOML: {error}")
        tip = _("Windows paths must use 'single quotes' in TOML, e.g. 'C:\\Photos'.")
        raise ConfigError(message.format(path=config_file, error=exc), tip) from exc


def read_env_layer(environ: Mapping[str, str]) -> Layer:
    """Collect `MEDIA_DEDUP_<SECTION>__<KEY>` variables; lists are JSON arrays.

    Args:
        environ: The process environment.

    Returns:
        The overrides found, by section.

    Raises:
        ConfigError: A list variable does not hold a JSON array.
    """
    layer: Layer = {}
    for section, model in _SECTIONS.items():
        for key, field in model.model_fields.items():
            name = f"{ENV_PREFIX}{section}{_ENV_SEPARATOR}{key}".upper()
            if name not in environ:
                continue
            value: object = environ[name]
            if get_origin(field.annotation) is tuple:
                value = _parse_json_list(name, environ[name])
            layer.setdefault(section, {})[key] = value
    return layer


def _parse_json_list(name: str, raw: str) -> list[str]:
    """Parse a JSON array of strings from an environment variable.

    Args:
        name: Variable name, for the error message.
        raw: Its value.

    Returns:
        The list of strings.

    Raises:
        ConfigError: The value is not a JSON array.
    """
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        message = _('{name} must be a JSON array, e.g. ["C:\\\\Photos"]')
        raise ConfigError(message.format(name=name)) from exc
    if not isinstance(value, list):
        message = _('{name} must be a JSON array, e.g. ["C:\\\\Photos"]')
        raise ConfigError(message.format(name=name))
    return [str(item) for item in value]


def merge_layers(*layers: Layer) -> Layer:
    """Merge layers section by section; later layers win.

    Args:
        *layers: From the lowest to the highest precedence.

    Returns:
        The merged layer.
    """
    merged: Layer = {}
    for layer in layers:
        for section, values in layer.items():
            merged.setdefault(section, {}).update(values)
    return merged
