# .devcontainer/scripts/helpers/_common.sh
#
# Private helpers shared by the other modules. Deliberately un-annotated (no @cat/@cmd): they are
# building blocks, not commands, so they never show up in the cheatsheet.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# _repo_root — absolute path of the repository, whatever the current directory.
function _repo_root() {
    realpath "${INTERACTIVE_SCRIPTS_DIR}/../.."
}

# _media_dedup_env — print the MEDIA_DEDUP_*_DIR assignments that redirect every mount point of
# the tool to /tmp/media-dedup/, so a local run never needs Docker mounts nor touches the repo.
function _media_dedup_env() {
    local base="/tmp/media-dedup"
    local kind
    for kind in data config journal quarantine reports cache; do
        mkdir -p "${base}/${kind}"
        printf 'MEDIA_DEDUP_%s_DIR=%s/%s\n' "${kind^^}" "${base}" "${kind}"
    done
}
