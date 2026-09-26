# 0022 — Keep the copy that has a sidecar (its edits)

- **Priority**: Medium
- **Batch**: keep-policy
- **Depends**: —
- **Files**: `src/media_dedup/plan/keeper.py`, `src/media_dedup/constants.py` (`KeepReason`), `src/media_dedup/services/policy.py`, `src/media_dedup/services/audit.py`, `src/media_dedup/report/reasons.py`

## Context

TODO 0007 (2026-09-26) moves orphan sidecars (`.xmp`, `.aae`, `.thm`) to the quarantine. The
demo tree shows the gap: `C:\Family Photos\2019\Vacances\IMG_0001.jpg` has an `IMG_0001.xmp`
next to it, but the keep policy keeps the identical `D:\backup\2019\IMG_0001.jpg` (shortest
path). The Vacances copy is deleted, its `.xmp` becomes an orphan and goes to the quarantine:
the kept photo loses its edits (reversible with `undo`, but silent).

The walk already knows, for each sidecar, the names of the files it belongs to
(`scan/sidecars.py`, `Sidecar.companions`), so the set of media paths that have a sidecar is
free to compute.

## Proposal

- A new keep criterion "has a sidecar" (`KeepReason.HAS_SIDECAR`), after `protected` and
  `preferred`, before `not-a-copy`: between identical copies, the one whose sidecar holds
  its edits wins.
- `KeepPolicy` receives the frozen set of paths accompanied by a sidecar (built in the audit
  from `Walk.sidecars`).
- The report's "why" label and README / README_FR (keep rules table) follow.

## Acceptance

- [ ] A copy with a sidecar is kept over an identical copy without one (unit test).
- [ ] On the demo tree, `Vacances/IMG_0001.xmp` is no longer an orphan.
- [ ] Both READMEs list the rule in "How it keeps your photos safe".

## Explicit NON-goals

- Moving or renaming a sidecar next to the kept copy (too magical; the user may have several
  different sidecars for different copies).
