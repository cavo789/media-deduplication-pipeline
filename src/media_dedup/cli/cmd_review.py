"""`media-dedup review`: set burst shots aside, one series at a time, in the browser."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Final

import typer

from media_dedup.cli import options, review_options
from media_dedup.cli.context import folder_layer, runtime_of, user_errors
from media_dedup.cli.flows import audit_and_show
from media_dedup.console.formatting import human_number
from media_dedup.i18n import _, ngettext
from media_dedup.services.reviewing import open_review, review_target, serve_review

REVIEW_PORT: Final = 8080
_DECISIONS_FILE: Final = Path("decisions.json")


# The options are parameters: the documented exception for Typer commands.
def review_command(  # pylint: disable=too-many-arguments
    ctx: typer.Context,
    *,
    prefer: Annotated[list[str] | None, options.prefer()] = None,
    protect: Annotated[list[str] | None, options.protect()] = None,
    exclude: Annotated[list[str] | None, options.exclude()] = None,
    decisions: Annotated[Path, review_options.decisions_file()] = _DECISIONS_FILE,
    port: Annotated[int, review_options.port()] = REVIEW_PORT,
) -> None:
    """Audit, then serve the burst series in the browser until Ctrl+C.

    Args:
        ctx: Typer context holding the runtime.
        prefer: `--prefer` folders.
        protect: `--protect` folders.
        exclude: `--exclude` folders.
        decisions: `--decisions`, the file to save the decisions in.
        port: `--port`, inside the container.
    """
    runtime = runtime_of(ctx)
    output = runtime.output
    with user_errors(output):
        runtime = runtime.with_overrides(folder_layer(prefer, protect, exclude))
        target = review_target(runtime, decisions)
        findings = audit_and_show(runtime)
        if not findings.similar.bursts:
            output.success(_("No burst series: nothing to review."))
            return
        session = open_review(runtime, findings, target)
        if session.dropped:
            dropped = ngettext(
                "{count} series reviewed earlier changed since: reviewed again.",
                "{count} series reviewed earlier changed since: reviewed again.",
                session.dropped,
            )
            output.warning(dropped.format(count=human_number(session.dropped)))
        serve_review(runtime, session, port)
        series, shots = session.progress
        output.blank()
        output.success(
            _(
                "Review stopped — series with shots set aside: {series}, shots set "
                "aside: {shots}."
            ).format(series=human_number(series), shots=human_number(shots))
        )
        if shots:
            output.tip(
                _(
                    "Next: the same 'clean' command with --decisions {file}; the shots "
                    "set aside go to the quarantine, 'undo' brings them back."
                ).format(file=decisions)
            )
