"""Review decisions on folder pairs: swap keeps the other folder, skip keeps both."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from media_dedup.constants import KeepReason, MediaKind
from media_dedup.errors import DecisionsError
from media_dedup.plan.keeper import KeepPolicy
from media_dedup.plan.models import CleanPlan, KeepDecision
from media_dedup.plan.review import PairAction, PairChoice, apply_choices
from media_dedup.report.decisions import read_decisions
from media_dedup.scan.models import MediaFile

if TYPE_CHECKING:
    from collections.abc import Sequence

DATA = Path("/data")
A, B, C = DATA / "c/A", DATA / "c/B", DATA / "c/C"
POLICY = KeepPolicy()


def at(folder: Path, name: str = "IMG.jpg") -> MediaFile:
    """A 10-byte image in `folder`."""
    return MediaFile(folder / name, 10, 0, MediaKind.IMAGE)


def group(keeper: MediaFile, *removable: MediaFile) -> CleanPlan:
    """A plan of one group."""
    return CleanPlan((KeepDecision("digest", 10, keeper, removable),), ())


def reviewed(plan: CleanPlan, choices: Sequence[PairChoice]) -> KeepDecision:
    """Apply the choices and return the only group left."""
    [decision] = apply_choices(plan, choices, POLICY).decisions
    return decision


def test_swap_keeps_the_other_folder() -> None:
    """The copy of the second folder becomes the keeper; the old keeper goes."""
    decision = reviewed(group(at(A), at(B)), [PairChoice(A, B, PairAction.SWAP)])
    assert decision.keeper == at(B)
    assert decision.removable == (at(A),)
    assert decision.reason is KeepReason.REVIEWED


def test_skip_spares_the_pair_and_drops_empty_groups() -> None:
    """A skipped pair deletes nothing; a group with nothing left leaves the plan."""
    plan = group(at(A), at(B), at(C))
    decision = reviewed(plan, [PairChoice(A, B, PairAction.SKIP)])
    assert decision.keeper == at(A)
    assert decision.removable == (at(C),)
    assert decision.spared == (at(B),)
    both = [PairChoice(A, B, PairAction.SKIP), PairChoice(A, C, PairAction.SKIP)]
    assert not apply_choices(plan, both, POLICY).decisions


def test_every_copy_a_decision_keeps_stays() -> None:
    """Swap A/B and skip A/C: B keeps, C stays, only A's copy goes."""
    choices = [PairChoice(A, B, PairAction.SWAP), PairChoice(A, C, PairAction.SKIP)]
    decision = reviewed(group(at(A), at(B), at(C)), choices)
    assert decision.keeper == at(B)
    assert decision.removable == (at(A),)
    assert decision.spared == (at(C),)


def test_swap_keeps_the_best_copy_of_the_folder() -> None:
    """Two copies in the swapped folder: the policy picks the keeper, both stay."""
    copies = (at(B, "IMG (1).jpg"), at(B))
    decision = reviewed(group(at(A), *copies), [PairChoice(A, B, PairAction.SWAP)])
    assert decision.keeper == at(B)
    assert decision.spared == (at(B, "IMG (1).jpg"),)


def test_undecided_groups_are_untouched() -> None:
    """Choices on other pairs change nothing."""
    plan = group(at(A), at(B))
    assert apply_choices(plan, [PairChoice(C, B, PairAction.SWAP)], POLICY) == plan


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (None, "Cannot read"),
        ("not json", "not a valid decisions file"),
        ('{"version": 2, "roots": []}', "not a valid decisions file"),
        (
            (
                '{"version": 1, "roots": [], "pairs": ['
                '{"kept_in": "C:\\\\A", "removed_from": "C:\\\\B", "action": "swap"},'
                '{"kept_in": "C:\\\\A", "removed_from": "C:\\\\B", "action": "skip"}]}'
            ),
            "decided twice",
        ),
    ],
)
def test_invalid_files_are_refused(
    tmp_path: Path, content: str | None, error: str
) -> None:
    """Missing, garbage, another version, a pair decided twice: refused."""
    path = tmp_path / "decisions.json"
    if content is not None:
        path.write_text(content)
    with pytest.raises(DecisionsError, match=error):
        read_decisions(path)
