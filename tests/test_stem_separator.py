"""Tests for Vocal and Instrumental Stem Separation service."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from harvester.analysis.enhancement.stem_separator import (
    StemResult,
    StemSeparator,
    apply_adaptive_spectral_gate,
    apply_inversion_subtraction,
    apply_vocal_harmonic_polish,
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
    """Test that neural separation raises RuntimeError when both AI models fail.

    Since eco-DSP fallback was removed (user decision: surface error instead),
    both BS-RoFormer and HDEMUCS failing must propagate as a clear RuntimeError.
    """
    separator = StemSeparator(cache_dir=tmp_path / "cache")
    with (
        patch.object(
            separator, "_separate_bs_roformer", side_effect=RuntimeError("HF unavailable")
        ),
        patch.object(separator, "_separate_neural", side_effect=RuntimeError("CUDA OOM")),
        pytest.raises(RuntimeError, match="BS-RoFormer and HDEMUCS are unavailable"),
    ):
        separator.separate_file(sample_stereo_wav, mode="neural")


def test_stem_separator_bs_roformer_fallback_to_hdemucs(
    sample_stereo_wav: Path, tmp_path: Path
) -> None:
    """Test that BS-RoFormer failure falls back to HDEMUCS when available."""
    separator = StemSeparator(cache_dir=tmp_path / "cache")
    mock_res = StemResult(
        vocals_path=tmp_path / "vocals.wav",
        instrumental_path=tmp_path / "inst.wav",
        mode="hdemucs",
        sample_rate=44100,
        duration_s=1.0,
    )
    with (
        patch.object(
            separator, "_separate_bs_roformer", side_effect=RuntimeError("transformers missing")
        ),
        patch.object(separator, "_separate_neural", return_value=mock_res),
    ):
        res = separator.separate_file(sample_stereo_wav, mode="neural")
        assert res.mode == "hdemucs"


def test_apply_adaptive_spectral_gate_suppresses_pause() -> None:
    """Verify adaptive spectral gate attenuates inter-phrase noise floor with smooth envelope."""
    sr = 44100
    t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
    sig = np.zeros_like(t)
    sig[:sr] = 0.5 * np.sin(2 * np.pi * 1000 * t[:sr])
    sig[sr:] = 0.005 * np.random.default_rng(42).standard_normal(sr).astype(np.float32)
    stereo = np.stack([sig, sig], axis=0)

    gated = apply_adaptive_spectral_gate(stereo, sr)
    steady_pause_orig = float(np.sqrt(np.mean(stereo[:, int(sr * 1.4) :] ** 2)))
    steady_pause_gated = float(np.sqrt(np.mean(gated[:, int(sr * 1.4) :] ** 2)))
    assert steady_pause_gated < steady_pause_orig * 0.25


def test_apply_vocal_harmonic_polish() -> None:
    """Verify vocal harmonic polish smooths isolated phase smearing."""
    sr = 44100
    t = np.linspace(0, 0.5, sr // 2, endpoint=False, dtype=np.float32)
    vocal = 0.4 * np.sin(2 * np.pi * 440 * t)
    stereo = np.stack([vocal, vocal], axis=0)

    polished = apply_vocal_harmonic_polish(stereo, sr)
    assert polished.shape == stereo.shape
    assert np.max(np.abs(polished)) > 0.1


def test_apply_inversion_subtraction() -> None:
    """Verify phase-inversion subtraction extracts instrumental backing."""
    sr = 44100
    t = np.linspace(0, 0.5, sr // 2, endpoint=False, dtype=np.float32)
    sub_bass = 0.4 * np.sin(2 * np.pi * 60 * t)
    lead_vocal = 0.3 * np.sin(2 * np.pi * 1000 * t)
    mix = np.stack([sub_bass + lead_vocal, sub_bass + lead_vocal], axis=0)
    voc = np.stack([lead_vocal, lead_vocal], axis=0)

    inst = apply_inversion_subtraction(mix, voc, sr)
    assert inst.shape == mix.shape
    assert np.max(np.abs(inst)) > 0.2


def test_stem_separator_progress_callback(sample_stereo_wav: Path, tmp_path: Path) -> None:
    """Verify progress callback reports steps and percentages monotonically."""
    reports: list[tuple[float, str]] = []

    def cb(pct: float, step: str) -> None:
        reports.append((pct, step))

    separator = StemSeparator(cache_dir=tmp_path / "cache_cb")
    separator.separate_file(sample_stereo_wav, mode="eco", progress_callback=cb)

    assert len(reports) >= 3
    assert reports[0][0] <= 20.0
    assert reports[-1][0] == 100.0


def test_stem_separator_multi_song_cache_isolation(tmp_path: Path) -> None:
    """Verify different songs maintain isolated caches without collisions."""
    sr = 44100
    t = np.linspace(0, 0.5, sr // 2, endpoint=False, dtype=np.float32)

    song_a_path = tmp_path / "song_a.wav"
    song_b_path = tmp_path / "song_b.wav"

    save_audio_numpy(np.stack([0.4 * np.sin(2 * np.pi * 400 * t)] * 2, axis=0), song_a_path, sr)
    save_audio_numpy(np.stack([0.4 * np.sin(2 * np.pi * 800 * t)] * 2, axis=0), song_b_path, sr)

    cache_dir = tmp_path / "cache_isolation"
    separator = StemSeparator(cache_dir=cache_dir)

    res_a = separator.separate_file(song_a_path, mode="eco")
    res_b = separator.separate_file(song_b_path, mode="eco")

    assert res_a.vocals_path != res_b.vocals_path
    assert res_a.vocals_path.parent != res_b.vocals_path.parent
    assert res_a.vocals_path.exists()
    assert res_b.vocals_path.exists()


def test_stem_separator_bs_roformer_execution(sample_stereo_wav: Path, tmp_path: Path) -> None:
    """Verify BS-RoFormer inference produces isolated vocal and instrumental stems."""
    separator = StemSeparator(cache_dir=tmp_path / "cache_bs")
    reports: list[str] = []

    def cb(_pct: float, step: str) -> None:
        reports.append(step)

    res = separator.separate_file(sample_stereo_wav, mode="bs_roformer", progress_callback=cb)
    assert res.mode == "bs_roformer"
    assert res.vocals_path.exists()
    assert res.instrumental_path.exists()
    assert res.vocals_path.stat().st_size > 1000
    assert res.instrumental_path.stat().st_size > 1000
    assert any("BS-RoFormer" in r for r in reports)
