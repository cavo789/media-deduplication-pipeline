# 0010 — Replace the static ffprobe (141 MB) with a demux-only build

- **Priority**: Medium
- **Batch**: docker
- **Depends**: —
- **Files**: `Dockerfile`

## Context

`dive` (docker-image-slimming, bucket B — decide together): the static `ffprobe` from
`mwader/static-ffmpeg` is 141 MB, 42 % of the 336 MB image, while the tool only asks it whether a
video *container* opens. Measured on 2026-09-25: base ≈ 120 MB, ffprobe 141 MB, venv 75 MB.

Options:

1. Compile ffprobe in a discarded builder stage with `--disable-everything` plus the needed
   demuxers (mov/mp4, matroska, avi, mpegts, asf, flv) and the file protocol: likely a few MB.
2. `pymediainfo` (bundled libmediainfo, ~10 MB): container parsing without ffmpeg.
3. Keep as is: simplest, largest.

## Acceptance

- [ ] Option chosen with the user.
- [ ] Broken-video tests (truncated MP4) still pass; `e2e` passes.
- [ ] Size before/after reported from `dive`.
