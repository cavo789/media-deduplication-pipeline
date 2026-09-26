# 0016 — Let users verify the audit themselves ("don't trust me, check")

- **Priority**: Medium
- **Batch**: report
- **Depends**: —
- **Files**: `src/media_dedup/report/builder.py`, `src/media_dedup/report/views.py`, `src/media_dedup/report/templates/report.html.j2`, `src/media_dedup/console/tables.py`, `src/media_dedup/services/audit.py`

## Context

"Exact duplicate" means the same SHA-256, then a byte-by-byte comparison right before every
deletion (`actions/verify.py`). That is mathematically certain, but users cannot see it. Give
them cheap, tool-independent ways to check a few cases themselves.

## Proposal

- **Random sample**: besides the largest groups, show about 30 image groups drawn at random
  (seeded by the run id, so it is reproducible), with thumbnails. Today the listed groups are
  mostly videos without previews.
- **Short SHA-256 per group** and a ready-to-paste PowerShell line to recompute it with
  Windows' own tool: `Get-FileHash "C:\…\a.jpg","C:\…\b.jpg"`. Same hash, same bytes: no need to
  trust media-dedup.
- **Group count in the terminal summary** (the HTML shows it, the terminal does not). Czkawka
  and other tools report groups, which makes comparisons possible (0013).
- A short "How do we know these are duplicates?" box in the report: same size, same SHA-256,
  compared byte by byte again before deletion, one file seen twice is never a duplicate.

## Acceptance

- [ ] Sample, hashes and PowerShell line in the report; group count in the terminal summary.
- [ ] `.po` translated; README + README_FR ("Reading the result").
