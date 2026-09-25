# .devcontainer/scripts/helpers/docker.sh
#
# Category "Docker image" — build the shipped image, inspect its layers, run the end-to-end tests.
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
# @cmd push
# @desc Build + publish to Docker Hub (latest, version)
function push() {
    # The namespace is overridable so a fork can publish under its own Docker Hub account.
    local -r repository="${DOCKER_HUB_NAMESPACE:-cavo789}/media-dedup"
    local version
    version="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$(_repo_root)/pyproject.toml")"
    if [[ -z "${version}" ]]; then
        printf "❌ Cannot read the version from pyproject.toml\n" >&2
        return 1
    fi

    build || return 1

    local tag
    for tag in latest "${version}"; do
        docker tag media-dedup:latest "${repository}:${tag}" || return 1
        printf "🚀 Pushing %s:%s...\n" "${repository}" "${tag}"
        if ! docker push "${repository}:${tag}"; then
            printf "❌ Push failed — log in first with: docker login --username %s\n" \
                "${repository%%/*}" >&2
            return 1
        fi
    done
    printf "✅ Published https://hub.docker.com/r/%s\n" "${repository}"
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
