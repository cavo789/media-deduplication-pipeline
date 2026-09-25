# 0005 — Identify similar videos (re-encoded copies)

- **Priority**: Low
- **Batch**: similarity
- **Depends**: 0001
- **Files**: `src/media_dedup/scan/video_check.py`, `Dockerfile`

## Context

Phone videos are often re-encoded when shared. Keyframe hashes (a few frames at fixed
percentages of the duration, dHash each) plus a duration tolerance would find them. Needs
`ffmpeg` (not only `ffprobe`) in the image — weigh it against the ffprobe slimming TODO.

## Acceptance

- [ ] Similar-video groups reported, never cleaned without an explicit tier flag.
- [ ] Image size impact measured with `dive`.
