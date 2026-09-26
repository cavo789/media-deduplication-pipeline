# .devcontainer/scripts/helpers/github.sh
#
# Category "GitHub" — follow CI from the terminal with the GitHub CLI (gh). The login is asked
# once ('gh auth login'); its token is kept across rebuilds in the media-dedup-config volume
# (~/.config), outside the workspace: it can never be committed.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat GitHub
# @cmd ci
# @desc Latest CI runs of the current branch — e.g. 'ci 10'
function ci() {
    _gh_ready || return 1
    (
        cd "$(_repo_root)" || return 1
        gh run list --branch "$(git branch --show-current)" --limit "${1:-5}"
    )
}

# @cat GitHub
# @cmd ci_logs
# @desc Logs of the failed steps of the latest failed run (or of a run ID)
function ci_logs() {
    _gh_ready || return 1
    (
        cd "$(_repo_root)" || return 1
        local run_id="${1:-}"
        if [[ -z "${run_id}" ]]; then
            run_id="$(gh run list --status failure --limit 1 --json databaseId \
                --jq '.[0].databaseId // empty')" || return 1
        fi
        if [[ -z "${run_id}" ]]; then
            printf "✅ No failed run\n"
            return 0
        fi
        gh run view "${run_id}" --log-failed
    )
}

# _gh_ready — fail with a hint when the GitHub CLI is missing or not logged in.
function _gh_ready() {
    if ! command -v gh >/dev/null 2>&1; then
        printf "❌ The GitHub CLI is not installed: rebuild the devcontainer.\n" >&2
        return 1
    fi
    if ! gh auth status >/dev/null 2>&1; then
        printf "❌ The GitHub CLI is not logged in: run 'gh auth login' once.\n" >&2
        return 1
    fi
}
