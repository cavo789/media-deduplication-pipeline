"""Other files than media, asked for with `--ext`: compared only, copies quarantined."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from media_dedup.actions.journal import journal_file, read_journal
from media_dedup.constants import ActionKind, MediaKind
from media_dedup.errors import MountError
from media_dedup.paths.mount_kind import MountKind
from media_dedup.scan.progress import NullProgress
from media_dedup.services.audit import AuditService
from media_dedup.services.clean import CleanService
from media_dedup.services.undo import undo_run
from tests.support.media import MediaFactory
from tests.support.runtime import make_locations, make_runtime, output_of

if TYPE_CHECKING:
    from pathlib import Path

    from media_dedup.config.layers import Layer
    from media_dedup.paths.locations import Locations

_ASKED: Layer = {"scan": {"extensions": ["pdf", "jpg"]}}
_CONTRACT = b"%PDF-1.7 contract"


def documents_tree(data_dir: Path) -> Path:
    """A PDF and its copy, one in a software folder, an empty PDF, a photo copy."""
    media = MediaFactory(data_dir)
    photo = media.image("c/Photos/IMG_1.jpg", seed=1)
    media.copy(photo, "c/Photos/old/IMG_1.jpg")
    for relative in ("c/Docs/Contract.pdf", "c/Docs/project/node_modules/Contract.pdf"):
        path = data_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_CONTRACT)
    copy = data_dir / "c/Docs/old/Contract.pdf"
    copy.parent.mkdir(parents=True)
    copy.write_bytes(_CONTRACT)
    (data_dir / "c/Docs/__init__.pdf").touch()
    return copy


def test_other_files_are_compared_and_their_copies_quarantined(
    locations: Locations,
) -> None:
    """The PDF copy is moved, the photo copy deleted, and `undo` restores both."""
    copy = documents_tree(locations.data_dir)
    runtime = make_runtime(locations, _ASKED)
    findings = AuditService(runtime, NullProgress()).run()
    assert "Not photos or videos: .pdf." in output_of(runtime)
    assert not findings.plan.broken  # an empty document is not a broken photo
    kinds = {d.keeper.kind: d for d in findings.plan.decisions}
    assert set(kinds) == {MediaKind.IMAGE, MediaKind.OTHER}
    document = kinds[MediaKind.OTHER]
    assert len(document.removable) == 1  # node_modules is skipped
    assert findings.plan.moved_copies == 1
    service = CleanService(runtime, NullProgress())
    service.ensure_ready()
    run_id, outcome = service.execute(service.feasible(findings.plan))
    assert outcome.quarantined == 1
    assert not copy.exists()
    entries = read_journal(journal_file(locations.journal_dir, run_id))
    actions = {e.action for e in entries}
    assert actions == {ActionKind.QUARANTINE_DUPLICATE, ActionKind.DELETE_DUPLICATE}
    assert undo_run(runtime, run_id, NullProgress()).done == len(actions)
    assert copy.read_bytes() == _CONTRACT


def test_other_files_need_the_quarantine(tmp_path: Path) -> None:
    """Without /quarantine, `clean` refuses before analysing anything."""
    locations = make_locations(tmp_path, MountKind.QUARANTINE)
    runtime = make_runtime(locations, _ASKED)
    with pytest.raises(MountError, match="go to /quarantine"):
        CleanService(runtime, NullProgress()).ensure_ready()
