"""Translation between container and host paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from media_dedup.paths.host_paths import HostPathMapper, is_within

MAPPER = HostPathMapper(Path("/data"))


@pytest.mark.parametrize(
    ("container", "host"),
    [
        ("/data/c/Family Photos/IMG.jpg", "C:\\Family Photos\\IMG.jpg"),
        ("/data/d", "D:\\"),
        ("/data/home/me/pics", "/home/me/pics"),
        ("/elsewhere/file.jpg", "/elsewhere/file.jpg"),
    ],
)
def test_to_host(container: str, host: str) -> None:
    """Drive-letter folders render as Windows paths, others as POSIX paths."""
    assert MAPPER.to_host(Path(container)) == host


@pytest.mark.parametrize(
    ("host", "container"),
    [
        ("C:\\Family Photos", "/data/c/Family Photos"),
        ("d:/backup/2019/", "/data/d/backup/2019"),
        ("E:", "/data/e"),
        ("/home/me/pics", "/data/home/me/pics"),
        ("/data/c/x", "/data/c/x"),
        ("relative/dir", "/data/relative/dir"),
    ],
)
def test_to_container(host: str, container: str) -> None:
    """Paths typed by the user land under the data directory."""
    assert MAPPER.to_container(host) == Path(container)


def test_relative_keeps_the_tree() -> None:
    """The quarantine mirrors the tree below the data directory."""
    assert MAPPER.relative(Path("/data/c/a/b.jpg")) == Path("c/a/b.jpg")
    assert MAPPER.relative(Path("/other/b.jpg")) == Path("other/b.jpg")


def test_is_within_ignores_case_and_matches_whole_parts() -> None:
    r"""`C:\Photos` contains `c:\photos\x` but not `C:\Photos2`."""
    assert is_within(Path("/data/c/photos/x.jpg"), Path("/data/c/Photos"))
    assert is_within(Path("/data/c/Photos"), Path("/data/c/Photos"))
    assert not is_within(Path("/data/c/Photos2/x.jpg"), Path("/data/c/Photos"))
