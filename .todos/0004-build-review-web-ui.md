# 0004 — Build a keyboard-driven review UI for series

- **Priority**: Medium
- **Batch**: review-ui
- **Depends**: 0003
- **Files**: TBD

## Context

Thousands of photos make file-by-file review tedious. A local web page (served by the image:
`docker run -p 127.0.0.1::8080 … media-dedup review`) would show one series at a time, keyboard
driven (keep / discard / next), and write a decisions file that `clean --decisions` executes
with the usual journal and undo.

## Acceptance

- [ ] Decisions saved incrementally (resumable review).
- [ ] `clean --decisions` journals every action; `undo` restores them.
- [ ] Port published dynamically by Docker (`127.0.0.1::8080`), never a fixed host port.
