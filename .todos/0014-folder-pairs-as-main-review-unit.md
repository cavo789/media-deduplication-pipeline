# 0014 — Make folder pairs the main review unit of the report

- **Priority**: High — the only way to review 12,633 copies in a few minutes
- **Batch**: report
- **Depends**: —
- **Files**: `src/media_dedup/plan/pairs.py`, `src/media_dedup/plan/models.py`, `src/media_dedup/report/builder.py`, `src/media_dedup/report/views.py`, `src/media_dedup/report/templates/report.html.j2`, `src/media_dedup/console/tables.py`

## Context

Nobody reviews 12,633 photos one by one, and a side-by-side album of exact duplicates would
show the same picture twice. The question users actually need answered is "which folder keeps
its copies, which folder loses them". Thousands of copies usually reduce to a few dozen folder
pairs. The report already has a "Folder pairs" table, but it sits below the fold, carries no
picture, and says nothing about completeness.

The group list shows the 500 largest groups (`Sizes.MAX_GROUPS_IN_REPORT`). With 44 GB to free,
those are mostly videos, which have no preview. The part of the report meant to reassure is
therefore mostly icons.

## Proposal

- Pairs first, sorted by number of files. Per pair: files, size, keep reason (see 0012), and 3–4
  sample thumbnails (images only, chosen deterministically).
- **Fully duplicated folder** flag: every media file of `removed_from` also exists in `kept_in`.
  It is the most reassuring sentence the tool can write ("`D:\Old phone\2019` is entirely a copy
  of `C:\Photos\2019`"). This needs per-folder file counts from the listing; the findings only
  carry `files_scanned` today.
- Each pair links to its groups (anchor or paginated page per pair), so the 500-group cap no
  longer hides whole folders.
- The terminal "Folders sharing identical files" block gets the same "fully duplicated" marker.

## Acceptance

- [ ] Pairs section first, with samples and the fully-duplicated flag.
- [ ] Every group reachable from its pair, whatever the total.
- [ ] Terminal and HTML agree; `.po` translated; README + README_FR ("Reading the result").
