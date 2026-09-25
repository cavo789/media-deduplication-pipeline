# .devcontainer/scripts/helpers/tool.sh
#
# Category "Tool" — run media-dedup from the sources, against /tmp/media-dedup/ instead of mounts.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat Tool
# @cmd dedup
# @desc Run media-dedup from the sources with every mount redirected to /tmp/media-dedup/ — e.g. 'dedup audit'
function dedup() {
    local -a env_vars
    mapfile -t env_vars < <(_media_dedup_env)
    (
        cd "$(_repo_root)" || return 1
        env "${env_vars[@]}" uv run --frozen --quiet media-dedup "$@"
    )
}

# @cat Tool
# @cmd demo
# @desc Generate sample photos/videos (duplicates, copies, broken files) in /tmp/media-dedup/data, then audit them
function demo() {
    local -r data_dir="/tmp/media-dedup/data"
    printf "🧪 Generating demo media in %s...\n" "${data_dir}"
    rm -rf "${data_dir}"
    (
        cd "$(_repo_root)" || return 1
        uv run --frozen --quiet python -m tests.support.demo "${data_dir}"
    ) || return 1
    dedup audit "$@"
}
