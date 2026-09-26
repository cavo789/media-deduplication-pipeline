"""A minimal HTTP/1.1 exchange on asyncio streams: one request, one response, closed.

Enough for one local page: GET, and POST with a small body; no keep-alive, no chunked
body. Requests must name a loopback host (`localhost`, `127.0.0.1`): Docker publishes
the port on 127.0.0.1, and a page of another site reaching it through its own domain
name (DNS rebinding) is refused.
"""

from __future__ import annotations

import asyncio
import ipaddress
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

_MAX_BODY: Final = 64 * 1024
_MAX_HEADERS: Final = 64
_TIMEOUT_SECONDS: Final = 30.0
_HEADER_ENCODING: Final = "latin-1"
_LOCALHOST: Final = "localhost"
_HTTP_1: Final = "HTTP/1."
_REQUEST_LINE_PARTS: Final = 3  # method, target, version
_SECURITY_HEADERS: Final = (
    "X-Content-Type-Options: nosniff",
    "Referrer-Policy: no-referrer",
    (
        "Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; "
        "style-src 'unsafe-inline'; img-src 'self'; connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
)


class ContentType(StrEnum):
    """Media types the review server answers with."""

    HTML = "text/html; charset=utf-8"
    JSON = "application/json"
    JPEG = "image/jpeg"
    TEXT = "text/plain; charset=utf-8"


@dataclass(frozen=True, slots=True)
class Request:
    """A request: method, path without its query, headers (lower-case names), body."""

    method: str
    path: str
    headers: Mapping[str, str]
    body: bytes = b""


@dataclass(frozen=True, slots=True)
class Response:
    """A response; `cacheable` ones never change for a given path."""

    status: HTTPStatus
    body: bytes = b""
    content_type: ContentType = ContentType.TEXT
    cacheable: bool = False


class BadRequestError(Exception):
    """The request cannot be served; `status` says why."""

    def __init__(self, status: HTTPStatus) -> None:
        """Remember the status to answer with.

        Args:
            status: The error status.
        """
        super().__init__(status.phrase)
        self.status = status


async def read_request(reader: asyncio.StreamReader) -> Request:
    """Read one request.

    Args:
        reader: The connection.

    Returns:
        The request.

    Raises:
        BadRequestError: A malformed, oversized or unsupported request.
        TimeoutError: The browser sent nothing for too long.
        IncompleteReadError: The connection closed in the middle of the request.
    """
    async with asyncio.timeout(_TIMEOUT_SECONDS):
        try:
            parts = (await reader.readline()).decode(_HEADER_ENCODING).split()
            if len(parts) != _REQUEST_LINE_PARTS or not parts[2].startswith(_HTTP_1):
                raise BadRequestError(HTTPStatus.BAD_REQUEST)
            headers = await _read_headers(reader)
        except ValueError as exc:  # a line longer than the reader's limit
            raise BadRequestError(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE) from exc
        body = await _read_body(reader, headers)
    method, target = parts[0], parts[1]
    return Request(method, target.split("?", 1)[0], headers, body)


def is_local(request: Request) -> bool:
    """Tell whether the request names a loopback host.

    Args:
        request: The request.

    Returns:
        True for `localhost`, `127.0.0.1`, `[::1]`, with any port.
    """
    host = request.headers.get("host", "")
    name = host[1:].partition("]")[0] if host.startswith("[") else host.split(":")[0]
    if name == _LOCALHOST:
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


async def write_response(writer: asyncio.StreamWriter, response: Response) -> None:
    """Send a response; the connection is closed by the caller.

    Args:
        writer: The connection.
        response: What to send.
    """
    status = response.status
    cache = "private, max-age=86400, immutable" if response.cacheable else "no-store"
    head = (
        f"HTTP/1.1 {status.value} {status.phrase}",
        f"Content-Type: {response.content_type}",
        f"Content-Length: {len(response.body)}",
        f"Cache-Control: {cache}",
        "Connection: close",
        *_SECURITY_HEADERS,
    )
    writer.write(("\r\n".join(head) + "\r\n\r\n").encode(_HEADER_ENCODING))
    writer.write(response.body)
    await writer.drain()


async def _read_headers(reader: asyncio.StreamReader) -> dict[str, str]:
    """Read the header lines, up to the blank line.

    Args:
        reader: The connection.

    Returns:
        The headers, names in lower case.

    Raises:
        BadRequestError: A line without a colon, or too many headers.
    """
    headers: dict[str, str] = {}
    for _line in range(_MAX_HEADERS):
        line = (await reader.readline()).decode(_HEADER_ENCODING).strip()
        if not line:
            return headers
        name, colon, value = line.partition(":")
        if not colon:
            raise BadRequestError(HTTPStatus.BAD_REQUEST)
        headers[name.strip().lower()] = value.strip()
    raise BadRequestError(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)


async def _read_body(reader: asyncio.StreamReader, headers: Mapping[str, str]) -> bytes:
    """Read the body announced by `Content-Length`.

    Args:
        reader: The connection.
        headers: The request headers.

    Returns:
        The body (empty without `Content-Length`).

    Raises:
        BadRequestError: A chunked, oversized or wrongly announced body.
    """
    if "transfer-encoding" in headers:
        raise BadRequestError(HTTPStatus.NOT_IMPLEMENTED)
    length = headers.get("content-length", "0")
    if not length.isdigit():
        raise BadRequestError(HTTPStatus.BAD_REQUEST)
    if int(length) > _MAX_BODY:
        raise BadRequestError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
    return await reader.readexactly(int(length))
