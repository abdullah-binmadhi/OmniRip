"""Platform-aware runtime directories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir


@dataclass(frozen=True, slots=True)
class AppPaths:
    """All paths used by harvester runtime state.

    The object is pure until :meth:`ensure` is called, which makes it safe to use while
    validating configuration and straightforward to inject into tests.
    """

    data_dir: Path
    config_file: Path
    workspace: Path
    cache: Path
    logs: Path
    reports: Path
    quarantine: Path

    @classmethod
    def from_base(
        cls,
        data_dir: Path | str,
        *,
        config_file: Path | str | None = None,
    ) -> AppPaths:
        base = Path(data_dir).expanduser().resolve()
        return cls(
            data_dir=base,
            config_file=(Path(config_file).expanduser() if config_file else base / "config.toml"),
            workspace=base / "workspace",
            cache=base / "cache",
            logs=base / "logs",
            reports=base / "reports",
            quarantine=base / "quarantine",
        )

    @classmethod
    def default(cls, app_name: str = "harvester") -> AppPaths:
        return cls.from_base(user_data_dir(app_name))

    def ensure(self) -> AppPaths:
        """Create runtime directories and return this immutable path set."""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        for directory in (self.workspace, self.cache, self.logs, self.reports, self.quarantine):
            directory.mkdir(parents=True, exist_ok=True)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        return self

    def job_workspace(self, job_id: str) -> Path:
        """Return a deterministic per-job directory without creating it."""

        return self.workspace / job_id


__all__ = ["AppPaths"]
