# 0019 — Explain unwritable mount points instead of crashing

- **Priority**: Medium
- **Batch**: mounts
- **Depends**: —
- **Files**: `src/media_dedup/services/reporting.py`, `src/media_dedup/report/writer.py`, `src/media_dedup/services/clean.py`, `src/media_dedup/cli/context.py`, `README.md`, `README_FR.md`

## Context

Found on 2026-09-26 while testing `crosscheck`: when the folder mounted on `/reports` is
not writable by the container user, the run ends with a Python traceback
(`PermissionError: [Errno 13] Permission denied: '/reports/20260926-140016-audit'` in
`ReportWriter._new_folder`). The audit itself had succeeded.

It happens when a bind-mounted folder does not exist on the Docker host (Docker creates it,
owned by root), or from WSL/Linux with a folder owned by another user and no
`--user "$(id -u):$(id -g)"`. `/journal`, `/quarantine` and `/cache` can fail the same way.

## Proposal

- Check that every persistent mount the command writes to (`/reports`, `/journal`,
  `/quarantine`, `/cache`) is writable before the long analysis starts, next to the existing
  `:ro` checks in `CleanService.ensure_ready`. Report it as a `MountError` with a tip: create the
  folder on your computer first, or add `--user "$(id -u):$(id -g)"` from WSL/Linux.
- For `/reports` only, a failure after the audit becomes a warning: the results were already
  shown in the terminal.

## Acceptance

- [ ] No traceback for an unwritable mount point: a translated message and a tip.
- [ ] The audit summary stays visible when only the report cannot be written.
- [ ] Tests with a read-only `tmp_path` folder; README + README_FR (Warnings); `.po` translated.
