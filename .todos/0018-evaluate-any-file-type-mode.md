# 0018 — Evaluate a generic mode: duplicates of any file type

- **Priority**: Low — decide scope first
- **Batch**: scan
- **Depends**: —
- **Files**: `src/media_dedup/scan/filters.py`, `src/media_dedup/constants.py`, `src/media_dedup/scan/broken.py`, `src/media_dedup/config/settings.py`

## Context

A user asked whether media-dedup could find duplicates of any file (`.docx`, `.pdf`, …). The
exact pipeline (size → partial SHA-256 → full SHA-256 → byte compare before delete) is
type-agnostic. Only the walker's extension filter and the integrity checks (Pillow, `ffprobe`)
are media-specific.

The risk is different, though. For photos, the path is only organisation. For documents and
software, the path is **functional**: identical `LICENSE`, `__init__.py`, templates shared by
two projects, `node_modules`, `.git` objects, application folders. Deleting "a copy" there breaks
things, even though no byte is lost.

## Options

- Out of scope: point to Czkawka (already generic, see 0013).
- Opt-in mode (`--all-files` or `scan.extensions = ["*"]`), with:
  - default exclusions (`.git`, `node_modules`, `Program Files`, `AppData`, `Windows`);
  - a minimal size;
  - quarantine instead of deletion for non-media files;
  - type detection by content (magic bytes, pure-Python library) to route integrity checks:
    images to Pillow, videos to `ffprobe`, other types none (or PDF/zip checks later).

## Acceptance

- [ ] Decision recorded (scope and name of the tool). If implemented: the options above,
  documented, with the risk explained in README + README_FR.
