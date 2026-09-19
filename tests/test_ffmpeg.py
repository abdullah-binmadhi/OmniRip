from pathlib import Path

import pytest

from harvester.services.ffmpeg import FfmpegService
from harvester.util.errors import ConfigError


def test_build_mp3_320_arguments() -> None:
    args = FfmpegService.build_transcode_args(
        Path("input.webm"), Path("output.mp3"), mode="mp3-320"
    )

    assert args[-3:] == ["-b:a", "320k", "output.mp3"]
    assert "-map" in args
    assert "0:a:0" in args


def test_build_mp3_v0_arguments() -> None:
    args = FfmpegService.build_transcode_args(Path("input.webm"), Path("output.mp3"), mode="mp3-v0")

    assert args[-3:] == ["-q:a", "0", "output.mp3"]


def test_keep_opus_is_not_an_mp3_transcode() -> None:
    with pytest.raises(ConfigError):
        FfmpegService.build_transcode_args(Path("input.webm"), Path("output.mp3"), mode="keep-opus")


@pytest.mark.asyncio
async def test_probe_audio_info_cache(tmp_path: Path) -> None:
    from harvester.config import load_config

    audio_file = tmp_path / "track.flac"
    audio_file.write_bytes(b"dummy")

    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("")
    svc = FfmpegService(load_config(cfg_path, environ={"HARVESTER_DATA_DIR": str(tmp_path)}))
    fake_json = (
        b'{"format": {"duration": "184.5"}, '
        b'"streams": [{"codec_name": "flac", "sample_rate": "44100", "channels": 2}]}'
    )
    run_calls: list[list[str]] = []

    async def fake_run(command, *, job_id=None, timeout_s=0):
        run_calls.append(command)
        return 0, fake_json, b""

    async def fake_resolve(setting: str) -> list[str]:
        return [setting]

    svc._run = fake_run  # type: ignore[assignment]
    svc._resolve = fake_resolve  # type: ignore[assignment]

    info = await svc.probe_audio_info(audio_file)
    assert info["duration"] == 184.5
    assert info["sample_rate"] == 44100
    assert info["codec"] == "flac"
    assert len(run_calls) == 1

    # Subsequent probe calls hit the in-memory cache without spawning new subprocesses
    dur = await svc.probe_duration(audio_file)
    sr = await svc.probe_sample_rate(audio_file)
    codec = await svc.probe_codec(audio_file)
    assert dur == 184.5
    assert sr == 44100
    assert codec == "flac"
    assert len(run_calls) == 1
