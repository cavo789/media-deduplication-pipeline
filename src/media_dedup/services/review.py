"""`clean --decisions`: check a review against the audit, then apply it to the plan.

The decisions file is read before the audit (a wrong path fails at once) and checked
after it: made on the same folders, about pairs that still exist, and never asking to
delete the copies of a protected folder. Anything else refuses the whole file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.errors import DecisionsError
from media_dedup.i18n import _, ngettext
from media_dedup.paths.host_paths import is_within
from media_dedup.plan.pairs import folder_pairs
from media_dedup.plan.review import PairAction, PairChoice, apply_choices
from media_dedup.report.decisions import read_decisions
from media_dedup.services.policy import keep_policy

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.plan.models import AuditFindings, CleanPlan
    from media_dedup.plan.pairs import FolderPair
    from media_dedup.report.decisions import DecisionsFile
    from media_dedup.services.runtime import Runtime


def load_review(runtime: Runtime, source: Path) -> DecisionsFile:
    """Read a decisions file; a relative path is read from the reports folder.

    Args:
        runtime: Settings, mount points and output.
        source: `--decisions` value.

    Returns:
        The decisions.
    """
    reports_dir = runtime.locations.reports_dir
    return read_decisions(source if source.is_absolute() else reports_dir / source)


def review_choices(
    runtime: Runtime, findings: AuditFindings, review: DecisionsFile
) -> tuple[PairChoice, ...]:
    """Check that the decisions were made on this very audit, and translate them.

    Args:
        runtime: Settings, mount points and output.
        findings: The audit just run.
        review: The decisions file.

    Returns:
        The decisions, in container paths.

    Raises:
        DecisionsError: Other folders, a pair that no longer exists, or an
            impossible swap.
    """
    mapper = runtime.mapper
    ours = mapper.roots_on_host(findings.roots)
    if sorted(review.roots) != sorted(ours):
        raise DecisionsError(
            _(
                "These decisions were made on other folders ({theirs}); this run "
                "analyses {ours}."
            ).format(theirs=", ".join(review.roots), ours=", ".join(ours)),
            _("Mount the folders of that report, or decide again on a new report."),
        )
    pairs = {
        (mapper.to_host(pair.kept_in), mapper.to_host(pair.removed_from)): pair
        for pair in folder_pairs(findings.plan.decisions)
    }
    stale = [d for d in review.pairs if (d.kept_in, d.removed_from) not in pairs]
    if stale:
        message = ngettext(
            "{count} decided folder pair no longer exists, e.g. {kept} -> {removed}.",
            "{count} decided folder pairs no longer exist, e.g. {kept} -> {removed}.",
            len(stale),
        )
        raise DecisionsError(
            message.format(
                count=len(stale), kept=stale[0].kept_in, removed=stale[0].removed_from
            ),
            _("Files changed since the report: audit again and decide on it."),
        )
    choices = [(pairs[d.kept_in, d.removed_from], d.action) for d in review.pairs]
    for pair, action in choices:
        _check_swap(runtime, pair, action)
    return tuple(PairChoice(p.kept_in, p.removed_from, a) for p, a in choices)


def apply_review(
    runtime: Runtime, plan: CleanPlan, choices: tuple[PairChoice, ...]
) -> CleanPlan:
    """Apply checked decisions to the plan, and say what they change.

    Args:
        runtime: Settings, mount points and output.
        plan: The plan `clean` would execute.
        choices: The decisions, from `review_choices`.

    Returns:
        The plan, decisions applied.
    """
    swapped = sum(choice.action is PairAction.SWAP for choice in choices)
    runtime.output.info(
        _(
            "Your decisions — pairs swapped: {swapped}, pairs left alone: {skipped}."
        ).format(swapped=swapped, skipped=len(choices) - swapped)
    )
    return apply_choices(plan, choices, keep_policy(runtime.settings, runtime.mapper))


def _check_swap(runtime: Runtime, pair: FolderPair, action: PairAction) -> None:
    """Refuse a swap that would delete what must stay.

    Args:
        runtime: Settings, mount points and output.
        pair: The folder pair.
        action: What the review decided for it.

    Raises:
        DecisionsError: The pair is inside one folder, or its kept folder is protected.
    """
    if action is not PairAction.SWAP:
        return
    kept = runtime.mapper.to_host(pair.kept_in)
    if pair.kept_in == pair.removed_from:
        message = _("{folder}: copies inside one folder cannot be swapped.")
        raise DecisionsError(message.format(folder=kept))
    protected = keep_policy(runtime.settings, runtime.mapper).protected
    if any(is_within(pair.kept_in, folder) for folder in protected):
        message = _("{folder} is protected: its copies are always kept.")
        raise DecisionsError(message.format(folder=kept))
