# .devcontainer/scripts/helpers/i18n.sh
#
# Category "i18n" — keep the gettext catalogs in sync with the source code.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat i18n
# @cmd i18n_extract
# @desc Extract every _() string (Python + Jinja templates) into the media_dedup.pot template
function i18n_extract() {
    (
        cd "$(_repo_root)" || return 1
        pybabel extract --omit-header --no-location --sort-output \
            --mapping-file .config/babel.cfg \
            --output-file src/media_dedup/i18n/locales/media_dedup.pot src
    )
}

# @cat i18n
# @cmd i18n_update
# @desc Extract, then merge new strings into every locale's .po file (translate them afterwards)
function i18n_update() {
    i18n_extract || return 1
    (
        cd "$(_repo_root)" || return 1
        pybabel update --ignore-pot-creation-date --ignore-obsolete --domain media_dedup \
            --input-file src/media_dedup/i18n/locales/media_dedup.pot \
            --output-dir src/media_dedup/i18n/locales
    )
}
