"""The whole plan as a spreadsheet: one row per file, readable by Excel in any language.

The HTML report caps the groups it lists; this file never does. Excel reads a CSV with
the list separator of the regional settings (`;` in French, `,` in English) and needs a
byte order mark to read accents: both follow the interface language.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

from media_dedup.constants import BrokenReason, Locale
from media_dedup.i18n import _, active_locale
from media_dedup.report.reasons import keep_reason_label

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from media_dedup.paths.host_paths import HostPathMapper
    from media_dedup.plan.models import CleanPlan
    from media_dedup.scan.models import BrokenFile, MediaFile

type Row = tuple[str | int, ...]

_SEPARATORS: Final = {Locale.FR: ";"}
_DEFAULT_SEPARATOR: Final = ","
_ENCODING: Final = "utf-8-sig"
_NANOSECONDS: Final = 1_000_000_000
_DATE_FORMAT: Final = "%Y-%m-%d %H:%M:%S"


def write_plan_csv(target: Path, plan: CleanPlan, mapper: HostPathMapper) -> None:
    """Write every file of the plan, group by group, then the broken files.

    Args:
        target: The CSV file to write.
        plan: The plan of the audit or clean.
        mapper: Host/container path translator.
    """
    rows = _Rows(mapper)
    separator = _SEPARATORS.get(active_locale(), _DEFAULT_SEPARATOR)
    with target.open("w", encoding=_ENCODING, newline="") as stream:
        writer = csv.writer(stream, delimiter=separator)
        writer.writerow(
            (
                _("Group"),
                _("SHA-256"),
                _("Size (bytes)"),
                _("Action"),
                _("File"),
                _("Folder"),
                _("Modified (UTC)"),
                _("Detail"),
            )
        )
        writer.writerows(rows.duplicates(plan))
        writer.writerows(rows.broken(plan))


@dataclass(frozen=True, slots=True)
class _Line:
    """What a row says about its file, beyond the file itself."""

    action: str
    group: str = ""
    digest: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class _Rows:
    """Builds the rows, in host paths."""

    mapper: HostPathMapper

    def duplicates(self, plan: CleanPlan) -> Iterator[Row]:
        """One row per file of every duplicate group, the kept copy first.

        Args:
            plan: The plan.

        Yields:
            The rows.
        """
        for number, decision in enumerate(plan.decisions, start=1):
            group, digest = str(number), decision.digest
            reason = keep_reason_label(decision.reason)
            keep = _Line(_("keep"), group, digest, reason)
            yield self._row(decision.keeper, keep)
            for file in decision.removable:
                yield self._row(file, _Line(_("delete"), group, digest))
            for file in decision.protected:
                yield self._row(file, _Line(_("protected, kept"), group, digest))

    def broken(self, plan: CleanPlan) -> Iterator[Row]:
        """One row per broken file, handled or left alone in a protected folder.

        Args:
            plan: The plan.

        Yields:
            The rows.
        """
        for item in plan.broken:
            empty = item.reason is BrokenReason.EMPTY
            action = _("delete") if empty else _("move to the quarantine")
            yield self._row(item.file, _Line(action, detail=_describe(item)))
        for item in plan.protected_broken:
            line = _Line(_("protected, kept"), detail=_describe(item))
            yield self._row(item.file, line)

    def _row(self, file: MediaFile, line: _Line) -> Row:
        modified = datetime.fromtimestamp(file.mtime_ns / _NANOSECONDS, UTC)
        return (
            line.group,
            line.digest,
            file.size,
            line.action,
            self.mapper.to_host(file.path),
            self.mapper.to_host(file.path.parent),
            modified.strftime(_DATE_FORMAT),
            line.detail,
        )


def _describe(item: BrokenFile) -> str:
    """Say why a file is broken, with the decoder's message when there is one.

    Args:
        item: The broken file.

    Returns:
        The translated reason.
    """
    reasons = {
        BrokenReason.EMPTY: _("Empty file (0 bytes)"),
        BrokenReason.UNREADABLE_IMAGE: _("Image cannot be decoded"),
        BrokenReason.UNREADABLE_VIDEO: _("Video cannot be opened"),
    }
    reason = reasons[item.reason]
    return f"{reason} — {item.detail}" if item.detail else reason
