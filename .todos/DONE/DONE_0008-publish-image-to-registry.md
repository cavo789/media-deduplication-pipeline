# 0008 — Publish the image to a registry

- **Priority**: Low
- **Batch**: docker
- **Depends**: —
- **Files**: `Dockerfile`, `README.md`, `README_FR.md`

## Context

Today the image is built locally (`docker build --tag media-dedup .`). Publishing it (e.g.
GHCR, multi-arch amd64/arm64, SBOM + provenance attestations) would make `docker run` work on
any machine without cloning the repository.

## Acceptance

- [ ] CI workflow building, testing (`e2e`) and pushing tagged images.
- [ ] READMEs switch the examples to the published image name.
