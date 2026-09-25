"""Internationalisation: gettext `.po` catalogs loaded at runtime, English by default.

Every user-facing string goes through `_()` (or `ngettext()` for plurals) so that
`pybabel extract` finds it. The active translation lives in a context variable,
installed once at start-up by `install()`.
"""

from __future__ import annotations

import gettext
from contextvars import ContextVar
from typing import TYPE_CHECKING

from media_dedup.i18n.catalog import load_translations

if TYPE_CHECKING:
    from media_dedup.constants import Locale

_ACTIVE: ContextVar[gettext.NullTranslations] = ContextVar(
    "media_dedup_translations",
    default=gettext.NullTranslations(),  # noqa: B039 - stateless, safe to share
)


def install(locale: Locale) -> gettext.NullTranslations:
    """Activate the catalog of `locale` for every later `_()` call.

    Args:
        locale: Language to activate.

    Returns:
        The translations object, also usable by Jinja's i18n extension.
    """
    translations = load_translations(locale)
    _ACTIVE.set(translations)
    return translations


def active() -> gettext.NullTranslations:
    """Return the translations currently in use.

    Returns:
        The active translations (a no-op catalog before `install()`).
    """
    return _ACTIVE.get()


def _(message: str) -> str:
    """Translate `message` into the active language.

    Args:
        message: English source text.

    Returns:
        The translation, or `message` itself when none exists.
    """
    return _ACTIVE.get().gettext(message)


def ngettext(singular: str, plural: str, count: int) -> str:
    """Translate a message whose wording depends on `count`.

    Args:
        singular: English text for one item.
        plural: English text for several items.
        count: Number of items, selecting the plural form.

    Returns:
        The translation matching `count`.
    """
    return _ACTIVE.get().ngettext(singular, plural, count)
