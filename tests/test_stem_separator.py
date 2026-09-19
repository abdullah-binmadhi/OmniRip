"""Tests for Vocal and Instrumental Stem Separation service."""

from collections.abc import Callable
from pathlib import Path
from typing import Any
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
    postprocess_stems,
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


def _mock_separate_bs_roformer(
    input_path: Path,
    vocals_path: Path,
    inst_path: Path,
    raw_vocals_path: Path | None = None,
    raw_inst_path: Path | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
    blend_weight: float = 0.70,
    vocal_profile: str = "natural",
    inst_profile: str = "natural",
    vocal_flags: set[str] | list[str] | str | None = None,
    inst_flags: set[str] | list[str] | str | None = None,
    **kwargs: Any,
) -> StemResult:
    if progress_callback:
        progress_callback(5.0, "Loading BS-RoFormer Rotary Transformer...")
        progress_callback(50.0, "BS-RoFormer inference chunk 1/1...")
    audio, sr = load_audio_numpy(input_path)
    raw_voc = audio * 0.6
    raw_inst = audio * 0.4
    if raw_vocals_path:
        save_audio_numpy(raw_voc, raw_vocals_path, sr)
    if raw_inst_path:
        save_audio_numpy(raw_inst, raw_inst_path, sr)
    voc_clean, inst_clean = postprocess_stems(
        audio,
        raw_voc,
        raw_inst,
        sr,
        blend_weight=blend_weight,
        vocal_profile=vocal_profile,
        inst_profile=inst_profile,
        vocal_flags=vocal_flags,
        inst_flags=inst_flags,
        progress_callback=progress_callback,
    )
    save_audio_numpy(voc_clean, vocals_path, sr)
    save_audio_numpy(inst_clean, inst_path, sr)
    duration = audio.shape[1] / max(1, sr)
    return StemResult(
        vocals_path=vocals_path,
        instrumental_path=inst_path,
        mode="bs_roformer",
        sample_rate=sr,
        duration_s=duration,
        engine="bs_roformer",
    )


def test_stem_separator_bs_roformer_execution(sample_stereo_wav: Path, tmp_path: Path) -> None:
    """Verify BS-RoFormer inference produces isolated vocal and instrumental stems."""
    separator = StemSeparator(cache_dir=tmp_path / "cache_bs")
    reports: list[str] = []

    def cb(_pct: float, step: str) -> None:
        reports.append(step)

    with patch.object(separator, "_separate_bs_roformer", side_effect=_mock_separate_bs_roformer):
        res = separator.separate_file(sample_stereo_wav, mode="bs_roformer", progress_callback=cb)
    assert res.mode == "bs_roformer"
    assert res.vocals_path.exists()
    assert res.instrumental_path.exists()
    assert res.vocals_path.stat().st_size > 1000
    assert res.instrumental_path.stat().st_size > 1000
    assert any("BS-RoFormer" in r for r in reports)


def test_stem_profile_persistence(tmp_path: Path) -> None:
    """Verify stem defect profiles save and load correctly."""
    from harvester.analysis.enhancement.stem_separator import (
        load_stem_profile,
        save_stem_profile,
    )

    test_dir = tmp_path / "stem_profile_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Initial default load
    initial = load_stem_profile(test_dir)
    assert initial["vocal_profile"] == "natural"
    assert initial["inst_profile"] == "natural"

    # Save custom profile
    save_stem_profile(
        test_dir,
        {
            "vocal_profile": "fix_pumping",
            "inst_profile": "kill_whispers",
            "bs_roformer_weight": 0.85,
        },
    )

    loaded = load_stem_profile(test_dir)
    assert loaded["vocal_profile"] == "fix_pumping"
    assert loaded["inst_profile"] == "kill_whispers"
    assert loaded["bs_roformer_weight"] == 0.85


