# 0020 — Publish version 0.1.1 on Docker Hub (maintainer steps)

- **Priority**: High — the published `latest` and `0.1.0` images still count a folder mounted twice as its own duplicates
- **Batch**: docker
- **Depends**: —
- **Files**: `README.md`, `README_FR.md`

## Context

`pyproject.toml`, `uv.lock` and the Dockerfile label say 0.1.1. The CI workflow
(`.github/workflows/ci.yml`) publishes `cavo789/media-dedup:<version>` and `:latest` for
amd64 and arm64 when a `vX.Y.Z` tag is pushed; the devcontainer helper `release` creates that
tag. Nothing has been published since 0.1.0 (pushed by hand with the former `push` helper), so
Docker Hub users still run an image without the same-file protection (6b3ddaf), the report
aids, the meaningful-name keep rule and `crosscheck`.

Most steps need the maintainer's accounts: they cannot be done from the devcontainer.

## Steps

1. Docker Hub → Account settings → Personal access tokens: create a token with
   *Read & Write* scope.
2. GitHub → repository Settings → Secrets and variables → Actions: add
   `DOCKERHUB_USERNAME` (`cavo789`) and `DOCKERHUB_TOKEN` (the token).
3. GitHub → Actions: check that the first CI run on `main` (quality, image e2e) is green; fix
   it first otherwise.
4. README + README_FR, *Reading the result*: the "Groups of identical files" line of the
   example (`11,904` / `11.904`) was made up. Replace it with the real value of the same audit,
   or drop the line from the example.
5. In the devcontainer, on an up-to-date, clean `main`: run `release` (it tags `v0.1.1` and
   pushes the tag).
6. Follow the *Publish to Docker Hub* job, then check Docker Hub: tags `0.1.1` and `latest`,
   each listing `linux/amd64` and `linux/arm64`.
7. On Windows: `docker pull cavo789/media-dedup`, then `docker run --rm cavo789/media-dedup
   --version` prints `media-dedup 0.1.1`; audit a folder, and mount a folder twice to see the
   refusal.

## Acceptance

- [ ] `cavo789/media-dedup:0.1.1` and `:latest` published by CI, amd64 and arm64.
- [ ] The README example shows real numbers only.
- [ ] `--version` of the pulled image prints 0.1.1.
