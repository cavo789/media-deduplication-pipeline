"""Folder pairs, the review unit of the report: samples, completeness, one page each."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from media_dedup.constants import PAIRS_DIR_NAME, Sizes
from media_dedup.report.thumbnails import PREVIEWABLE, thumbnail_name
from media_dedup.report.views import CopyView, FolderPairView, PairPageView

if TYPE_CHECKING:
    from collections.abc import Sequence

    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.pairs import FolderPair
    from media_dedup.scan.models import MediaFile


def pair_samples(pair: FolderPair) -> tuple[MediaFile, ...]:
    """Pick a few images of a pair to preview, the same ones on every run.

    Ordering by digest spreads the picks over the whole folder without randomness.

    Args:
        pair: The folder pair.

    Returns:
        Up to `Sizes.PAIR_SAMPLES` kept images.
    """
    images = sorted(
        (copy for copy in pair.copies if copy.kept.kind in PREVIEWABLE),
        key=lambda copy: copy.digest,
    )
    return tuple(copy.kept for copy in images[: Sizes.PAIR_SAMPLES])


def sampled_files(pairs: Sequence[FolderPair]) -> list[MediaFile]:
    """List the images previewed for the first pairs of the report.

    Args:
        pairs: Every folder pair, in report order.

    Returns:
        The images to render as thumbnails.
    """
    return [
        file for pair in pairs[: Sizes.MAX_SAMPLED_PAIRS] for file in pair_samples(pair)
    ]


def pair_page_name(index: int) -> str:
    """Return the relative path of a pair's page.

    Args:
        index: Position of the pair in the report, from 1.

    Returns:
        A path such as `pairs/pair-0001.html`.
    """
    return f"{PAIRS_DIR_NAME}/pair-{index:04d}.html"


@dataclass(frozen=True, slots=True)
class PairRenderer:
    """Turns folder pairs into views: host paths, and the previews actually written."""

    mapper: HostPathMapper
    previews: frozenset[str]
    is_clean: bool = False

    def summary(self, index: int, pair: FolderPair) -> FolderPairView:
        """Describe one pair for the report's pairs table.

        Args:
            index: Position of the pair in the report, from 1.
            pair: The folder pair.

        Returns:
            Its view.
        """
        samples = pair_samples(pair) if index <= Sizes.MAX_SAMPLED_PAIRS else ()
        return FolderPairView(
            kept_in=self.mapper.to_host(pair.kept_in),
            removed_from=self.mapper.to_host(pair.removed_from),
            files=pair.files,
            size=pair.size,
            complete=pair.complete,
            samples=tuple(
                name
                for name in (thumbnail_name(file) for file in samples)
                if name in self.previews
            ),
            page=pair_page_name(index),
        )

    def page(self, index: int, pair: FolderPair) -> PairPageView:
        """Describe every copy of one pair, sorted by the name of the deleted file.

        Args:
            index: Position of the pair in the report, from 1.
            pair: The folder pair.

        Returns:
            The page's view.
        """
        copies = sorted(pair.copies, key=lambda copy: copy.removed.path.name.casefold())
        return PairPageView(
            pair=self.summary(index, pair),
            copies=tuple(
                CopyView(
                    copy.kept.path.name, copy.removed.path.name, copy.size, copy.digest
                )
                for copy in copies
            ),
            is_clean=self.is_clean,
        )
