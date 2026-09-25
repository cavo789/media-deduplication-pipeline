"""The report catalogue: `index.html`, listing, pruning."""

from __future__ import annotations

import logging
import shutil
from typing import TYPE_CHECKING

from pydantic import ValidationError

from media_dedup.constants import REPORT_INDEX_FILE_NAME, SUMMARY_FILE_NAME
from media_dedup.report.environment import make_environment
from media_dedup.report.summary import ReportSummary

if TYPE_CHECKING:
    from pathlib import Path

_LOGGER = logging.getLogger(__name__)
_INDEX_TEMPLATE = "index.html.j2"


def load_summaries(reports_dir: Path) -> list[ReportSummary]:
    """Read the summary of every report, newest first; unreadable ones are skipped.

    Args:
        reports_dir: Reports mount point.

    Returns:
        The summaries.
    """
    summaries: list[ReportSummary] = []
    for file in reports_dir.glob(f"*/{SUMMARY_FILE_NAME}"):
        try:
            summaries.append(ReportSummary.model_validate_json(file.read_text("utf-8")))
        except OSError, ValidationError:
            _LOGGER.warning("Skipping unreadable report summary %s", file)
    return sorted(summaries, key=lambda summary: summary.created_at, reverse=True)


def write_index(reports_dir: Path) -> Path:
    """(Re)generate `index.html`, the entry page listing every report.

    Args:
        reports_dir: Reports mount point.

    Returns:
        Path of the index page.
    """
    page = make_environment().get_template(_INDEX_TEMPLATE)
    target = reports_dir / REPORT_INDEX_FILE_NAME
    target.write_text(
        page.render(summaries=load_summaries(reports_dir)), encoding="utf-8"
    )
    return target


def prune_reports(reports_dir: Path, keep: int) -> list[str]:
    """Delete every report but the `keep` most recent ones, then refresh the index.

    Args:
        reports_dir: Reports mount point.
        keep: How many reports to keep.

    Returns:
        The folders deleted.
    """
    removed = [summary.folder for summary in load_summaries(reports_dir)[keep:]]
    for folder in removed:
        shutil.rmtree(reports_dir / folder)
    write_index(reports_dir)
    return removed
