"""Choice of the copy to keep in a duplicate group."""

from __future__ import annotations

from pathlib import Path

from media_dedup.constants import KeepReason, MediaKind
from media_dedup.plan.keeper import KeepPolicy
from media_dedup.scan.models import DuplicateGroup, MediaFile

DATA = Path("/data")


def file_at(relative: str, mtime_ns: int = 0) -> MediaFile:
    """Describe a 10-byte image at `/data/<relative>`."""
    return MediaFile(DATA / relative, 10, mtime_ns, MediaKind.IMAGE)


def keeper_of(policy: KeepPolicy, *files: MediaFile) -> Path:
    """Return the path the policy keeps among `files`."""
    return policy.decide(DuplicateGroup("digest", 10, files)).keeper.path


def test_protected_folder_wins_over_everything() -> None:
    """A copy in a protected folder is kept, even when it looks like a copy."""
    policy = KeepPolicy(protected=(DATA / "d/backup",))
    kept = keeper_of(policy, file_at("c/a/IMG.jpg"), file_at("d/backup/IMG (1).jpg", 9))
    assert kept == DATA / "d/backup/IMG (1).jpg"


def test_preferred_folders_follow_their_order() -> None:
    """The first preferred folder beats the second one."""
    policy = KeepPolicy(preferred=(DATA / "c/archive", DATA / "c/family"))
    kept = keeper_of(
        policy, file_at("c/family/IMG.jpg"), file_at("c/archive/IMG.jpg", 5)
    )
    assert kept == DATA / "c/archive/IMG.jpg"


def test_preferred_match_ignores_case() -> None:
    """Windows paths are case-insensitive: so is the preference."""
    policy = KeepPolicy(preferred=(DATA / "c/Family Photos",))
    kept = keeper_of(
        policy, file_at("c/other/IMG.jpg"), file_at("c/family photos/IMG.jpg", 5)
    )
    assert kept == DATA / "c/family photos/IMG.jpg"


def test_a_sidecar_keeps_its_photo() -> None:
    """The copy with a sidecar (its edits) wins, unless another folder is preferred."""
    edited, plain = file_at("c/long/path/IMG (1).jpg", 9), file_at("d/IMG.jpg")
    policy = KeepPolicy(with_sidecar=frozenset({edited.path}))
    decision = policy.decide(DuplicateGroup("digest", 10, (plain, edited)))
    assert decision.keeper == edited
    assert decision.reason is KeepReason.HAS_SIDECAR
    preferred = KeepPolicy(preferred=(DATA / "d",), with_sidecar=policy.with_sidecar)
    assert keeper_of(preferred, plain, edited) == plain.path


def test_original_name_beats_copy_name() -> None:
    """Without preference, `IMG.jpg` is kept rather than `IMG (1).jpg`."""
    kept = keeper_of(
        KeepPolicy(), file_at("c/a/IMG (1).jpg"), file_at("c/a/IMG.jpg", 5)
    )
    assert kept == DATA / "c/a/IMG.jpg"


def test_oldest_then_shortest_then_alphabetical() -> None:
    """Remaining ties: oldest mtime, then shortest path, then alphabetical order."""
    policy = KeepPolicy()
    assert (
        keeper_of(policy, file_at("c/b.jpg", 2), file_at("c/a.jpg", 1))
        == DATA / "c/a.jpg"
    )
    assert (
        keeper_of(policy, file_at("c/x/y/a.jpg"), file_at("c/z.jpg"))
        == DATA / "c/z.jpg"
    )
    assert keeper_of(policy, file_at("c/B.jpg"), file_at("c/a.jpg")) == DATA / "c/a.jpg"


def test_protected_copies_are_never_removable() -> None:
    """Every protected copy stays; only unprotected ones are removable."""
    policy = KeepPolicy(protected=(DATA / "d",))
    group = DuplicateGroup(
        "digest",
        10,
        (file_at("d/one.jpg"), file_at("d/two.jpg"), file_at("c/three.jpg")),
    )
    decision = policy.decide(group)
    assert decision.keeper.path == DATA / "d/one.jpg"
    assert [f.path for f in decision.protected] == [DATA / "d/two.jpg"]
    assert [f.path for f in decision.removable] == [DATA / "c/three.jpg"]
    assert decision.reclaimable == 10
