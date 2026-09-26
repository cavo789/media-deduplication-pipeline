# 0013 — Offer a second opinion: cross-check the audit with Czkawka

- **Priority**: High — an independent implementation caught a real data-loss bug
- **Batch**: cross-check
- **Depends**: —
- **Files**: `src/media_dedup/cli/` (new `cmd_crosscheck.py`), `src/media_dedup/services/` (new cross-check service), `src/media_dedup/services/audit.py` (tip), `src/media_dedup/report/`, `README.md`, `README_FR.md`

## Context

Users hesitate before deleting 12,633 family photos. A second, independent tool agreeing on the
same duplicates is the strongest reassurance. It is also a real safety net: on 2026-09-26, with
`C:\Windows\Web` mounted twice, Czkawka found 2 duplicates in 2 groups while media-dedup
(before the overlapping-mount fix) claimed 28.

Facts checked on 2026-09-26:

- `jlesage/czkawka` (485 MB, a web GUI image) ships `/usr/bin/czkawka_cli` 12.0.2. The image has
  no `ENTRYPOINT` (`CMD /init`), so
  `docker run --rm -v "C:\Photos:/data/c/Photos:ro" -v "…:/out" jlesage/czkawka czkawka_cli dup -d /data …`
  runs the CLI directly. There is no official CLI-only image.
- Defaults that differ from ours: `-m 8192` minimal size (use `-m 1`); every extension (use
  `-x` with our list; its `IMAGE`/`VIDEO` macros differ from ours); non-zero exit code when
  duplicates are found (`-W` disables it). Hard links are counted once, like ours now.
- Output: `-C file.json` (compact JSON), `-p` (pretty JSON), `-f` (text). "Found N duplicated
  files in G groups" counts extra copies, like our "Extra copies that can be deleted".

## Proposal

Our container cannot and must not start another one (no Docker socket). So:

1. After `audit`, a 💡 tip prints the exact, ready-to-paste Czkawka command (PowerShell and
   WSL). It uses the **same `-v` targets** (Czkawka reports container paths), `-m 1`,
   `-x <our extensions>`, `-e` for excluded folders, and `-C /reports/<run>/czkawka.json`.
2. `media-dedup crosscheck [run]` reads that JSON and compares the groups in both directions.
   Output is either "Czkawka agrees on 12,633 / 12,633 copies (G groups)" or the differences,
   with their likely cause (size threshold, extension, excluded folder, broken files that we
   keep out of groups).
3. The verdict is stored in `summary.json` and shown in the report. `clean` shows
   "cross-checked ✅ / not cross-checked" before confirming, as information and never a
   requirement.

Check the exact JSON schema of `czkawka_cli` 12 during implementation, and pin the image tag in
the tip.

## Acceptance

- [ ] The audit tip gives a working command (tested in e2e with `jlesage/czkawka`, marker `e2e`).
- [ ] `crosscheck` reports agreement or lists differences both ways, with reasons.
- [ ] README + README_FR: section "Get a second opinion"; `.po` translated.
