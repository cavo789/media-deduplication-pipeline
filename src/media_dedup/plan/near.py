"""Near duplicates: one picture saved again at another size, quality or without EXIF.

Two images are near duplicates only when every test agrees: both 64-bit hashes differ
by at most `NEAR_DISTANCE` bits, the aspect ratio is the same (±1 %), and the smaller
one was shot at the same moment or has lost its date. A burst (another moment) never
qualifies.
Featureless images (black, white, blank) are left out: they all hash alike.

Candidates meet through multi-index hashing: two hashes at most 3 bits apart share at
least one of their four 16-bit quarters, so only images sharing a quarter are compared.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import TYPE_CHECKING, Final

from media_dedup.plan.similar_models import NearDecision
from media_dedup.plan.union_find import UnionFind

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from media_dedup.plan.keeper import KeepPolicy
    from media_dedup.scan.models import MediaFile, VisualFacts

NEAR_DISTANCE: Final = 2
_ASPECT_TOLERANCE: Final = 0.01
_HASH_BITS: Final = 64
_QUARTER_BITS: Final = 16
_QUARTER_MASK: Final = (1 << _QUARTER_BITS) - 1
_FEATURELESS_BITS: Final = 2


def distance(first: int, second: int) -> int:
    """Count the bits two hashes differ by.

    Args:
        first: A hash.
        second: Another hash.

    Returns:
        The Hamming distance.
    """
    return (first ^ second).bit_count()


def is_featureless(visual: VisualFacts) -> bool:
    """Tell whether an image has almost no detail (its gradient hash is nearly flat).

    Args:
        visual: What the image looks like.

    Returns:
        True for black, white or blank pictures.
    """
    bits = visual.dhash.bit_count()
    return bits <= _FEATURELESS_BITS or bits >= _HASH_BITS - _FEATURELESS_BITS


def is_near(best: VisualFacts, other: VisualFacts) -> bool:
    """Tell whether `other` is a smaller or recompressed version of `best`.

    Args:
        best: The larger version.
        other: The candidate copy.

    Returns:
        True when every test agrees.
    """
    return (
        distance(best.dhash, other.dhash) <= NEAR_DISTANCE
        and distance(best.phash, other.phash) <= NEAR_DISTANCE
        and abs(best.width * other.height - other.width * best.height)
        <= _ASPECT_TOLERANCE * best.width * other.height
        and (other.taken_at is None or other.taken_at == best.taken_at)
    )


def near_decisions(
    files: Sequence[MediaFile],
    visuals: Mapping[Path, VisualFacts],
    policy: KeepPolicy,
) -> tuple[NearDecision, ...]:
    """Group near duplicates and choose the version to keep in each group.

    The highest resolution is kept, then the largest file, then the usual keep rules.
    Only copies near the kept version are listed; protected copies are never removable.

    Args:
        files: Candidate images, one per exact-duplicate group.
        visuals: What each image looks like.
        policy: Protected folders and the usual keep rules.

    Returns:
        The decisions, the largest keeper first.
    """
    usable = [
        file
        for file in files
        if file.path in visuals and not is_featureless(visuals[file.path])
    ]
    decisions: list[NearDecision] = []
    for cluster in _clusters(usable, visuals):
        keeper = min(
            cluster,
            key=lambda file: (
                -visuals[file.path].pixels,
                -file.size,
                policy.rank(file),
            ),
        )
        near = [
            file
            for file in cluster
            if file != keeper and is_near(visuals[keeper.path], visuals[file.path])
        ]
        removable = tuple(file for file in near if not policy.is_protected(file))
        if removable:
            decisions.append(
                NearDecision(
                    keeper,
                    removable,
                    tuple(file for file in near if policy.is_protected(file)),
                )
            )
    return tuple(sorted(decisions, key=lambda d: (-d.keeper.size, str(d.keeper.path))))


def _clusters(
    files: Sequence[MediaFile], visuals: Mapping[Path, VisualFacts]
) -> Iterable[list[MediaFile]]:
    """Link images whose hashes are close, and return the linked sets.

    Args:
        files: Candidate images.
        visuals: What each image looks like.

    Returns:
        The sets of two images or more.
    """
    links = UnionFind(files)
    for members in _quarter_buckets(files, visuals):
        for first, second in combinations(members, 2):
            if _close(visuals[files[first].path], visuals[files[second].path]):
                links.link(first, second)
    return links.sets()


def _quarter_buckets(
    files: Sequence[MediaFile], visuals: Mapping[Path, VisualFacts]
) -> Iterable[list[int]]:
    """Bucket images by each 16-bit quarter of their perceptual hash.

    Args:
        files: Candidate images.
        visuals: What each image looks like.

    Returns:
        The positions of the images sharing a quarter, bucket by bucket.
    """
    buckets: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for index, file in enumerate(files):
        phash = visuals[file.path].phash
        for quarter in range(_HASH_BITS // _QUARTER_BITS):
            key = (quarter, (phash >> (quarter * _QUARTER_BITS)) & _QUARTER_MASK)
            buckets[key].append(index)
    return (members for members in buckets.values() if len(members) > 1)


def _close(first: VisualFacts, second: VisualFacts) -> bool:
    """Tell whether two images may be near duplicates (the hashes alone).

    Args:
        first: An image.
        second: Another image.

    Returns:
        True when both hashes are within `NEAR_DISTANCE`.
    """
    return (
        distance(first.phash, second.phash) <= NEAR_DISTANCE
        and distance(first.dhash, second.dhash) <= NEAR_DISTANCE
    )
