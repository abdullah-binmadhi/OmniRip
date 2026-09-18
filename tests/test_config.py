from pathlib import Path

import pytest

from harvester.config import load_config
from harvester.util.errors import ConfigError


def test_defaults_are_valid_and_use_the_requested_data_dir(tmp_path: Path) -> None:
    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})

    assert config.batch.skip_bitrate_kbps == 256
    assert config.paths.data_dir == (tmp_path / "data").resolve()
    assert config.ffmpeg.transcode == "mp3-320"


def test_precedence_is_cli_over_environment_over_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[batch]\nskip_bitrate_kbps = 320\n[general]\nlog_level_file = 'WARNING'\n",
        encoding="utf-8",
    )

    config = load_config(
        config_file,
        environ={
            "HARVESTER_DATA_DIR": str(tmp_path / "data"),
            "HARVESTER_BATCH_SKIP_BITRATE_KBPS": "256",
        },
        cli_overrides={"batch.skip_bitrate_kbps": 192},
    )

    assert config.batch.skip_bitrate_kbps == 192
    assert config.general.log_level_file == "WARNING"


def test_invalid_url_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="slskd.url"):
        load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"slskd.url": "not-a-url"},
        )


def test_secret_values_are_never_in_public_config(tmp_path: Path) -> None:
    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})

    public = config.public_dict()
    assert "SLSKD_API_KEY" in public["slskd"]["api_key_env"]
    assert "value" not in public["slskd"]
