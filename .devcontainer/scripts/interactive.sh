#!/bin/bash
# .devcontainer/scripts/interactive.sh
#
# Purpose: dynamic interactive shell for the media-dedup devcontainer.
# This script uses annotations to build a real-time cheatsheet.
#
# It is the launcher only: the commands themselves live one per category in helpers/, and the
# cheatsheet engine that renders them lives in helpers/_cheatsheet.sh. Adding a command means
# adding it to the matching module with its @cat/@cmd/@desc annotations — nothing here has to
# change except its `export -f` line below.

# --- MODULE LOADING ---

# Resolving helpers/ relative to THIS file (not a hardcoded path) keeps the launcher working
# wherever the workspace is mounted.
INTERACTIVE_SCRIPTS_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
export INTERACTIVE_SCRIPTS_DIR

# The modules have no load-time dependency on each other — they only define functions — so
# alphabetical glob order is fine. The `-r` guard keeps a shell from dying on an unmatched glob.
for _module in "${INTERACTIVE_SCRIPTS_DIR}"/helpers/*.sh; do
    [[ -r "${_module}" ]] || continue
    # shellcheck source=/dev/null
    source "${_module}"
done
unset _module

alias ls='ls -alh --color=auto'

# --- PUBLIC SURFACE ---

# Export functions for subshells. Kept centralised here rather than spread across the modules:
# this list IS the public surface of the cheatsheet, and one place to read it beats seven.
export -f _repo_root
export -f _media_dedup_env
export -f check
export -f format
export -f tests
export -f build
export -f push
export -f dive
export -f dive_ci
export -f e2e
export -f dedup
export -f demo
export -f reports
export -f reports_stop
export -f i18n_extract
export -f i18n_update
export -f todos
export -f welcome

# Display on startup
welcome
