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


def test_load_env_file_supplies_api_keys_and_keeps_real_env_wins(tmp_path: Path) -> None:
    """A local .env feeds ACOUSTID_API_KEY et al. (NFR-6) without overriding real env."""
    from harvester.config import load_env_file

    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "ACOUSTID_API_KEY=from-file\n"
        'SLSKD_API_KEY="quoted-value"\n'
        "export EXTRA_KEY=exported\n"
        "BROKEN LINE\n"
        "\n",
        encoding="utf-8",
    )
    environ = {"ACOUSTID_API_KEY": "from-shell"}

    loaded = load_env_file(env_file, environ=environ)

    assert "ACOUSTID_API_KEY" not in loaded  # shell export wins
    assert environ["ACOUSTID_API_KEY"] == "from-shell"
    assert environ["SLSKD_API_KEY"] == "quoted-value"
    assert environ["EXTRA_KEY"] == "exported"
    assert sorted(loaded) == ["EXTRA_KEY", "SLSKD_API_KEY"]


def test_load_env_file_is_silent_when_missing(tmp_path: Path, monkeypatch) -> None:
    """No .env anywhere → no keys loaded and no exception."""
    from harvester.config import load_env_file

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HARVESTER_DATA_DIR", str(tmp_path / "data"))

    assert load_env_file(tmp_path / "nope.env", environ={}) == []


def test_load_env_file_tops_up_from_less_specific_candidates(
    tmp_path: Path, monkeypatch
) -> None:
    """A key missing from the more specific .env is still found further down."""
    from harvester.config import load_env_file

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ONLY_HERE=local\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / ".env").write_text(
        "ACOUSTID_API_KEY=from-data-dir\nONLY_HERE=ignored\n", encoding="utf-8"
    )
    monkeypatch.setenv("HARVESTER_DATA_DIR", str(data_dir))

    environ: dict[str, str] = {}
    loaded = load_env_file(environ=environ)

    assert environ["ONLY_HERE"] == "local"  # most specific wins
    assert environ["ACOUSTID_API_KEY"] == "from-data-dir"  # topped up from the next file
    assert sorted(loaded) == ["ACOUSTID_API_KEY", "ONLY_HERE"]


def test_processing_defaults_keep_hosted_and_diarize_off(tmp_path: Path) -> None:
    """The hosted path is opt-in: nothing in the config turns it on (D26)."""
    from harvester.processing import DEFAULT_SEP_TYPE

    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})

    assert config.processing.hosted_sep_type == DEFAULT_SEP_TYPE
    assert config.processing.hosted_max_seconds == 0.0
    assert config.processing.diarize_max_seconds == 0.0


def test_processing_hosted_and_diarize_limits_are_read_from_the_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[processing]\n"
        'hosted_sep_type = "mega_53_stem"\n'
        "hosted_max_seconds = 45\n"
        "diarize_max_seconds = 90\n",
        encoding="utf-8",
    )

    config = load_config(config_file, environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})

    assert config.processing.hosted_sep_type == "mega_53_stem"
    assert config.processing.hosted_max_seconds == 45.0
    assert config.processing.diarize_max_seconds == 90.0


def test_negative_processing_limits_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="hosted_max_seconds"):
        load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"processing.hosted_max_seconds": -5},
        )
    with pytest.raises(ConfigError, match="diarize_max_seconds"):
        load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"processing.diarize_max_seconds": -1},
        )


def test_obsidian_defaults_to_disabled(tmp_path: Path) -> None:
    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})

    assert config.obsidian.enabled is False
    assert config.obsidian.vault_dir == Path("~/OmniRip-Vault").expanduser()
    assert config.public_dict()["obsidian"]["enabled"] is False


def test_obsidian_section_is_read_from_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[obsidian]\n"
        "enabled = true\n"
        'vault_dir = "~/My-Vault"\n'
        'library = "Albums"\n',
        encoding="utf-8",
    )

    config = load_config(config_file, environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})

    assert config.obsidian.enabled is True
    assert config.obsidian.vault_dir == Path("~/My-Vault").expanduser()
    assert config.obsidian.library == "Albums"
    assert config.obsidian.wants == "Wants"


def test_processing_genre_defaults_and_validation(tmp_path: Path) -> None:
    """Default genre is auto, subtle intensity; invalid values are rejected."""
    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})
    assert config.processing.genre == "auto"
    assert config.processing.genre_intensity == "subtle"

    # Invalid genre rejected
    with pytest.raises(ConfigError, match="processing.genre must be"):
        load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"processing.genre": "unknown_future_genre"},
        )

    # Invalid intensity rejected
    with pytest.raises(ConfigError, match="processing.genre_intensity must be"):
        load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"processing.genre_intensity": "extreme"},
        )


def test_processing_genre_all_profiles_and_intensities_valid(tmp_path: Path) -> None:
    """auto, mix, and every defined profile and intensity load cleanly."""
    from harvester.analysis.enhancement.genres import GENRE_INTENSITIES, GENRE_PROFILES

    for g in ("auto", "mix", *GENRE_PROFILES):
        cfg = load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"processing.genre": g},
        )
        assert cfg.processing.genre == g

    for intensity in GENRE_INTENSITIES:
        cfg = load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"processing.genre_intensity": intensity},
        )
        assert cfg.processing.genre_intensity == intensity


def test_config_example_matches_genre_keys(tmp_path: Path) -> None:
    """config.example.toml defines genre and genre_intensity and loads validly."""
    example_path = Path("config.example.toml")
    assert example_path.is_file()
    cfg = load_config(example_path, environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})
    assert cfg.processing.genre == "auto"
    assert cfg.processing.genre_intensity == "subtle"
    assert cfg.ui.visual_fidelity == "auto"
    assert cfg.ui.reduced_motion is False


def test_ui_fidelity_and_reduced_motion_override(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[ui]\nvisual_fidelity = "OCTANT"\nreduced_motion = true\n',
        encoding="utf-8",
    )
    cfg = load_config(config_file, environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})
    assert cfg.ui.visual_fidelity == "octant"
    assert cfg.ui.reduced_motion is True


def test_invalid_visual_fidelity_is_rejected(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text('[ui]\nvisual_fidelity = "vhs"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="ui.visual_fidelity"):
        load_config(config_file, environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})


