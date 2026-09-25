"""Translations: runtime catalogs, early locale resolution, catalog completeness."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

import polib
import pytest

from media_dedup.constants import Locale
from media_dedup.i18n import _, install, ngettext
from media_dedup.i18n.bootstrap import locale_from_argv, resolve_locale

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations

LOCALES = files("media_dedup.i18n").joinpath("locales")


def test_french_is_loaded_from_the_po_file() -> None:
    """Installing French translates simple and plural messages."""
    install(Locale.FR)
    assert _("Nothing was changed.") == "Rien n'a été modifié."
    assert ngettext("{count} report deleted.", "{count} reports deleted.", 2) == (
        "{count} rapports supprimés."
    )


def test_english_is_the_source_language() -> None:
    """English needs no catalog: messages come back unchanged."""
    install(Locale.EN)
    assert _("Nothing was changed.") == "Nothing was changed."


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--locale", "fr", "audit"], Locale.FR),
        (["audit", "--locale=fr"], Locale.FR),
        (["--locale", "xx"], None),
        (["--locale"], None),
        (["audit"], None),
    ],
)
def test_locale_from_argv(argv: list[str], expected: Locale | None) -> None:
    """`--locale` is found anywhere; invalid values are left to Typer."""
    assert locale_from_argv(argv) is expected


def test_resolve_locale_falls_back_to_config(
    locations: Locations,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without `--locale`, the configuration decides; a broken one means English."""
    monkeypatch.setenv("MEDIA_DEDUP_CONFIG_DIR", str(locations.config_dir))
    locations.config_file.write_text('[general]\nlocale = "fr"\n')
    assert resolve_locale(["audit"]) is Locale.FR
    locations.config_file.write_text("not = [valid")
    assert resolve_locale(["audit"]) is Locale.EN


def test_french_catalog_is_complete() -> None:
    """Every message of the template has a non-fuzzy French translation."""
    template = polib.pofile(LOCALES.joinpath("media_dedup.pot").read_text("utf-8"))
    french = polib.pofile(
        LOCALES.joinpath("fr", "LC_MESSAGES", "media_dedup.po").read_text("utf-8"),
    )
    translated = {entry.msgid for entry in french.translated_entries()}
    missing = [entry.msgid for entry in template if entry.msgid not in translated]
    assert missing == []
    assert french.fuzzy_entries() == []
