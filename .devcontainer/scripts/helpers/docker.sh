# .devcontainer/scripts/helpers/docker.sh
#
# Category "Docker image" — build the shipped image, inspect its layers, run the end-to-end tests,
# release a version.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat Docker image
# @cmd build
# @desc Build media-dedup:latest
function build() {
    printf "🏗️  Building media-dedup:latest...\n"
    docker build --tag media-dedup:latest "$(_repo_root)"
}

# @cat Docker image
# @cmd release
# @desc Tag vX.Y.Z (pyproject version) and push it: CI publishes the image
function release() {
    (
        cd "$(_repo_root)" || return 1
        local version
        version="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)"
        if [[ -z "${version}" ]]; then
            printf "❌ Cannot read the version from pyproject.toml\n" >&2
            return 1
        fi
        local -r tag="v${version}"

        if [[ -n "$(git status --porcelain)" ]]; then
            printf "❌ Uncommitted changes: commit them first, the tag must match main\n" >&2
            return 1
        fi
        if git rev-parse --quiet --verify "refs/tags/${tag}" >/dev/null; then
            printf "❌ %s already exists: bump the version in pyproject.toml first\n" "${tag}" >&2
            return 1
        fi
        git fetch --quiet origin main || return 1
        if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
            printf "❌ HEAD is not origin/main: push main (or pull) first\n" >&2
            return 1
        fi

        # CI builds amd64 + arm64, runs the end-to-end tests, then pushes :<version> and :latest.
        git tag --annotate "${tag}" --message "media-dedup ${version}" || return 1
        git push origin "${tag}" || return 1
        printf "✅ %s pushed: follow the publication in the repository's Actions tab\n" "${tag}"
    )
}

# @cat Docker image
# @cmd dive
# @desc Explore image layers with dive
function dive() {
    # The socket path is resolved on the Docker host (docker-outside-of-docker), where it exists.
    docker run --rm -it \
        --volume /var/run/docker.sock:/var/run/docker.sock \
        wagoodman/dive:latest media-dedup:latest
}

# @cat Docker image
# @cmd dive_ci
# @desc Fail if the image wastes space (dive CI)
function dive_ci() {
    # Thresholds are flags rather than a .dive-ci file: a file would have to be bind-mounted from
    # a host path, which docker-outside-of-docker makes awkward. The ~2.2 % of "user" waste is
    # inherited from the official python image's own layers (debconf/dpkg files rewritten by its
    # apt steps), not from ours — 3 % keeps the gate strict on everything this Dockerfile adds.
    local -r lowest_efficiency=0.98
    local -r highest_user_wasted_percent=0.03
    docker run --rm \
        --env CI=true \
        --volume /var/run/docker.sock:/var/run/docker.sock \
        wagoodman/dive:latest media-dedup:latest \
        --lowestEfficiency "${lowest_efficiency}" \
        --highestUserWastedPercent "${highest_user_wasted_percent}"
}

# @cat Docker image
# @cmd e2e
# @desc Build, then run the end-to-end tests
function e2e() {
    build || return 1
    (
        cd "$(_repo_root)" || return 1
        pytest -m e2e "$@"
    )
}
