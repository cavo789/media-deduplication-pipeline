# syntax=docker/dockerfile:1.19
#
# media-dedup — the shipped image. Build: `docker build --tag media-dedup .`
# Run:  docker run --rm -it -v "C:\Photos:/data/c/Photos:ro" media-dedup audit
# The development environment is built by .devcontainer/Dockerfile, never by this file.

# Base image pinned by digest: this is what users run on their photos.
ARG PYTHON_IMAGE=python:3.14-slim-trixie@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2
ARG UV_VERSION=0.12.19
ARG FFMPEG_VERSION=9.0.2

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv
FROM mwader/static-ffmpeg:${FFMPEG_VERSION} AS ffmpeg

# --- builder: resolve the locked dependencies, then install the project as a wheel ---------
FROM ${PYTHON_IMAGE} AS builder

COPY --from=uv /uv /usr/local/bin/uv

# The virtual environment lives at the same path in both stages: its scripts hardcode it.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

# Dependencies first: this layer is only rebuilt when the lockfile changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# --- runtime: the interpreter, the virtual environment and ffprobe — nothing else ---------
FROM ${PYTHON_IMAGE} AS runtime

ARG VERSION=0.1.0
ARG APP_UID=1000
ARG APP_GID=1000

LABEL org.opencontainers.image.title="media-dedup" \
      org.opencontainers.image.description="Find and safely clean duplicate photos and videos across folders and disks." \
      org.opencontainers.image.version="${VERSION}"

# Avoid .pyc cache files from build-time pip/pre-commit invocations, and unbuffered stdout for
# any Python process run interactively in this container.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/opt/venv/bin:${PATH}

# Every mount point exists and belongs to the app user: a named volume mounted there for the
# first time inherits that ownership (e.g. -v media-dedup-cache:/cache).
RUN groupadd --gid "${APP_GID}" app && \
    useradd --uid "${APP_UID}" --gid "${APP_GID}" --no-create-home --shell /usr/sbin/nologin app && \
    mkdir -p /data /config /journal /quarantine /reports /cache && \
    chown app:app /config /journal /quarantine /reports /cache

COPY --from=ffmpeg /ffprobe /usr/local/bin/ffprobe
COPY --from=builder /opt/venv /opt/venv

USER ${APP_UID}:${APP_GID}
WORKDIR /tmp

ENTRYPOINT ["media-dedup"]
CMD ["--help"]
