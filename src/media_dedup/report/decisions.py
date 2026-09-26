r"""The decisions file the report downloads (`decisions.json`) and `clean` reads.

```json
{"version": 1, "report": "20260926-171446-audit", "roots": ["C:\\Photos"],
 "pairs": [{"kept_in": "C:\\Photos\\2019", "removed_from": "D:\\Old",
            "action": "swap"}]}
```

Paths are host paths, as the report shows them. `roots` are the folders analysed by the
audit behind the report: `clean` refuses the file when it sees other folders. Pairs left
as planned are not listed. The schema is versioned so that the review of bursts (0004)
can add its own key.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from media_dedup.errors import DecisionsError
from media_dedup.i18n import _
from media_dedup.plan.review import PairAction

if TYPE_CHECKING:
    from pathlib import Path

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class PairDecision(BaseModel):
    """The decision on one folder pair, in host paths."""

    model_config = _FROZEN

    kept_in: str
    removed_from: str
    action: PairAction


class DecisionsFile(BaseModel):
    """Every decision of one review, and the audit it was made on."""

    model_config = _FROZEN

    version: Literal[1]
    report: str = ""
    roots: tuple[str, ...]
    pairs: tuple[PairDecision, ...] = ()

    @field_validator("pairs")
    @classmethod
    def _each_pair_once(
        cls, pairs: tuple[PairDecision, ...]
    ) -> tuple[PairDecision, ...]:
        """Refuse a pair decided twice: which decision would win?

        Args:
            pairs: The decisions.

        Returns:
            The decisions, unchanged.

        Raises:
            ValueError: A pair appears twice.
        """
        seen: set[tuple[str, str]] = set()
        for pair in pairs:
            key = (pair.kept_in, pair.removed_from)
            if key in seen:
                message = f"{pair.kept_in} -> {pair.removed_from} is decided twice"
                raise ValueError(message)
            seen.add(key)
        return pairs


def read_decisions(path: Path) -> DecisionsFile:
    """Read and validate a decisions file.

    Args:
        path: The file, in the container.

    Returns:
        Its decisions.

    Raises:
        DecisionsError: The file is missing or is not a valid decisions file.
    """
    tip = _("Download it again from the report, next to it on /reports.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        message = _("Cannot read the decisions file {path}.").format(path=path)
        raise DecisionsError(message, tip) from exc
    try:
        return DecisionsFile.model_validate_json(raw)
    except ValidationError as exc:
        message = _("{path} is not a valid decisions file ({error}).").format(
            path=path, error=exc.errors()[0]["msg"]
        )
        raise DecisionsError(message, tip) from exc
