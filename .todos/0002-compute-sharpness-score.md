# 0002 — Compute a sharpness score for every image

- **Priority**: Medium
- **Batch**: similarity
- **Depends**: —
- **Files**: `src/media_dedup/scan/image_check.py`, `src/media_dedup/index/`, `src/media_dedup/report/`

## Context

digiKam's blur detection boils down to the variance of the Laplacian. Computing it (numpy,
on the downscaled grayscale image already decoded by the integrity check) lets later features
suggest the sharpest shot of a series — the user's burst concern (blurry shots, closed eyes).

## Acceptance

- [ ] Score computed during the existing decode (no second read of the file), cached in the index.
- [ ] Shown next to previews in the report.
- [ ] Tests on a sharp and a blurred version of the same synthetic image.

## Explicit NON-goals

- Eyes-closed or red-eyes detection (needs face landmark models).
