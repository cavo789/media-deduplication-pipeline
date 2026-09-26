"""The routes of the review: the page, its state, the previews, and each decision.

`GET /` serves the page, `GET /api/state` every series and the shots set aside,
`GET /preview/<key>.jpg` a large preview (rendered in the worker pool), and
`POST /api/decide` sets shots of one series aside, saved at once. A decision needs a
JSON body: a page of another site cannot send one without the browser asking first.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, ConfigDict, ValidationError

from media_dedup.errors import DecisionsError
from media_dedup.i18n import _
from media_dedup.report.thumbnails import review_preview
from media_dedup.review.http import (
    BadRequestError,
    ContentType,
    Response,
    is_local,
    read_request,
    write_response,
)
from media_dedup.review.views import PREVIEW_PREFIX

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from media_dedup.review.http import Request
    from media_dedup.review.session import ReviewSession

PAGE_PATH: Final = "/"
STATE_PATH: Final = "/api/state"
DECIDE_PATH: Final = "/api/decide"
_PREVIEW_SUFFIX: Final = ".jpg"
_GET, _POST = "GET", "POST"
_DROPPED_CONNECTION: Final = (
    TimeoutError,
    asyncio.IncompleteReadError,
    ConnectionError,
)


class _Decision(BaseModel):
    """`POST /api/decide`: the ranks of the shots set aside in one series."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    series: int
    discarded: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ReviewApp:
    """Answers the browser; the session holds the state and saves it."""

    session: ReviewSession
    page: bytes
    executor: Executor

    async def connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Serve one connection: one request, one response.

        Args:
            reader: What the browser sends.
            writer: Where to answer.
        """
        try:
            try:
                request = await read_request(reader)
            except BadRequestError as exc:
                response = Response(exc.status)
            else:
                response = await self.handle(request)
            await write_response(writer, response)
        except _DROPPED_CONNECTION:
            pass  # the browser went away: nothing to answer
        finally:
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()

    async def handle(self, request: Request) -> Response:
        """Route a request.

        Args:
            request: The request.

        Returns:
            The response.
        """
        if not is_local(request):
            message = _("Open the review at 127.0.0.1 or localhost.")
            return Response(HTTPStatus.FORBIDDEN, message.encode())
        if request.method == _GET:
            return await self._get(request.path)
        if request.path == DECIDE_PATH and request.method == _POST:
            return self._decide(request)
        return Response(HTTPStatus.METHOD_NOT_ALLOWED)

    async def _get(self, path: str) -> Response:
        """Serve the page, the state, or a preview.

        Args:
            path: The path asked for.

        Returns:
            The response; 404 for anything else, or a preview that cannot be made.
        """
        if path == PAGE_PATH:
            return Response(HTTPStatus.OK, self.page, ContentType.HTML)
        if path == STATE_PATH:
            state = self.session.state().model_dump_json().encode()
            return Response(HTTPStatus.OK, state, ContentType.JSON)
        key = path.removeprefix(PREVIEW_PREFIX).removesuffix(_PREVIEW_SUFFIX)
        source = self.session.preview_source(key)
        if source is None or path != f"{PREVIEW_PREFIX}{key}{_PREVIEW_SUFFIX}":
            return Response(HTTPStatus.NOT_FOUND)
        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(self.executor, review_preview, source)
        if image is None:
            return Response(HTTPStatus.NOT_FOUND)
        return Response(HTTPStatus.OK, image, ContentType.JPEG, cacheable=True)

    def _decide(self, request: Request) -> Response:
        """Set shots of a series aside and save the decisions file.

        Args:
            request: `POST /api/decide`, with a JSON body.

        Returns:
            The new totals, or an error with a translated message.
        """
        headers = request.headers
        if not headers.get("content-type", "").startswith(ContentType.JSON):
            return Response(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        origin = headers.get("origin")
        if origin is not None and origin != f"http://{headers.get('host')}":
            return Response(HTTPStatus.FORBIDDEN)
        try:
            decision = _Decision.model_validate_json(request.body)
            self.session.decide(decision.series, frozenset(decision.discarded))
        except ValidationError:
            return Response(HTTPStatus.BAD_REQUEST)
        except DecisionsError as exc:
            return _json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": exc.message})
        except OSError as exc:
            message = _("Cannot save the decisions file: {error}.")
            error = message.format(error=exc.strerror or exc)
            return _json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": error})
        series, shots = self.session.progress
        return _json(HTTPStatus.OK, {"series": series, "shots": shots})


def _json(status: HTTPStatus, value: dict[str, object]) -> Response:
    """Answer with a JSON object.

    Args:
        status: The status.
        value: The object.

    Returns:
        The response.
    """
    return Response(status, json.dumps(value).encode(), ContentType.JSON)
