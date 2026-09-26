"""`clean --decisions`: check the burst shots a review set aside against the audit.

Every reviewed series must still be one series of the audit, and no shot set aside may
lie in a protected folder. Anything else refuses the whole file, like a stale pair.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.errors import DecisionsError
from media_dedup.i18n import _, ngettext
from media_dedup.plan.similar_models import BurstChoice
from media_dedup.review.shots import match_burst, shot_places
from media_dedup.services.policy import keep_policy

if TYPE_CHECKING:
    from media_dedup.plan.models import AuditFindings
    from media_dedup.plan.similar_models import BurstSeries
    from media_dedup.report.decisions import BurstDecision
    from media_dedup.review.shots import MatchedBurst
    from media_dedup.services.runtime import Runtime


def burst_choices(
    runtime: Runtime, findings: AuditFindings, bursts: tuple[BurstDecision, ...]
) -> tuple[BurstChoice, ...]:
    """Translate the reviewed burst series into shots of this audit.

    Args:
        runtime: Settings, mount points and output.
        findings: The audit just run.
        bursts: The reviews of burst series, from the decisions file.

    Returns:
        The shots kept and set aside, in container paths.

    Raises:
        DecisionsError: A series changed since the review, or a shot set aside lies
            in a protected folder.
    """
    series = findings.similar.bursts
    places = shot_places(series, runtime.mapper)
    matched = [(decision, match_burst(decision, places)) for decision in bursts]
    stale = [decision for decision, match in matched if match is None]
    if stale:
        message = ngettext(
            "{count} reviewed burst series no longer matches the audit, e.g. {path}.",
            "{count} reviewed burst series no longer match the audit, e.g. {path}.",
            len(stale),
        )
        raise DecisionsError(
            message.format(count=len(stale), path=stale[0].discarded[0]),
            _("Files changed since the review: run 'review' again."),
        )
    choices = tuple(_choice(series, match) for _decision, match in matched if match)
    policy = keep_policy(runtime.settings, runtime.mapper)
    for choice in choices:
        locked = [file for file in choice.discarded if policy.is_protected(file)]
        if locked:
            message = _("{path} is in a protected folder: it is never moved.")
            raise DecisionsError(
                message.format(path=runtime.mapper.to_host(locked[0].path))
            )
    return choices


def _choice(series: tuple[BurstSeries, ...], match: MatchedBurst) -> BurstChoice:
    """Turn ranks in a series into its shots.

    Args:
        series: The burst series of the audit.
        match: The review, as ranks in one of them.

    Returns:
        The shots kept and set aside.
    """
    shots = series[match.series].shots
    return BurstChoice(
        kept=tuple(shots[rank] for rank in sorted(match.kept)),
        discarded=tuple(shots[rank] for rank in sorted(match.discarded)),
    )
