"""`media-dedup review`: the page, its state, previews, and decisions saved at once."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from media_dedup.errors import DecisionsError
from media_dedup.report.decisions import read_decisions
from tests.support.review import (
    BURST_HOST,
    PAGE,
    Call,
    decide,
    review_session,
    serve_and_call,
    write_burst,
)

if TYPE_CHECKING:
    from media_dedup.paths.locations import Locations

JSON = ("Host: 127.0.0.1", "Content-Type: application/json")


def test_the_page_the_state_and_the_previews(locations: Locations) -> None:
    """The series comes with its sharpest shot; previews are cached JPEG files."""
    write_burst(locations.data_dir)
    session = review_session(locations)
    [series] = session.state().series
    preview = series.shots[0].preview
    page, state, image, unknown, other = serve_and_call(
        session,
        [
            Call("GET", "/"),
            Call("GET", "/api/state?now"),
            Call("GET", preview),
            Call("GET", "/preview/0123.jpg"),
            Call("GET", "/favicon.ico"),
        ],
    )
    assert (page.status, page.body) == (200, PAGE)
    assert page.headers["content-type"].startswith("text/html")
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert state.json() == json.loads(session.state().model_dump_json())
    assert sum(shot.best for shot in series.shots) == 1
    assert not series.shots[1].best  # the blurred one
    assert [shot.folder for shot in series.shots] == [BURST_HOST] * 3
    assert (image.status, image.headers["content-type"]) == (200, "image/jpeg")
    assert image.body.startswith(b"\xff\xd8")
    assert "immutable" in image.headers["cache-control"]
    assert (unknown.status, other.status) == (404, 404)


def test_each_decision_is_saved_at_once_and_resumed(locations: Locations) -> None:
    """Report pairs stay; the review resumes; a series kept whole is not listed."""
    write_burst(locations.data_dir)
    target = locations.reports_dir / "decisions.json"
    target.write_text(json.dumps({"version": 1, "roots": ["C:\\"], "pairs": []}))
    session = review_session(locations)
    [first] = serve_and_call(session, [decide(0, 1)])
    assert (first.status, first.json()) == (200, {"series": 1, "shots": 1})
    [burst] = read_decisions(target).bursts
    assert burst.discarded == (f"{BURST_HOST}\\IMG_1.jpg",)
    assert burst.kept == (f"{BURST_HOST}\\IMG_0.jpg", f"{BURST_HOST}\\IMG_2.jpg")
    resumed = review_session(locations)
    assert resumed.state().series[0].discarded == (1,)
    assert resumed.progress == (1, 1)
    serve_and_call(resumed, [decide(0)])
    assert read_decisions(target).bursts == ()


@pytest.mark.parametrize(
    ("call", "status"),
    [
        (Call("GET", "/", headers=("Host: rebind.example:8080",)), 403),
        (Call("GET", "/", headers=()), 403),
        (Call("POST", "/api/decide", b'{"series": 0, "discarded": [1]}'), 415),
        (
            Call("POST", "/api/decide", b"{}", (*JSON, "Origin: http://evil.example")),
            403,
        ),
        (Call("POST", "/api/decide", b'{"series": "x"}', JSON), 400),
        (Call("PUT", "/api/decide", b"{}", JSON), 405),
        (
            Call(
                "GET", "/", headers=("Host: [::1]:8080", "Transfer-Encoding: chunked")
            ),
            501,
        ),
        (
            Call("GET", "/", headers=("Host: localhost", "Content-Length: 99999999")),
            413,
        ),
        (Call("GET", "/", headers=("Host: localhost", "Content-Length: x")), 400),
        (Call("GET", "/", headers=("Host: localhost", "no colon")), 400),
        (Call("GET", "/", headers=tuple(f"X-{n}: y" for n in range(70))), 431),
        (b"GARBAGE\r\n\r\n", 400),
        (b"GET /" + b"x" * 70_000 + b" HTTP/1.1\r\n\r\n", 431),
    ],
)
def test_refused_requests(
    locations: Locations, call: Call | bytes, status: int
) -> None:
    """Another host name, no JSON, another site, garbage: refused, nothing saved."""
    write_burst(locations.data_dir)
    session = review_session(locations)
    [reply] = serve_and_call(session, [call])
    assert reply.status == status
    assert not (locations.reports_dir / "decisions.json").exists()


@pytest.mark.parametrize(
    ("call", "error"),
    [
        (decide(0, 0, 1, 2), "Keep at least one shot"),
        (decide(3, 1), "no such series"),
        (decide(0, 7), "no such shot"),
    ],
)
def test_impossible_decisions_are_explained(
    locations: Locations, call: Call, error: str
) -> None:
    """The page shows the reason; the file is left as it was."""
    write_burst(locations.data_dir)
    [reply] = serve_and_call(review_session(locations), [call])
    assert reply.status == 422
    body = reply.json()
    assert isinstance(body, dict)
    assert error in body["error"]


def test_protected_shots_stay(locations: Locations) -> None:
    """A shot of a protected folder is shown as such and never set aside."""
    write_burst(locations.data_dir)
    session = review_session(locations, {"folders": {"protected": [BURST_HOST]}})
    assert all(shot.protected for shot in session.state().series[0].shots)
    [reply] = serve_and_call(session, [decide(0, 1)])
    assert reply.status == 422
    assert b"protected folder" in reply.body


def test_a_saving_error_is_reported(locations: Locations) -> None:
    """The reports folder vanished: the page says the choice was not saved."""
    write_burst(locations.data_dir)
    session = review_session(locations)
    locations.reports_dir.rmdir()
    [reply] = serve_and_call(session, [decide(0, 1)])
    assert reply.status == 500
    assert b"Cannot save the decisions file" in reply.body


def test_a_vanished_shot_has_no_preview(locations: Locations) -> None:
    """Deleted since the audit: 404, the page shows its broken image."""
    shots = write_burst(locations.data_dir)
    session = review_session(locations)
    preview = session.state().series[0].shots[0].preview
    shots[0].unlink()
    [reply] = serve_and_call(session, [Call("GET", preview)])
    assert reply.status == 404


def test_decisions_of_other_folders_or_series_are_not_resumed(
    locations: Locations,
) -> None:
    """Other roots: refused; a series that changed: dropped and counted."""
    write_burst(locations.data_dir)
    target = locations.reports_dir / "decisions.json"
    target.write_text(json.dumps({"version": 1, "roots": ["E:\\"]}))
    with pytest.raises(DecisionsError, match="made on other folders"):
        review_session(locations)
    gone = {"kept": [f"{BURST_HOST}\\IMG_0.jpg"], "discarded": ["C:\\gone.jpg"]}
    target.write_text(json.dumps({"version": 1, "roots": ["C:\\"], "bursts": [gone]}))
    session = review_session(locations)
    assert session.dropped == 1
    assert session.progress == (0, 0)
