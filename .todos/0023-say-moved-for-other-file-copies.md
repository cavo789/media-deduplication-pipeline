# 0023 — Say "moved to the quarantine" for copies of other file types

- **Priority**: Low
- **Batch**: report
- **Depends**: —
- **Files**: `src/media_dedup/console/tables.py`, `src/media_dedup/report/templates/report.html.j2`, `src/media_dedup/report/templates/pair.html.j2`, `src/media_dedup/report/group_views.py`, `src/media_dedup/plan/pairs.py`

## Context

TODO 0018 (2026-09-26) lets `--ext` analyse other file types than media (`--ext pdf`); the
copies of those files are moved to the quarantine instead of being deleted
(`ActionKind.QUARANTINE_DUPLICATE`). `plan.csv` and the confirmation already say so, but the
folder pairs still say "deleted":

- console: *"1 file is both in C:\Docs (kept) and in D:\backup (deleted), 1 B freed."*;
- report: the *Deleted from* / *Will be deleted from* column and the pair page;
- the group block shows 🗑️ for every removable copy.

## Proposal

- `FolderPair` (or its view) knows whether its copies are moved (all of kind `OTHER`) or
  deleted; mixed pairs cannot happen (a group holds one extension, but check).
- Wording: *"(moved to the quarantine)"*, *"Moved from"*, 📦 instead of 🗑️; translate the new
  strings (`i18n_update`).

## Acceptance

- [ ] A PDF pair reads "moved to the quarantine" in the console, the report and the pair page.
- [ ] Media pairs are unchanged (existing tests still pass).
