# .devcontainer/scripts/helpers/docker.sh
#
# Category "Docker image" — build the shipped image, inspect its layers, run the end-to-end tests.
#
# Sourced by ../interactive.sh — no shebang, never executed directly.
# shellcheck shell=bash

# @cat Docker image
# @cmd image
# @desc Build the tool image media-dedup:latest from the root Dockerfile
function image() {
    printf "🏗️  Building media-dedup:latest...\n"
    docker build --tag media-dedup:latest "$(_repo_root)"
}

# @cat Docker image
# @cmd dive
# @desc Explore the layers of media-dedup:latest interactively with dive (build it first with 'image')
function dive() {
    # The socket path is resolved on the Docker host (docker-outside-of-docker), where it exists.
    docker run --rm -it \
        --volume /var/run/docker.sock:/var/run/docker.sock \
        wagoodman/dive:latest media-dedup:latest
}

# @cat Docker image
# @cmd dive_ci
# @desc Fail if media-dedup:latest wastes space (dive CI mode, strict efficiency thresholds)
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
# @desc Build the image then run the end-to-end tests (real docker run, :ro mounts, clean, undo)
function e2e() {
    image || return 1
    (
        cd "$(_repo_root)" || return 1
        pytest -m e2e "$@"
    )
}
