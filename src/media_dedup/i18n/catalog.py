"""Load a gettext `.po` catalog without any compiled `.mo` file in the repository."""

from __future__ import annotations

import gettext
import io
from importlib.resources import files

import polib

from media_dedup.constants import GETTEXT_DOMAIN, Locale

_LOCALES_PACKAGE = "media_dedup.i18n"
_LOCALES_DIR = "locales"
_MESSAGES_DIR = "LC_MESSAGES"


def load_translations(locale: Locale) -> gettext.NullTranslations:
    """Build the translations of `locale` from its `.po` file, compiled in memory.

    English is the source language: it needs no catalog.

    Args:
        locale: Language to load.

    Returns:
        A GNU translations object, or a no-op one for English or a missing catalog.
    """
    if locale is Locale.EN:
        return gettext.NullTranslations()
    resource = (
        files(_LOCALES_PACKAGE)
        .joinpath(_LOCALES_DIR, locale.value, _MESSAGES_DIR)
        .joinpath(f"{GETTEXT_DOMAIN}.po")
    )
    if not resource.is_file():
        return gettext.NullTranslations()
    catalog = polib.pofile(resource.read_text(encoding="utf-8"))
    return gettext.GNUTranslations(io.BytesIO(catalog.to_binary()))
