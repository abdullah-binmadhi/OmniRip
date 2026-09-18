"""Config persistence tests for the first-run notice (docs/08 §2)."""

from __future__ import annotations

from harvester.config import load_config, persist_first_run_acceptance


def _config(tmp_path, config_file):
    return load_config(
        config_file,
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
    )


def test_persist_creates_missing_file(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config = _config(tmp_path, config_file)

    persist_first_run_acceptance(config)

    assert config_file.exists()
    assert "first_run_notice_accepted = true" in config_file.read_text(encoding="utf-8")


def test_persist_replaces_existing_value(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[general]\noutput_dir = \"/music\"\nfirst_run_notice_accepted = false\n",
        encoding="utf-8",
    )
    config = _config(tmp_path, config_file)

    persist_first_run_acceptance(config)

    text = config_file.read_text(encoding="utf-8")
    assert "first_run_notice_accepted = true" in text
    assert "output_dir = \"/music\"" in text  # other settings preserved


def test_persist_inserts_missing_key_under_general(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[general]\noutput_dir = \"/music\"\n", encoding="utf-8")
    config = _config(tmp_path, config_file)

    persist_first_run_acceptance(config)

    text = config_file.read_text(encoding="utf-8")
    assert "first_run_notice_accepted = true" in text
    assert text.index("first_run_notice_accepted") > text.index("[general]")


def test_persist_appends_general_section_when_missing(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[batch]\nskip_bitrate_kbps = 200\n", encoding="utf-8")
    config = _config(tmp_path, config_file)

    persist_first_run_acceptance(config)

    text = config_file.read_text(encoding="utf-8")
    assert "[general]" in text
    assert "first_run_notice_accepted = true" in text


def test_persisted_flag_is_reloaded(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config = _config(tmp_path, config_file)

    persist_first_run_acceptance(config)
    reloaded = _config(tmp_path, config_file)

    assert reloaded.general.first_run_notice_accepted is True