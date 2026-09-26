# 0017 — Decide per folder pair in the report, then `clean --decisions`

- **Priority**: Medium
- **Batch**: review-ui
- **Depends**: 0014
- **Files**: `src/media_dedup/report/templates/report.html.j2`, `src/media_dedup/report/` (decisions format), `src/media_dedup/cli/cmd_clean.py`, `src/media_dedup/services/clean.py`, `src/media_dedup/plan/planner.py`, `README.md`, `README_FR.md`

## Context

A static report (opened from disk) cannot delete files: the browser sandbox forbids it. That is
a good thing. Deleting from the page would bypass the journal, the byte-by-byte check and
`undo`. The page can still **decide**, and the CLI then executes the decisions with every
safeguard.

For exact duplicates, decisions are made per folder pair (0014), not per photo:

- "swap": keep the copies in the other folder;
- "skip": leave this pair alone.

0004 (keyboard review UI for bursts) needs a decisions file too: both must share one format.

## Proposal

- In the report, each pair gets swap / skip controls. A "Download decisions.json" button builds
  the file in the browser with a Blob (no server). Decisions are also kept in `localStorage` so
  a review can be resumed.
- `clean --decisions <file>` re-audits, applies the decisions on top of the keep policy, and
  shows the summary before confirming. It refuses a decisions file from another set of mounts,
  or one whose pairs no longer exist.
- Optional: "remember" writes the swap into `config.toml` as `folders.preferred`, so the next
  audits apply it.
- Versioned schema (`{"version": 1, "pairs": [...]}`), reused by 0004.

## Acceptance

- [ ] Report → decisions.json → `clean --decisions`: journaled, `undo` restores.
- [ ] A stale or foreign decisions file is refused with a clear message.
- [ ] README + README_FR; `.po` translated.
