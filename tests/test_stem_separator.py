"""Tests for Vocal and Instrumental Stem Separation service."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from harvester.analysis.enhancement.stem_separator import (
    StemResult,
    StemSeparator,
    load_audio_numpy,
    save_audio_numpy,
)


@pytest.fixture
def sample_stereo_wav(tmp_path: Path) -> Path:
    """Create a 1.0-second 44.1kHz synthetic stereo WAV with center vocal and stereo reverb."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)

    # Center vocal at 1000 Hz
    vocal = 0.5 * np.sin(2 * np.pi * 1000 * t)
    # Stereo instrument at 300 Hz (out of phase)
    inst_l = 0.3 * np.sin(2 * np.pi * 300 * t)
    inst_r = -0.3 * np.sin(2 * np.pi * 300 * t)

    stereo = np.stack([vocal + inst_l, vocal + inst_r], axis=0)
    audio_path = tmp_path / "test_track.wav"
    save_audio_numpy(stereo, audio_path, sr)
    return audio_path


def test_stem_separator_eco_mode(sample_stereo_wav: Path, tmp_path: Path) -> None:
    """Test Eco DSP stem separation splits audio into vocals and instrumental."""
    out_dir = tmp_path / "stems_output"
    separator = StemSeparator(cache_dir=tmp_path / "cache")

    result: StemResult = separator.separate_file(sample_stereo_wav, output_dir=out_dir, mode="eco")

    assert result.vocals_path.exists()
    assert result.instrumental_path.exists()
    assert result.vocals_path.stat().st_size > 1000
    assert result.instrumental_path.stat().st_size > 1000
    assert result.mode == "eco"
    assert result.duration_s > 0.9

    # Verify vocal energy in instrumental is attenuated compared to vocals
    v_audio, _ = load_audio_numpy(result.vocals_path)
    i_audio, _ = load_audio_numpy(result.instrumental_path)

    # Vocals audio should have prominent center energy
    assert np.max(np.abs(v_audio)) > 0.05
    assert np.max(np.abs(i_audio)) > 0.05


def test_stem_separator_caching(sample_stereo_wav: Path, tmp_path: Path) -> None:
    """Test that subsequent requests for the same track reuse cached stem files."""
    out_dir = tmp_path / "stems_cache_test"
    separator = StemSeparator(cache_dir=tmp_path / "cache")

    res1 = separator.separate_file(sample_stereo_wav, output_dir=out_dir, mode="eco")
    mtime1 = res1.vocals_path.stat().st_mtime

    # Call again with same file
    res2 = separator.separate_file(sample_stereo_wav, output_dir=out_dir, mode="eco")
    mtime2 = res2.vocals_path.stat().st_mtime

    assert res1.vocals_path == res2.vocals_path
    assert mtime1 == mtime2


def test_stem_separator_file_not_found(tmp_path: Path) -> None:
    """Test FileNotFoundError when source file does not exist."""
    separator = StemSeparator()
    with pytest.raises(FileNotFoundError):
        separator.separate_file(tmp_path / "non_existent.wav")


def test_stem_separator_neural_fallback(sample_stereo_wav: Path, tmp_path: Path) -> None:
    """Test that neural separation failure gracefully falls back to Eco DSP mode."""
    separator = StemSeparator(cache_dir=tmp_path / "cache")
    with patch.object(separator, "_separate_neural", side_effect=RuntimeError("CUDA OOM")):
        res = separator.separate_file(sample_stereo_wav, mode="neural")
        assert res.mode == "eco"
        assert res.vocals_path.exists()
        assert res.instrumental_path.exists()
