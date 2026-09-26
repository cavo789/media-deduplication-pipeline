# 0011 — Translate the few built-in CLI strings (Usage, Options, --help)

- **Priority**: Low
- **Batch**: i18n
- **Depends**: —
- **Files**: `src/media_dedup/cli/app.py`

## Context

With `--locale fr`, every string of the tool is French, but a few come from Typer/Click itself:
"Usage:", the "Options" panel title and "Show this message and exit.". They use Click's own
gettext domain, not ours.

## Acceptance

- [ ] `media-dedup --locale fr --help` fully French, without monkeypatching private APIs if possible.
