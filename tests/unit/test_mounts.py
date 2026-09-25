"""Mount table inspection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from media_dedup.paths.locations import Locations
from media_dedup.paths.mount_kind import MountKind
from media_dedup.paths.mounts import MountTable, is_read_only, read_mounts

if TYPE_CHECKING:
    from pathlib import Path

MOUNTINFO = (
    "36 35 98:0 / / rw,noatime - overlay overlay rw\n"
    "40 36 0:52 /photos /data/c/Family\\040Photos rw - 9p drvfs rw\n"
    "41 36 0:53 / /journal rw - ext4 /dev/sdb rw\n"
    "broken line\n"
)


def test_read_mounts_decodes_escapes(tmp_path: Path) -> None:
    r"""Spaces are escaped as \040 in mountinfo; short lines are ignored."""
    table = tmp_path / "mountinfo"
    table.write_text(MOUNTINFO)
    points = MountTable.current(table).mount_points
    assert {str(point) for point in points} == {
        "/",
        "/data/c/Family Photos",
        "/journal",
    }


def test_read_mounts_without_table(tmp_path: Path) -> None:
    """No mount table (not Linux) means no known mount."""
    assert not read_mounts(tmp_path / "absent")


def test_persistence_needs_a_mount_or_an_explicit_path(tmp_path: Path) -> None:
    """Default paths persist only when mounted; explicit paths always do."""
    table = tmp_path / "mountinfo"
    table.write_text(MOUNTINFO)
    mounts = MountTable.current(table)
    defaults = Locations()
    assert mounts.is_persistent(defaults, MountKind.JOURNAL)
    assert not mounts.is_persistent(defaults, MountKind.REPORTS)
    explicit = Locations(reports_dir=tmp_path)
    assert MountTable(frozenset()).is_persistent(explicit, MountKind.REPORTS)


def test_data_roots_are_the_nested_mounts(tmp_path: Path) -> None:
    """Folders mounted below /data are the roots; otherwise /data itself."""
    table = tmp_path / "mountinfo"
    table.write_text(MOUNTINFO)
    mounts = MountTable.current(table)
    assert [str(root) for root in mounts.data_roots(Locations().data_dir)] == [
        "/data/c/Family Photos",
    ]
    assert MountTable(frozenset()).data_roots(tmp_path) == (tmp_path,)


def test_current_table_and_read_only_flag(tmp_path: Path) -> None:
    """The live mount table is readable and a temp dir is writable."""
    assert isinstance(MountTable.current().mount_points, frozenset)
    assert not is_read_only(tmp_path)


DOCKER_DESKTOP = (
    "2070 2061 0:69 /Photos /data/current ro,noatime - 9p C:\\134 rw,aname=drvfs\n"
    "2100 2091 0:63 /desktop/mnt/host/d/My\\040Pics /data/d2 ro - tmpfs none rw\n"
    "2101 2091 8:64 /var/lib/x /journal rw - ext4 /dev/sde rw\n"
    "2102 2091 8:64 /var/lib/y /no-tail rw\n"
)


def test_windows_sources_come_from_docker_desktop_mounts(tmp_path: Path) -> None:
    """Drvfs and Docker Desktop host mounts reveal the Windows folder; others do not."""
    table = tmp_path / "mountinfo"
    table.write_text(DOCKER_DESKTOP)
    assert {
        str(point): host for point, host in MountTable.current(table).host_sources
    } == {
        "/data/current": "C:\\Photos",
        "/data/d2": "D:\\My Pics",
    }
