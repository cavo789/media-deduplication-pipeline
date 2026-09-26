"""Keep the copy whose name or folder someone chose, and say why each keeper won."""

from __future__ import annotations

from pathlib import Path

import pytest

from media_dedup.constants import KeepReason, MediaKind
from media_dedup.plan.copy_names import without_copy_marks
from media_dedup.plan.keeper import KeepPolicy
from media_dedup.plan.name_rules import DEFAULT_NAME_RULES, NameRules
from media_dedup.scan.models import DuplicateGroup, MediaFile

DATA = Path("/data")


def file_at(relative: str, mtime_ns: int = 0) -> MediaFile:
    """A 10-byte image at `/data/<relative>`."""
    return MediaFile(DATA / relative, 10, mtime_ns, MediaKind.IMAGE)


def decide(policy: KeepPolicy, *files: MediaFile) -> tuple[str, KeepReason | None]:
    """The kept path, relative to /data, and why it won."""
    decision = policy.decide(DuplicateGroup("digest", 10, files))
    return str(decision.keeper.path.relative_to(DATA)), decision.reason


def test_a_chosen_name_beats_an_older_generated_one() -> None:
    """Marie et Paul.jpg is kept although IMG_1234.jpg is older and shorter."""
    kept = decide(
        KeepPolicy(),
        file_at("c/DCIM/IMG_1234.jpg", mtime_ns=1),
        file_at("c/Mariage 2015/Marie et Paul.jpg", mtime_ns=9),
    )
    assert kept == ("c/Mariage 2015/Marie et Paul.jpg", KeepReason.MEANINGFUL_NAME)


def test_a_named_folder_beats_a_generic_one() -> None:
    r"""Same generated name: the copy in an album beats the one in DCIM\100CANON."""
    kept = decide(
        KeepPolicy(),
        file_at("c/DCIM/100CANON/IMG_0001.jpg", mtime_ns=1),
        file_at("c/Vacances 2019/IMG_0001.jpg", mtime_ns=9),
    )
    assert kept == ("c/Vacances 2019/IMG_0001.jpg", KeepReason.MEANINGFUL_FOLDER)


def test_higher_criteria_still_win() -> None:
    """Preferred folders and copy names come before the name rule."""
    preferred = KeepPolicy(preferred=(DATA / "c/DCIM",))
    assert decide(
        preferred, file_at("c/DCIM/IMG_1.jpg"), file_at("c/Album/Marie.jpg")
    ) == ("c/DCIM/IMG_1.jpg", KeepReason.PREFERRED)
    assert decide(
        KeepPolicy(), file_at("c/a/Marie (1).jpg"), file_at("c/a/IMG_1.jpg")
    ) == ("c/a/IMG_1.jpg", KeepReason.NOT_A_COPY)


def test_every_later_criterion_is_named() -> None:
    """Oldest date, shortest path, then alphabetical order."""
    policy = KeepPolicy()
    assert decide(policy, file_at("c/a/x.jpg", 5), file_at("c/b/x.jpg", 1))[1] == (
        KeepReason.OLDEST
    )
    assert decide(policy, file_at("c/a/b/x.jpg"), file_at("c/a/x.jpg"))[1] == (
        KeepReason.SHORTEST_PATH
    )
    assert decide(policy, file_at("c/b/x.jpg"), file_at("c/a/x.jpg"))[1] == (
        KeepReason.ALPHABETICAL
    )


def test_protected_copy_is_the_reason() -> None:
    """A protected folder decides before anything else."""
    policy = KeepPolicy(protected=(DATA / "d/master",))
    assert decide(policy, file_at("c/Marie.jpg"), file_at("d/master/IMG_1.jpg"))[1] == (
        KeepReason.PROTECTED
    )


def test_empty_rules_disable_the_criterion() -> None:
    """Without patterns, the older generated name wins again."""
    policy = KeepPolicy(names=NameRules.from_patterns((), ()))
    kept = decide(
        policy, file_at("c/DCIM/IMG_1234.jpg", 1), file_at("c/Album/Marie.jpg", 9)
    )
    assert kept == ("c/DCIM/IMG_1234.jpg", KeepReason.OLDEST)


@pytest.mark.parametrize(
    "name",
    [
        "IMG_1234.jpg",
        "IMG_1234 (1).jpg",
        "Copie de DSC_0001.JPG",
        "IMG-20190612-WA0001.jpg",
        "PXL_20210612_143012345.MP.jpg",
        "20190612_143012.jpg",
        "Screenshot_20210101-101010.png",
    ],
)
def test_generated_names(name: str) -> None:
    """Camera and app names are recognised, copy marks included."""
    assert DEFAULT_NAME_RULES.has_generated_name(DATA / "c" / name)


@pytest.mark.parametrize("name", ["Marie et Paul.jpg", "IMG_1234 - Paul.jpg"])
def test_chosen_names(name: str) -> None:
    """A name someone typed is never taken for a generated one."""
    assert not DEFAULT_NAME_RULES.has_generated_name(DATA / "c" / name)


def test_copy_marks_are_removed() -> None:
    """Every copy mark goes: brackets, "- Copie", "Copy of"."""
    assert without_copy_marks("Copy of IMG_0001 (2)") == "IMG_0001"
    assert without_copy_marks("Vacances - Copie") == "Vacances"
