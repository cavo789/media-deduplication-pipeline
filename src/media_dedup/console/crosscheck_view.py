"""Print the verdict of a cross-check with Czkawka, and what it set aside."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from media_dedup.console.formatting import human_number
from media_dedup.crosscheck.compare import OutsideReason
from media_dedup.i18n import _, ngettext

if TYPE_CHECKING:
    from media_dedup.console.output import Output
    from media_dedup.crosscheck.compare import CrossCheckResult
    from media_dedup.crosscheck.czkawka import Group
    from media_dedup.paths.host_paths import HostPathMapper

_SHOWN_DIFFERENCES: Final = 10
_DATE_FORMAT: Final = "%Y-%m-%d %H:%M"


def show_cross_check(
    output: Output,
    result: CrossCheckResult,
    mapper: HostPathMapper,
) -> None:
    """Say whether Czkawka agrees, list the disagreements, explain the rest.

    Args:
        output: Where to print.
        result: The comparison.
        mapper: Host/container path translator.
    """
    if result.results_date is not None:
        output.info(
            _("Czkawka results of {date} UTC.").format(
                date=result.results_date.strftime(_DATE_FORMAT)
            )
        )
    if result.agrees:
        output.success(
            _(
                "Czkawka agrees: the same {copies} extra copies in {groups} groups."
            ).format(
                copies=human_number(result.copies),
                groups=human_number(len(result.ours)),
            )
        )
    else:
        count = len(result.only_ours) + len(result.only_theirs)
        output.warning(
            ngettext(
                "Czkawka disagrees on {count} group: look at it before cleaning.",
                "Czkawka disagrees on {count} groups: look at them before cleaning.",
                count,
            ).format(count=human_number(count))
        )
        for line in (
            *_differences(_("only media-dedup"), result.only_ours, mapper),
            *_differences(_("only Czkawka"), result.only_theirs, mapper),
        ):
            output.info(line)
    if result.outside:
        details = ", ".join(
            f"{_outside_label(reason)}: {human_number(count)}"
            for reason, count in sorted(result.outside.items())
        )
        output.info(
            _("Set aside, as media-dedup does not analyse them: {details}.").format(
                details=details
            )
        )


def _differences(
    label: str,
    groups: tuple[Group, ...],
    mapper: HostPathMapper,
) -> list[str]:
    """Describe the first groups only one tool found.

    Args:
        label: Which tool found them.
        groups: The groups.
        mapper: Host/container path translator.

    Returns:
        One line per group shown, then how many are hidden.
    """
    lines = [
        f"  • {label}: " + " = ".join(mapper.to_host(path) for path in sorted(group))
        for group in groups[:_SHOWN_DIFFERENCES]
    ]
    hidden = len(groups) - _SHOWN_DIFFERENCES
    if hidden > 0:
        lines.append(
            "  • " + _("… and {count} more.").format(count=human_number(hidden))
        )
    return lines


def _outside_label(reason: OutsideReason) -> str:
    """Translate why a file is out of media-dedup's scope.

    Args:
        reason: The reason.

    Returns:
        A short label.
    """
    labels = {
        OutsideReason.NOT_MOUNTED: _("outside the mounted folders"),
        OutsideReason.EXTENSION: _("other file types"),
        OutsideReason.EXCLUDED: _("in excluded folders"),
        OutsideReason.BROKEN: _("broken files"),
    }
    return labels[reason]
