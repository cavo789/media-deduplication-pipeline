# 0021 — Evaluate dropping numpy (70 MB of the image for three array operations)

- **Priority**: Low
- **Batch**: docker
- **Depends**: —
- **Files**: `src/media_dedup/scan/visual.py`, `pyproject.toml`, `uv.lock`, `tests/unit/test_visual.py`

## Context

TODOs 0001/0002 (2026-09-26) added numpy to compute the perceptual hashes and the sharpness
score. Measured in `media-dedup:latest`: `numpy` 43 MB + `numpy.libs` (OpenBLAS) 27 MB; the
image went from 336 MB (0.1.0) to 405 MB. `scan/visual.py` only needs:

- a `8 x 32` by `32 x 32` matrix product and a median (pHash);
- a comparison of neighbouring pixels (dHash);
- the variance of a 3 x 3 Laplacian on a thumbnail of at most 512 x 512 (sharpness).

Measured alternatives without numpy:

- pHash in pure Python with a precomputed `8 x 32` cosine table: about 1 ms per image.
- dHash on a `9 x 8` thumbnail: trivial in pure Python.
- Sharpness with Pillow only is the hard part: `ImageFilter.Kernel` works on mode `I`
  (with `offset` to avoid clipping negatives), but `ImageStat` computes the variance of an
  `I` image from a 256-bin histogram, which gave wrong results (variance rising with blur).
  Options: sum the pixels of the `I` image in Python (about 200 k values per image, roughly
  20 ms), or two `L`-mode passes (positive and negative Laplacian, `scale=4`) and
  `ImageStat.sum2`, which loses precision on blurry pictures.

## Proposal

Rewrite `scan/visual.py` without numpy if an option keeps the current results: the
`test_visual.py` cases (copies found near, bursts not, blurred shot at least 10x less sharp)
must pass unchanged. Otherwise keep numpy and say why in this TODO. Hashes are cached in the
index: changing the algorithm changes the values; bump the index schema so they are
recomputed.

## Acceptance

- [ ] Decision recorded; if implemented, the image loses about 70 MB (check with `dive`).
- [ ] Same test results; audit time per image not worse than 2x (measure on the demo tree).
