"""Near-duplicate groups and burst series, from visual facts alone."""

from __future__ import annotations

from pathlib import Path

from media_dedup.constants import MediaKind
from media_dedup.plan.bursts import burst_series, moment_of
from media_dedup.plan.keeper import KeepPolicy
from media_dedup.plan.near import near_decisions
from media_dedup.scan.models import MediaFile, VisualFacts

DATA = Path("/data/c")
HASH = 0x0F0F_3C3C_5A5A_6969


def image(name: str, size: int = 100) -> MediaFile:
    """An image below /data/c."""
    return MediaFile(DATA / name, size, 0, MediaKind.IMAGE)


def looks(width: int = 400, /, **changes: object) -> VisualFacts:
    """Visual facts of the reference scene, with some fields changed."""
    fields: dict[str, object] = {
        "dhash": HASH,
        "phash": HASH,
        "width": width,
        "height": width * 3 // 4,
        "sharpness": 100.0,
    }
    fields.update(changes)
    return VisualFacts(**fields)  # type: ignore[arg-type]


def names(files: tuple[MediaFile, ...]) -> list[str]:
    """File names, for readable assertions."""
    return [file.path.name for file in files]


def test_the_highest_resolution_is_kept() -> None:
    """Smaller and one-bit-different copies go; the largest picture stays."""
    files = [image("small.jpg"), image("big.jpg"), image("other.jpg")]
    visuals = {
        DATA / "small.jpg": looks(200, dhash=HASH ^ 1),
        DATA / "big.jpg": looks(800),
        DATA / "other.jpg": looks(dhash=~HASH & (2**64 - 1)),
    }
    (decision,) = near_decisions(files, visuals, KeepPolicy())
    assert decision.keeper.path.name == "big.jpg"
    assert names(decision.removable) == ["small.jpg"]


def test_protected_copies_stay_and_dates_must_match() -> None:
    """A protected copy is listed but kept; a copy shot at another moment is no copy."""
    files = [image("big.jpg"), image("master/small.jpg"), image("later.jpg")]
    visuals = {
        DATA / "big.jpg": looks(800, taken_at="2020:01:01 10:00:00"),
        DATA / "master/small.jpg": looks(200),
        DATA / "later.jpg": looks(400, taken_at="2020:01:01 10:00:05"),
    }
    policy = KeepPolicy(protected=(DATA / "master",))
    assert not near_decisions(files, visuals, policy)
    files.append(image("copy.jpg"))
    visuals[DATA / "copy.jpg"] = looks(300)
    (decision,) = near_decisions(files, visuals, policy)
    assert names(decision.removable) == ["copy.jpg"]
    assert names(decision.protected) == ["small.jpg"]


def test_featureless_pictures_and_other_shapes_are_left_alone() -> None:
    """Blank pictures all hash alike; a crop has another aspect ratio."""
    blank = looks(dhash=0, phash=0)
    files = [
        image("black1.jpg"),
        image("black2.jpg"),
        image("big.jpg"),
        image("crop.jpg"),
    ]
    visuals = {
        DATA / "black1.jpg": blank,
        DATA / "black2.jpg": looks(200, dhash=0, phash=0),
        DATA / "big.jpg": looks(800),
        DATA / "crop.jpg": looks(400, height=400),
    }
    assert not near_decisions(files, visuals, KeepPolicy())


def shot(name: str, taken_at: str, **changes: object) -> tuple[MediaFile, VisualFacts]:
    """A camera shot at `taken_at`."""
    return image(name), looks(taken_at=taken_at, camera="Canon EOS 80D", **changes)


def test_a_burst_links_shots_seconds_apart_and_suggests_the_sharpest() -> None:
    """Same camera, same scene, seconds apart; the same second is linked too."""
    shots = [
        shot("a.jpg", "2021:07:04 10:15:00"),
        shot("b.jpg", "2021:07:04 10:15:00", sharpness=300.0, phash=HASH ^ 0xFF),
        shot("c.jpg", "2021:07:04 10:15:01", sharpness=2.0),
        shot("far.jpg", "2021:07:04 10:16:00"),
        shot("other.jpg", "2021:07:04 10:15:02", phash=~HASH & (2**64 - 1)),
    ]
    other_camera = (
        image("phone.jpg"),
        looks(taken_at="2021:07:04 10:15:01", camera="Apple iPhone"),
    )
    files = [file for file, _visual in (*shots, other_camera)]
    visuals = {file.path: visual for file, visual in (*shots, other_camera)}
    (series,) = burst_series(files, visuals)
    assert names(series.shots) == ["a.jpg", "b.jpg", "c.jpg"]
    assert series.best.path.name == "b.jpg"


def test_exif_moments() -> None:
    """Sub-seconds count; a missing or impossible date is no moment."""
    first = moment_of("2021:07:04 10:15:00.25")
    second = moment_of("2021:07:04 10:15:01")
    assert first is not None
    assert second is not None
    assert second - first == 0.75
    assert moment_of(None) is None
    assert moment_of("2021:02:30 10:00:00") is None
    assert moment_of("unknown") is None