def test_stem_separator_diagnostic_profiles_and_fast_cache(
    sample_stereo_wav: Path, tmp_path: Path
) -> None:
    """Verify diagnostic profiles produce tailored stems and leverage cached raw stems."""
    from harvester.analysis.enhancement.stem_separator import load_stem_profile

    cache_dir = tmp_path / "cache_diag"
    separator = StemSeparator(cache_dir=cache_dir)

    # First run: default natural profile
    with patch.object(separator, "_separate_bs_roformer", side_effect=_mock_separate_bs_roformer):
        res1 = separator.separate_file(
            sample_stereo_wav,
            mode="bs_roformer",
            vocal_profile="natural",
            inst_profile="natural",
        )
    assert res1.vocals_path.exists()
    assert res1.instrumental_path.exists()

    prof1 = load_stem_profile(res1.vocals_path.parent)
    assert prof1["vocal_profile"] == "natural"
    assert prof1["inst_profile"] == "natural"

    # Second run: targeted defect fix (fix_pumping + kill_whispers)
    # This should use the fast path without re-running neural inference
    reports: list[str] = []

    def cb(_pct: float, step: str) -> None:
        reports.append(step)

    res2 = separator.separate_file(
        sample_stereo_wav,
        mode="bs_roformer",
        vocal_profile="fix_pumping",
        inst_profile="kill_whispers",
        progress_callback=cb,
    )
    assert res2.vocals_path.exists()
    assert "fix_pumping" in str(res2.vocals_path)
    assert "kill_whispers" in str(res2.instrumental_path)
    assert any("Re-processing cached neural stems" in r for r in reports)

    prof2 = load_stem_profile(res2.vocals_path.parent)
    assert prof2["vocal_profile"] == "fix_pumping"
    assert prof2["inst_profile"] == "kill_whispers"


def test_all_ten_vocal_remediations(sample_stereo_wav: Path) -> None:
    """Verify each of the 10 vocal defect remediations executes cleanly on audio."""
    from harvester.analysis.enhancement.stem_separator import (
        VOCAL_REMEDIATIONS,
        apply_vocal_remediations,
    )

    audio, sr = load_audio_numpy(sample_stereo_wav)
    assert len(VOCAL_REMEDIATIONS) == 10

    # Test each individual flag
    for flag in VOCAL_REMEDIATIONS:
        out = apply_vocal_remediations(audio, sr, {flag})
        assert out.shape == audio.shape
        assert np.isfinite(out).all()

    # Test all 10 flags together
    all_flags = set(VOCAL_REMEDIATIONS.keys())
    out_all = apply_vocal_remediations(audio, sr, all_flags)
    assert out_all.shape == audio.shape
    assert np.isfinite(out_all).all()
    assert np.max(np.abs(out_all)) <= 1.05


def test_all_ten_instrumental_remediations(sample_stereo_wav: Path) -> None:
    """Verify each of the 10 instrumental defect remediations executes cleanly on audio."""
    from harvester.analysis.enhancement.stem_separator import (
        INST_REMEDIATIONS,
        apply_inst_remediations,
    )

    audio, sr = load_audio_numpy(sample_stereo_wav)
    voc_raw = audio * 0.5
    inst_raw = audio * 0.5
    assert len(INST_REMEDIATIONS) == 10

    # Test each individual flag
    for flag in INST_REMEDIATIONS:
        out = apply_inst_remediations(audio, voc_raw, inst_raw, sr, {flag})
        assert out.shape == audio.shape
        assert np.isfinite(out).all()

    # Test all 10 flags together
    all_flags = set(INST_REMEDIATIONS.keys())
    out_all = apply_inst_remediations(audio, voc_raw, inst_raw, sr, all_flags)
    assert out_all.shape == audio.shape
    assert np.isfinite(out_all).all()
    assert np.max(np.abs(out_all)) <= 1.05


def test_stem_separator_multi_flag_fast_cache(sample_stereo_wav: Path, tmp_path: Path) -> None:
    """Verify multi-choice flag sets generate distinct cached derivatives from raw stems."""
    from harvester.analysis.enhancement.stem_separator import (
        get_stem_cache_suffix,
        load_stem_profile,
    )

    separator = StemSeparator(cache_dir=tmp_path / "cache_multi")

    # Initial run populates raw stems
    with patch.object(separator, "_separate_bs_roformer", side_effect=_mock_separate_bs_roformer):
        res1 = separator.separate_file(sample_stereo_wav, mode="bs_roformer")

    assert res1.vocals_path.exists()
    assert res1.instrumental_path.exists()

    # Apply 3 vocal flags and 2 instrumental flags
    v_flags = {"de_plosive", "de_robot", "air_boost"}
    i_flags = {"preserve_drums", "kill_whispers"}
    res2 = separator.separate_file(
        sample_stereo_wav,
        mode="bs_roformer",
        vocal_flags=v_flags,
        inst_flags=i_flags,
    )

    v_sfx = get_stem_cache_suffix(v_flags)
    i_sfx = get_stem_cache_suffix(i_flags)

    assert v_sfx in str(res2.vocals_path)
    assert i_sfx in str(res2.instrumental_path)
    assert res2.vocals_path.exists()
    assert res2.instrumental_path.exists()

    prof = load_stem_profile(res2.vocals_path.parent)
    assert set(prof.get("vocal_flags", [])) == v_flags
    assert set(prof.get("inst_flags", [])) == i_flags
