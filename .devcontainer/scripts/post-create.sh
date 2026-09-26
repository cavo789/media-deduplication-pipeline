#!/usr/bin/env bash
# .devcontainer/scripts/post-create.sh
#
# Runs once per container creation (devcontainer.json postCreateCommand): reclaims the named
# volumes, installs the project, wires pre-commit and makes Claude's memory survive rebuilds.

set -o errexit
set -o nounset
set -o pipefail

WORKSPACE_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.." && pwd)"
readonly WORKSPACE_DIR

# Named volumes come back root-owned (first mount) or owned by the image's default UID, which
# updateRemoteUserUID may have changed since — take them back before anything writes there.
reclaim_volumes() {
    sudo chown -R "$(id -u):$(id -g)" "${HOME}/.bash_history" "${HOME}/.claude" \
        "${HOME}/.config"
}

install_project() {
    printf "📦 Installing the project and its dev dependencies (uv sync)...\n"
    uv sync --locked
}

install_git_hooks() {
    if [[ ! -d "${WORKSPACE_DIR}/.git" ]]; then
        printf "ℹ️  Not a git repository yet: pre-commit hooks not installed.\n"
        return 0
    fi
    printf "🪝 Installing pre-commit hooks...\n"
    pre-commit install --config .config/.pre-commit-config.yaml
}

# Claude Code keeps per-project memory under ~/.claude/projects/<path with / replaced by ->.
# Pointing it at .claude/memory/ (git-ignored: private) keeps it on the host disk, so it
# survives rebuilds without ever being published.
link_claude_memory() {
    local project_dir="${HOME}/.claude/projects/${WORKSPACE_DIR//\//-}"
    local link="${project_dir}/memory"
    local target="${WORKSPACE_DIR}/.claude/memory"

    mkdir -p "${project_dir}" "${target}"
    if [[ -d "${link}" && ! -L "${link}" ]]; then
        # A real directory means memories were written before the link existed: keep them.
        cp -n "${link}"/* "${target}/" 2>/dev/null || true
        rm -rf "${link}"
    fi
    ln -sfn "${target}" "${link}"
    printf "🧠 Claude memory linked to %s\n" "${target}"
}

cd "${WORKSPACE_DIR}"
reclaim_volumes
install_project
install_git_hooks
link_claude_memory
printf "✅ Devcontainer ready — open a new terminal to see the cheatsheet.\n"
