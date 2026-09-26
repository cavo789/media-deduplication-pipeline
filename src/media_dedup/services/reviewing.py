"""`media-dedup review`: open the review of the burst series and serve it until Ctrl+C.

The server listens on every interface of the container: Docker publishes the port on
the host's loopback only (`-p 127.0.0.1::8080`), on a port it chooses.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
from functools import partial
from typing import TYPE_CHECKING, Final

from media_dedup.errors import DecisionsError, MountError
from media_dedup.i18n import _
from media_dedup.i18n.templates import translated_environment
from media_dedup.paths.mount_kind import MountKind
from media_dedup.report.decisions import DecisionsFile, read_decisions
from media_dedup.review.app import DECIDE_PATH, STATE_PATH, ReviewApp
from media_dedup.review.session import ReviewSession, ReviewSource
from media_dedup.review.views import StateBuilder
from media_dedup.services.policy import keep_policy
from media_dedup.services.review import decisions_path
from media_dedup.services.writable import ensure_writable

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from media_dedup.plan.models import AuditFindings
    from media_dedup.services.runtime import Runtime

# Every interface of the container: Docker forwards the published port to it.
LISTEN_HOST: Final = "0.0.0.0"  # noqa: S104
_TEMPLATES_PACKAGE: Final = "media_dedup.review"
_PAGE_TEMPLATE: Final = "review.html.j2"


def review_target(runtime: Runtime, decisions: Path) -> Path:
    """Check, before the audit, that the decisions file will outlive the container.

    Args:
        runtime: Settings, mount points and output.
        decisions: `--decisions` value; a relative path lies in the reports folder.

    Returns:
        The decisions file, in the container.

    Raises:
        MountError: The reports folder is not mounted, or not writable.
    """
    if not decisions.is_absolute():
        if not runtime.persistent(MountKind.REPORTS):
            raise MountError(
                _("The decisions are saved in /reports: mount it, or they are lost."),
                _('Add -v "<a folder of yours>:/reports" to the docker run command.'),
            )
        ensure_writable(runtime, MountKind.REPORTS)
    return decisions_path(runtime, decisions)


def open_review(
    runtime: Runtime, findings: AuditFindings, target: Path
) -> ReviewSession:
    """Start the review of the audit's burst series, resuming the decisions file.

    Args:
        runtime: Settings, mount points and output.
        findings: The audit just run.
        target: The decisions file, in the container.

    Returns:
        The session.

    Raises:
        DecisionsError: The file is not a decisions file, or was made on other
            folders.
    """
    mapper = runtime.mapper
    builder = StateBuilder(
        mapper, keep_policy(runtime.settings, mapper), findings.similar.visuals
    )
    source = ReviewSource(findings.similar.bursts, builder, target)
    roots = mapper.roots_on_host(findings.roots)
    if not target.exists():
        return ReviewSession(source, DecisionsFile(version=1, roots=roots))
    base = read_decisions(target)
    if sorted(base.roots) != sorted(roots):
        message = _(
            "{path} was made on other folders ({theirs}); this review analyses {ours}."
        )
        raise DecisionsError(
            message.format(
                path=target.name, theirs=", ".join(base.roots), ours=", ".join(roots)
            ),
            _("Name another file with --decisions, or mount the same folders."),
        )
    return ReviewSession(source, base)


def serve_review(runtime: Runtime, session: ReviewSession, port: int) -> None:
    """Serve the review page until Ctrl+C; every decision is saved as it is made.

    Args:
        runtime: Settings, mount points and output.
        session: The review.
        port: The port to listen on, inside the container (0: any free one).
    """
    environment = translated_environment(_TEMPLATES_PACKAGE, escaped=("html", "j2"))
    page = environment.get_template(_PAGE_TEMPLATE).render(
        state_path=STATE_PATH, decide_path=DECIDE_PATH, file=session.target_name
    )
    with runtime.executor_factory() as executor, contextlib.suppress(KeyboardInterrupt):
        app = ReviewApp(session, page.encode(), executor)
        asyncio.run(run_server(app, port, partial(_announce, runtime, session)))


async def run_server(app: ReviewApp, port: int, ready: Callable[[int], None]) -> None:
    """Listen, tell the port, and serve until cancelled.

    Args:
        app: Answers each connection.
        port: The port to listen on (0: any free one).
        ready: Called with the port actually listened on.
    """
    server = await asyncio.start_server(app.connection, LISTEN_HOST, port)
    async with server:
        ready(server.sockets[0].getsockname()[1])
        await server.serve_forever()


def _announce(runtime: Runtime, session: ReviewSession, port: int) -> None:
    """Tell where the review is and how to open it from the host.

    Args:
        runtime: Settings, mount points and output.
        session: The review.
        port: The port listened on, inside the container.
    """
    output = runtime.output
    output.success(
        _(
            "Review ready on port {port}: each decision is saved at once in {file}. "
            "Ctrl+C stops the review."
        ).format(port=port, file=session.target_name)
    )
    output.tip(
        _(
            "Its address on your computer: run 'docker port {container} {port}' in "
            "another terminal, then open http://<that address> in your browser."
        ).format(container=socket.gethostname(), port=port)
    )
