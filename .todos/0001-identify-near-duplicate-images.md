# 0001 — Identify near-duplicate images (resized or recompressed copies)

- **Priority**: High
- **Batch**: similarity
- **Depends**: —
- **Files**: `src/media_dedup/scan/`, `src/media_dedup/plan/`, `src/media_dedup/index/repository.py`, `src/media_dedup/report/templates/report.html.j2`

## Context

Exact duplicates are handled. The next biggest win is the *same photo* saved again at another
size or quality (WhatsApp/Messenger exports, "reduced for email" copies, EXIF stripped by an
upload). They are not byte-identical, so `clean` cannot see them yet.

Approach agreed in the initial plan: dHash + pHash (64-bit, computed with numpy after
`ImageOps.exif_transpose`), cached in the SQLite index; multi-index hashing (4 × 16-bit
buckets) for the strict threshold. A pair is a "near duplicate" only when the Hamming
distance is ≤ 2, the aspect ratio is identical (±1 %), and the EXIF `DateTimeOriginal` is equal
or missing on the smaller file. The highest resolution (then the largest file) is kept.

## Acceptance

- [ ] New tier `near`, reported in its own report section with side-by-side previews.
- [ ] `clean` never acts on it unless `--tier near` is given explicitly.
- [ ] A burst (same camera, different `DateTimeOriginal`) is never classified `near`.
- [ ] Tests: resized copy, recompressed copy, EXIF-stripped copy, rotated copy found; burst shots not.
- [ ] README.md and README_FR.md document the tier.

## Explicit NON-goals

- Bursts and "similar" photos (see the burst TODO): never cleaned automatically.
