# 0003 — Detect burst series and suggest the best shot

- **Priority**: Medium
- **Batch**: similarity
- **Depends**: 0001, 0002
- **Files**: `src/media_dedup/plan/`, `src/media_dedup/report/`

## Context

A burst (same camera, `DateTimeOriginal` a few seconds apart, similar pixels) is curation, not
duplication: 2 shots may be great and 8 blurry. The tool must group them and *suggest* — never
delete on its own.

## Acceptance

- [ ] Burst groups built from EXIF time proximity + perceptual distance (BK-tree).
- [ ] Report section listing each series, the suggested sharpest shot highlighted.
- [ ] No burst file is ever part of a `clean` plan.

## Explicit NON-goals

- Deleting burst shots (see the review UI TODO).
