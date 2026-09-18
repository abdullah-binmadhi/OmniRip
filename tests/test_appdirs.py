from pathlib import Path

from harvester.appdirs import AppPaths


def test_app_paths_are_isolated_and_created(tmp_path: Path) -> None:
    paths = AppPaths.from_base(tmp_path / "data", config_file=tmp_path / "config.toml")

    paths.ensure()

    assert paths.data_dir == (tmp_path / "data").resolve()
    assert paths.workspace.is_dir()
    assert paths.cache.is_dir()
    assert paths.logs.is_dir()
    assert paths.reports.is_dir()
    assert paths.quarantine.is_dir()
    assert paths.job_workspace("abc") == paths.workspace / "abc"
