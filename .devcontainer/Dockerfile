# syntax=docker/dockerfile:1.19
#
# Development image of the media-dedup devcontainer: the environment a human edits, lints and
# tests inside. The shipped tool is built by the root Dockerfile, never by this one — so no
# application COPY and no ENTRYPOINT here: the workspace is bind-mounted live by VS Code.

ARG PYTHON_IMAGE=python:3.14-slim-trixie
# Pinned to the same versions as the root Dockerfile so local runs never drift from the image.
ARG UV_VERSION=0.12.19
ARG FFMPEG_VERSION=9.0.2
# GitHub CLI: CI logs (gh run view --log-failed), runs and pull requests from the terminal.
ARG GH_VERSION=2.101.0

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM mwader/static-ffmpeg:${FFMPEG_VERSION} AS ffmpeg

# A floating tag is acceptable for a dev image: rebuilt often, blast radius is one laptop.
# hadolint ignore=DL3006
FROM ${PYTHON_IMAGE}

ARG DEV_USER=vscode
ARG USER_UID=1000
ARG USER_GID=1000
# Workspace path inside the container, used to source the cheatsheet from ~/.bashrc.
ARG APP_HOME=/workspaces/media-deduplication-pipeline
# Timezone of the developer, passed from the host's TZ variable by devcontainer.json
# (UTC when unset) — never hardcoded in this public file.
ARG TZ=Etc/UTC

# Zero junk in the repository: every cache Python tooling would drop in the working tree is
# redirected to /tmp, and the virtual environment lives in the home directory.
ENV TZ=${TZ} \
    PYTHONUNBUFFERED=1 \
    PYTHONPYCACHEPREFIX=/tmp/pycache \
    MYPY_CACHE_DIR=/tmp/mypy_cache \
    RUFF_CACHE_DIR=/tmp/ruff_cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest_cache" \
    COVERAGE_FILE=/tmp/.coverage \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/home/${DEV_USER}/.venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    VIRTUAL_ENV=/home/${DEV_USER}/.venv \
    PATH=/home/${DEV_USER}/.venv/bin:${PATH}

# Dev image: unpinned OS packages are acceptable (see devcontainer-dockerfile-best-practices).
# hadolint ignore=DL3008
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    less \
    libimage-exiftool-perl \
    openssh-client \
    procps \
    sqlite3 \
    sudo

COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/

# The release archive of this machine's architecture, checked against the published SHA-256
# before it is unpacked. pipefail: a failed download must not reach sha256sum as empty input.
ARG GH_VERSION
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN set -eux && \
    archive="gh_${GH_VERSION}_linux_$(dpkg --print-architecture)" && \
    release="https://github.com/cli/cli/releases/download/v${GH_VERSION}" && \
    curl -fsSL -o "/tmp/${archive}.tar.gz" "${release}/${archive}.tar.gz" && \
    curl -fsSL "${release}/gh_${GH_VERSION}_checksums.txt" | \
    grep " ${archive}.tar.gz$" | sed "s|  | /tmp/|" | sha256sum --check --strict - && \
    tar -xzf "/tmp/${archive}.tar.gz" -C /tmp && \
    install -m 0755 "/tmp/${archive}/bin/gh" /usr/local/bin/gh && \
    rm -rf "/tmp/${archive}" "/tmp/${archive}.tar.gz"

# Passwordless sudo: post-create.sh must chown the named volumes (bash history, ~/.claude),
# which Docker hands over root- or old-UID-owned on first mount. Devcontainer only — never
# copy this line into the root Dockerfile.
RUN set -eux && \
    groupadd -g "${USER_GID}" "${DEV_USER}" && \
    useradd -l -m -u "${USER_UID}" -g "${USER_GID}" -s /bin/bash "${DEV_USER}" && \
    echo "${DEV_USER} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${DEV_USER}" && \
    chmod 0440 "/etc/sudoers.d/${DEV_USER}"

USER ${DEV_USER}

# Mount points for the named volumes declared in devcontainer.json. History is a directory
# (not a file) so the volume can be mounted without Docker creating a directory in its place.
# ~/.ssh receives the host's keys, bind-mounted read-only (git push over SSH). ~/.config is a
# volume: tool settings and logins (e.g. the GitHub CLI token) survive rebuilds and never
# land in the workspace. Nothing may be baked into ~/.config here: the volume would hide it.
RUN mkdir -p "/home/${DEV_USER}/.bash_history" "/home/${DEV_USER}/.claude" \
    "/home/${DEV_USER}/.cache" "/home/${DEV_USER}/.ssh" "/home/${DEV_USER}/.config" && \
    chmod 700 "/home/${DEV_USER}/.ssh" "/home/${DEV_USER}/.config" && \
    touch "/home/${DEV_USER}/.bash_history/.bash_history"

# Persistent history, a recognisable prompt, and the cheatsheet on every interactive shell.
# The workspace is not mounted at build time, hence the [ -f ] guard.
# printf, not echo: dash's echo would interpret the prompt's backslash escapes.
RUN printf '%s\n' \
    "export HISTFILE=/home/${DEV_USER}/.bash_history/.bash_history" \
    'export HISTSIZE=10000' \
    'export HISTFILESIZE=10000' \
    'shopt -s histappend' \
    "PS1='\\n\\[\\e[0;33m\\]🐳 \\[\\e[0;36m\\]\\u\\[\\e[0m\\] \\w # '" \
    "[ -f \"${APP_HOME}/.devcontainer/scripts/interactive.sh\" ] && source \"${APP_HOME}/.devcontainer/scripts/interactive.sh\"" \
    >> "/home/${DEV_USER}/.bashrc"
