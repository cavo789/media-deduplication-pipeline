"""Settings layers: defaults < config.toml < environment < command line."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from media_dedup.config.loader import Origin, load_settings, write_default_config
from media_dedup.config.settings import GeneralSettings, Settings
from media_dedup.constants import ColorMode, Locale, Verbosity
from media_dedup.errors import ConfigError
from media_dedup.i18n import install

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations


def test_defaults_without_any_file(locations: Locations) -> None:
    """No file, no variable, no option: built-in defaults."""
    loaded = load_settings(locations)
    assert loaded.settings == Settings()
    assert loaded.origin_of("general", "locale") is Origin.DEFAULT


def test_precedence_cli_over_env_over_file(
    locations: Locations,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each layer overrides the previous one, key by key."""
    locations.config_file.write_text(
        '[general]\nlocale = "fr"\nverbosity = "debug"\ncolor = "never"\n',
    )
    monkeypatch.setenv("MEDIA_DEDUP_GENERAL__VERBOSITY", "error")
    monkeypatch.setenv("MEDIA_DEDUP_GENERAL__COLOR", "always")
    loaded = load_settings(locations, {"general": {"color": "auto"}})
    general = loaded.settings.general
    assert (general.locale, general.verbosity, general.color) == (
        Locale.FR,
        Verbosity.ERROR,
        ColorMode.AUTO,
    )
    assert [
        loaded.origin_of("general", key) for key in ("locale", "verbosity", "color")
    ] == [
        Origin.FILE,
        Origin.ENV,
        Origin.CLI,
    ]


def test_env_lists_and_booleans(
    locations: Locations, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lists come as JSON arrays, booleans as text."""
    monkeypatch.setenv("MEDIA_DEDUP_FOLDERS__PROTECTED", '["D:\\\\backup"]')
    monkeypatch.setenv("MEDIA_DEDUP_CLEAN__CONFIRM", "false")
    settings = load_settings(locations).settings
    assert settings.folders.protected == ("D:\\backup",)
    assert settings.clean.confirm is False


@pytest.mark.parametrize("value", ["not json", '{"a": 1}'])
def test_env_list_must_be_a_json_array(
    locations: Locations,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    """A malformed list variable is a configuration error."""
    monkeypatch.setenv("MEDIA_DEDUP_FOLDERS__EXCLUDED", value)
    with pytest.raises(ConfigError, match="JSON array"):
        load_settings(locations)


def test_invalid_toml_explains_quotes(locations: Locations) -> None:
    """Double-quoted Windows paths are the classic TOML mistake: the tip says so."""
    locations.config_file.write_text('[folders]\nprotected = ["D:\\Photos"]\n')
    with pytest.raises(ConfigError) as caught:
        load_settings(locations)
    assert caught.value.tip is not None
    assert "single quotes" in caught.value.tip


def test_invalid_value_names_the_key(locations: Locations) -> None:
    """Validation errors point at the offending key."""
    locations.config_file.write_text('[general]\nlocale = "de"\n')
    with pytest.raises(ConfigError, match=r"general\.locale"):
        load_settings(locations)


def test_default_template_is_written_once_and_valid(locations: Locations) -> None:
    """The commented template matches the defaults and is never overwritten."""
    assert write_default_config(locations.config_file, Locale.EN)
    assert load_settings(locations).settings == Settings()
    assert not write_default_config(locations.config_file, Locale.FR)
    assert all(
        len(line) <= 88 for line in locations.config_file.read_text().splitlines()
    )


def test_french_template_keeps_the_next_runs_in_french(locations: Locations) -> None:
    """Created in French: French comments, and `locale = "fr"` for the next runs."""
    install(Locale.FR)
    assert write_default_config(locations.config_file, Locale.FR)
    text = locations.config_file.read_text()
    assert "Langue de l'interface" in text
    settings = load_settings(locations).settings
    assert settings == Settings(general=GeneralSettings(locale=Locale.FR))


def test_escaped_backspace_in_a_path_is_refused(locations: Locations) -> None:
    r"""`"D:\backup"` is valid TOML but holds a backspace: refused, never ignored."""
    locations.config_file.write_text('[folders]\nprotected = ["D:\\backup"]\n')
    with pytest.raises(ConfigError, match="single quotes"):
        load_settings(locations)
