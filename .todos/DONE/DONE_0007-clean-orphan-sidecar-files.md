# 0007 — Clean orphan sidecar files (.xmp, .aae, .thm)

- **Priority**: Medium
- **Batch**: scan
- **Depends**: —
- **Files**: `src/media_dedup/scan/filters.py`, `src/media_dedup/plan/`, `src/media_dedup/actions/clean.py`

## Context

Sidecars are small companion files: `.AAE` (iPhone edits), `.XMP` (Lightroom/digiKam metadata),
`.THM` (camcorder thumbnails). v1 never touches them. Once `clean` removes duplicate photos,
some sidecars become *orphans* (their photo no longer exists next to them) and are useless.
A sidecar that still accompanies a photo carries its edits and must stay.

## Acceptance

- [ ] Orphan = no media file with the same stem in the same folder.
- [ ] Orphans listed in the report, deleted by `clean` with journal and undo.
- [ ] Tests: orphan removed, sidecar next to its photo kept.
