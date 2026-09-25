# 0006 — Support RAW files (previews and integrity)

- **Priority**: Low
- **Batch**: scan
- **Depends**: —
- **Files**: `src/media_dedup/scan/image_check.py`, `src/media_dedup/report/thumbnails.py`

## Context

RAW files (CR2, NEF, ARW, DNG, …) are deduplicated exactly, but Pillow cannot decode them: no
integrity check, no preview. Their embedded JPEG preview (e.g. via `rawpy`/libraw) would give both.

## Acceptance

- [ ] Previews of RAW files in the report.
- [ ] Truncated RAW detected as broken.
- [ ] Image size impact measured with `dive`.
