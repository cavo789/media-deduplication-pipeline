"""The fixed mount points of the container, each overridable from the environment."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict

from media_dedup.constants import CONFIG_FILE_NAME, ENV_PREFIX, INDEX_FILE_NAME

if TYPE_CHECKING:
    from media_dedup.paths.mount_kind import MountKind


class Locations(BaseSettings):
    """Mount points of the container (`MEDIA_DEDUP_<NAME>_DIR` overrides each one).

    `/config` holds the configuration file only; every other kind of data has its own
    mount point so the user can store it wherever they want on the host.
    """

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX, frozen=True, extra="ignore"
    )

    data_dir: Path = Path("/data")
    config_dir: Path = Path("/config")
    journal_dir: Path = Path("/journal")
    quarantine_dir: Path = Path("/quarantine")
    reports_dir: Path = Path("/reports")
    cache_dir: Path = Path("/cache")

    @property
    def config_file(self) -> Path:
        """Path of the user-editable configuration file.

        Returns:
            `<config_dir>/config.toml`.
        """
        return self.config_dir / CONFIG_FILE_NAME

    @property
    def index_file(self) -> Path:
        """Path of the SQLite index that makes audits incremental.

        Returns:
            `<cache_dir>/index.sqlite`.
        """
        return self.cache_dir / INDEX_FILE_NAME

    def path_of(self, kind: MountKind) -> Path:
        """Return the directory of a mount point.

        Args:
            kind: Which mount point.

        Returns:
            Its path inside the container.
        """
        return Path(getattr(self, f"{kind.value}_dir"))

    def is_explicit(self, kind: MountKind) -> bool:
        """Tell whether the path of `kind` was set through the environment.

        An explicit path is trusted as persistent even when it is not a Docker mount
        (devcontainer helpers and tests redirect everything to /tmp this way).

        Args:
            kind: Which mount point.

        Returns:
            True when `MEDIA_DEDUP_<KIND>_DIR` was set.
        """
        return f"{kind.value}_dir" in self.model_fields_set
