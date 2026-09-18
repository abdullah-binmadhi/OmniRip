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
