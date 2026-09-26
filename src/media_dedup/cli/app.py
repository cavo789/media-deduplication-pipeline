"""Assemble the Typer app — after the locale is installed, so help is translated."""

from __future__ import annotations

import typer

from media_dedup.cli.cmd_audit import audit_command
from media_dedup.cli.cmd_clean import clean_command
from media_dedup.cli.cmd_config import config_command
from media_dedup.cli.cmd_crosscheck import crosscheck_command
from media_dedup.cli.cmd_history import history_command
from media_dedup.cli.cmd_purge import purge_command
from media_dedup.cli.cmd_reports import reports_command
from media_dedup.cli.cmd_review import review_command
from media_dedup.cli.cmd_undo import undo_command
from media_dedup.cli.localized import LocalizedCommand, LocalizedGroup
from media_dedup.cli.root import root_callback
from media_dedup.constants import APP_NAME
from media_dedup.i18n import _

# One short command per line, so a copy/paste stays a single command.
# "\b" tells Click not to re-wrap the block.
_WINDOWS_FOLDER = (
    'docker run --rm -it -v "C:\\Photos:/data/c/Photos:ro" media-dedup audit'
)
_CURRENT_FOLDER = 'docker run --rm -it -v "${PWD}:/data/current:ro" media-dedup audit'


def _epilog() -> str:
    """Translated examples block shown at the end of `--help`, each one labelled.

    Returns:
        The epilog text.
    """
    return "\n\n".join(
        (
            "\n".join(
                (
                    "\b",
                    _("A Windows folder (PowerShell):"),
                    f"  {_WINDOWS_FOLDER}",
                    _("The current folder (PowerShell, or bash on WSL, Linux, macOS):"),
                    f"  {_CURRENT_FOLDER}",
                ),
            ),
            _("Full commands (reports, journal, WSL): see README.md."),
        ),
    )


def build_app() -> typer.Typer:
    """Create the CLI with every command and its translated help.

    Returns:
        The Typer application.
    """
    app = typer.Typer(
        name=APP_NAME,
        cls=LocalizedGroup,
        help=_(
            "Find and safely clean duplicate photos and videos across folders and "
            "disks. Start with 'audit' (read-only), then 'clean'."
        ),
        epilog=_epilog(),
        subcommand_metavar=_("COMMAND [ARGS]..."),
        rich_markup_mode="rich",
        no_args_is_help=True,
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.callback()(root_callback)
    analyse, act = _("Analyse"), _("Act")
    commands = (
        (
            "audit",
            audit_command,
            analyse,
            _(
                "Find exact duplicates and broken files. "
                "Read-only: mount folders with :ro."
            ),
        ),
        (
            "crosscheck",
            crosscheck_command,
            analyse,
            _(
                "Compare a fresh audit with Czkawka's results: a second, "
                "independent opinion."
            ),
        ),
        (
            "review",
            review_command,
            act,
            _(
                "Set burst shots aside, one series at a time, with the keyboard in "
                "your browser; 'clean --decisions' then moves them."
            ),
        ),
        (
            "clean",
            clean_command,
            act,
            _(
                "Audit, confirm, then really delete duplicate "
                "copies (journaled, undoable)."
            ),
        ),
        (
            "undo",
            undo_command,
            act,
            _(
                "Restore every file of a clean run, from the "
                "kept copy or the quarantine."
            ),
        ),
        (
            "purge",
            purge_command,
            act,
            _("Permanently delete the quarantined broken files of a run."),
        ),
        (
            "history",
            history_command,
            analyse,
            _("List the clean runs and what they did."),
        ),
        (
            "reports",
            reports_command,
            analyse,
            _("List the HTML reports of previous audits and cleans."),
        ),
        (
            "config",
            config_command,
            analyse,
            _("Show every setting, where it comes from, and the mount points."),
        ),
    )
    for name, function, panel, help_text in commands:
        app.command(
            name=name,
            cls=LocalizedCommand,
            help=help_text,
            rich_help_panel=panel,
        )(function)
    return app
