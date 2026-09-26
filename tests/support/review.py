"""A burst series on disk, a review session on it, and raw HTTP calls to its server."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from media_dedup.review.app import ReviewApp
from media_dedup.scan.image_check import prepare_image_worker
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.reviewing import open_review, run_server
from tests.support.runtime import make_runtime
from tests.support.scenes import Effect, Shot, write_shot

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from media_dedup.config.layers import Layer
    from media_dedup.paths.locations import Locations
    from media_dedup.review.session import ReviewSession

BURST: Final = "c/Photos/Rafale"
BURST_HOST: Final = "C:\\Photos\\Rafale"
PAGE: Final = b"<!DOCTYPE html><title>review</title>"
_SHOTS: Final = 3
_SEED: Final = 100
_BLURRED: Final = 1


def write_burst(data_dir: Path) -> list[Path]:
    """Write three shots of one scene, a second apart; the middle one is blurred.

    Args:
        data_dir: Directory standing for the /data mount point.

    Returns:
        The shots, in time order.
    """
    return [
        write_shot(
            data_dir / f"{BURST}/IMG_{rank}.jpg",
            Shot(
                _SEED,
                shift=4 * rank,
                taken_at=f"2021:07:04 10:15:0{rank}",
                effect=Effect.BLURRED if rank == _BLURRED else Effect.NONE,
            ),
        )
        for rank in range(_SHOTS)
    ]


def review_session(locations: Locations, cli: Layer | None = None) -> ReviewSession:
    """Audit the data folder and open a review saved in /reports/decisions.json.

    Args:
        locations: The test mount points.
        cli: Command-line overrides (e.g. protected folders).

    Returns:
        The session.
    """
    runtime = make_runtime(locations, cli)
    findings = AuditService(runtime, NullProgress()).run()
    return open_review(runtime, findings, locations.reports_dir / "decisions.json")


@dataclass(frozen=True, slots=True)
class Call:
    """A raw HTTP request, `Host: 127.0.0.1` unless other headers are given."""

    method: str
    path: str
    body: bytes = b""
    headers: tuple[str, ...] = ("Host: 127.0.0.1",)

    def encode(self) -> bytes:
        """Render the request as sent on the wire."""
        length = (f"Content-Length: {len(self.body)}",) if self.body else ()
        lines = (f"{self.method} {self.path} HTTP/1.1", *self.headers, *length)
        return ("\r\n".join(lines) + "\r\n\r\n").encode() + self.body


def decide(series: int, *discarded: int) -> Call:
    """`POST /api/decide`, as the page sends it."""
    body = json.dumps({"series": series, "discarded": list(discarded)}).encode()
    headers = ("Host: 127.0.0.1", "Content-Type: application/json")
    return Call("POST", "/api/decide", body, headers)


@dataclass(frozen=True, slots=True)
class Reply:
    """What the server answered."""

    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def json(self) -> object:
        """The body, decoded as JSON."""
        return json.loads(self.body)


def serve_and_call(
    session: ReviewSession, calls: Sequence[Call | bytes]
) -> list[Reply]:
    """Serve the review on a free port, send each call, then stop the server.

    Args:
        session: The review.
        calls: The requests, in order (bytes: sent as they are).

    Returns:
        The replies, in order.
    """

    async def scenario() -> list[Reply]:
        with ThreadPoolExecutor(1, initializer=prepare_image_worker) as executor:
            app = ReviewApp(session, PAGE, executor)
            ports: asyncio.Queue[int] = asyncio.Queue()
            async with asyncio.TaskGroup() as group:
                server = group.create_task(run_server(app, 0, ports.put_nowait))
                port = await ports.get()
                replies = [await _send(port, call) for call in calls]
                server.cancel()
        return replies

    return asyncio.run(scenario())


async def _send(port: int, call: Call | bytes) -> Reply:
    """Send one request on a new connection and read the whole answer."""
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(call.encode() if isinstance(call, Call) else call)
    await writer.drain()
    raw = await reader.read()
    writer.close()
    await writer.wait_closed()
    head, _blank, body = raw.partition(b"\r\n\r\n")
    status, *lines = head.decode("latin-1").split("\r\n")
    headers = {
        name.lower(): value.strip()
        for name, _colon, value in (line.partition(":") for line in lines)
    }
    return Reply(int(status.split()[1]), headers, body)
