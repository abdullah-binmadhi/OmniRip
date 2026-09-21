"""Tests for Layer Studio Editor — per-second surgical stem editing (M2)."""

from __future__ import annotations

import numpy as np
import pytest

from harvester.analysis.enhancement.layer_editor import (
    EditPlan,
    apply_drum_punch,
    apply_op,
    commit_edit_plan,
    render_edited_layer,
    save_pcm32,
)
from harvester.analysis.enhancement.layers import (
    LayerTrack,
    build_layer_sources,
    build_layer_track,
)
from harvester.analysis.enhancement.stem_separator import save_audio_numpy


def _sine_stereo(sr: int = 44100, dur_s: float = 3.0, freq_hz: float = 1000.0,
                 gain: float = 0.5) -> np.ndarray:
    t = np.linspace(0, dur_s, int(sr * dur_s), endpoint=False, dtype=np.float32)
    sig = gain * np.sin(2 * np.pi * freq_hz * t, dtype=np.float32)
    return np.stack([sig, sig], axis=0)


def _write_sources(stem_dir, suffix: str, sr: int = 44100, dur_s: float = 3.0) -> None:
    for name in ("vocals", "bass", "drums", "other"):
        save_audio_numpy(_sine_stereo(sr, dur_s, 440.0, 0.5), stem_dir / f"{suffix}_raw_{name}.wav", sr)
        save_audio_numpy(_sine_stereo(sr, dur_s, 60.0, 0.5), stem_dir / f"{suffix}_raw_{name}_hdemucs.wav", sr)


def test_edit_plan_toggle_ops() -> None:
    plan = EditPlan()
    assert plan.count == 0
    plan.add("bass", 2, "mute")
    assert plan.count == 1
    assert plan.get("bass", 2) == "mute"
    # Toggling the same op clears it
    plan.add("bass", 2, "mute")
    assert plan.count == 0
    # Reset removes regardless of op
    plan.add("bass", 2, "mute")
    plan.add("bass", 2, "reset")
    assert plan.count == 0
    # Unknown op rejected
    with pytest.raises(ValueError):
        plan.add("bass", 1, "not_an_op")


def test_apply_op_mute_and_band_ops() -> None:
    seg = _sine_stereo(44100, 1.0, 1000.0, 0.5)
    muted = apply_op(seg, "mute", 44100)
    assert np.max(np.abs(muted)) == 0.0

    de_bleed = apply_op(seg, "de_bleed", 44100)
    assert de_bleed.shape == seg.shape
    assert np.isfinite(de_bleed).all()

    de_ess = apply_op(seg, "de_ess", 44100)
    assert np.isfinite(de_ess).all()

    de_mud = apply_op(seg, "de_mud", 44100)
    assert np.isfinite(de_mud).all()

    punch = apply_drum_punch(seg, 44100)
    assert punch.shape == seg.shape
    assert np.isfinite(punch).all()


def test_apply_op_band_attenuates_band_energy() -> None:
    """De-mud on a 300Hz tone must cut low-mid band energy vs the original."""
    sr = 44100
    seg = _sine_stereo(sr, 1.0, 300.0, 0.5)

    def band_db(audio: np.ndarray, band: tuple[float, float]) -> float:
        mono = audio.mean(axis=0)
        n = mono.shape[0]
        mag = np.abs(np.fft.rfft(mono))
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        mask = (freqs >= band[0]) & (freqs <= band[1])
        return float(20.0 * np.log10(np.mean(mag[mask]) + 1e-9))

    orig_db = band_db(seg, (250.0, 350.0))
    mud_db = band_db(apply_op(seg, "de_mud", sr), (250.0, 350.0))
    assert mud_db < orig_db - 6.0

    # De-ess on an 8kHz tone must cut sibilance band energy
    seg_hi = _sine_stereo(sr, 1.0, 8000.0, 0.5)
    orig_hi = band_db(seg_hi, (5500.0, 8500.0))
    ess_hi = band_db(apply_op(seg_hi, "de_ess", sr), (5500.0, 8500.0))
    assert ess_hi < orig_hi - 6.0


def test_render_edited_layer_only_touches_edited_segments() -> None:
    """Neighbour segments survive the edit byte-for-byte (infinity-norm zero)."""
    sr = 44100
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        fp = Path(d) / "layer_bass.wav"
        audio = _sine_stereo(sr, 3.0, 440.0, 0.5)
        save_audio_numpy(audio, fp, sr)
        import soundfile as sf

        # Reference = what render_edited_layer actually reads (16-bit quantized)
        ref, _ = sf.read(str(fp), dtype="float32", always_2d=True)
        ref = ref.T

        rendered = render_edited_layer(fp, [(1, "mute")], sample_rate=sr)
        seg_len = sr
        fade_n = int(0.02 * sr)
        # Segment 1 silent in the middle (20ms tail fades at each edge)
        assert np.max(np.abs(rendered[:, seg_len + fade_n:2 * seg_len - fade_n])) < 1e-5
        # Crossfade head/tail start exactly at the original signal, so the
        # boundary samples equal the untouched neighbouring samples (no click).
        assert np.array_equal(rendered[:, seg_len], ref[:, seg_len])
        assert np.array_equal(rendered[:, 2 * seg_len - 1], ref[:, 2 * seg_len - 1])
        # Segments 0 and 2 byte-identical to the audio actually read
        assert np.array_equal(rendered[:, :seg_len], ref[:, :seg_len])
        assert np.array_equal(rendered[:, 2 * seg_len:], ref[:, 2 * seg_len:])


def test_commit_edit_plan_writes_and_rebuilds(tmp_path) -> None:
    """Full M2 flow: stage mute + drum-punch, commit, rebuild shows muted cell."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_bs_roformer"
    _write_sources(stem_dir, suffix, sr=sr, dur_s=3.0)

    sources = build_layer_sources(stem_dir, "song", "bs_roformer", sample_rate=sr)
    plan = EditPlan()
    lanes = set(sources)
    # Song-detected lanes: bass carries sub + body content, so it splits.
    assert {"vocals", "other"} <= lanes
    assert {"sub_bass", "bass"} <= lanes
    assert len(lanes) > 4
    bass_lane = next(name for name in ("bass", "sub_bass") if name in sources)
    drum_lane = next(name for name in ("drums", "kick", "snare", "hats") if name in sources)
    plan.add(bass_lane, 1, "mute")
    plan.add(drum_lane, 0, "drum_punch")
    written = commit_edit_plan(plan, sources, sample_rate=sr)
    assert set(written) == {bass_lane, drum_lane}

    # Committed layer files now carry the edits
    import soundfile as sf

    bass, _ = sf.read(str(written[bass_lane]), dtype="float32", always_2d=True)
    bass = bass.T
    fade_n = int(0.02 * sr)
    splat = bass[:, sr + fade_n:2 * sr - fade_n]
    assert np.max(np.abs(splat)) < 1e-3

    # Rebuilding the timeline reflects the muted cell: level plummets vs the
    # neighbouring unedited cells (residual ~ the 20ms crossfade fades only).
    track: LayerTrack = build_layer_track(
        stem_dir, "song", "bs_roformer", duration_s=3.0, sample_rate=sr
    )
    bass_src = track.sources[bass_lane]
    assert bass_src.level(1) < bass_src.level(0) - 0.2
    assert bass_src.level(1) < bass_src.level(2) - 0.2
    # Committing edits never changes the detected lane set (cached lane files).
    assert set(track.active_layers) == lanes


def test_commit_empty_and_missing_layer(tmp_path) -> None:
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    _write_sources(stem_dir, "song_bs_roformer", sr=sr, dur_s=2.0)
    sources = build_layer_sources(stem_dir, "song", "bs_roformer", sample_rate=sr)

    assert commit_edit_plan(EditPlan(), sources, sample_rate=sr) == {}

    plan = EditPlan()
    plan.add("nonexistent", 0, "mute")
    with pytest.raises(ValueError, match="nonexistent"):
        commit_edit_plan(plan, sources, sample_rate=sr)


def test_save_pcm32_writes_32bit_wav(tmp_path) -> None:
    """Exported layer WAVs are 32-bit PCM and respect the -1dBFS ceiling."""
    sr = 44100
    out = tmp_path / "exported.wav"
    audio = _sine_stereo(sr, 1.0, 440.0, 1.2)  # would clip before limiter
    save_pcm32(audio, out, sr)

    import soundfile as sf

    info = sf.info(str(out))
    assert info.subtype == "PCM_32"
    data, _ = sf.read(str(out), dtype="float32", always_2d=True)
    assert float(np.max(np.abs(data))) <= 10.0 ** (-1.0 / 20.0) + 1e-6


def test_apply_op_surgical_expansions() -> None:
    sr = 44100
    # 1. de_hum: 55 Hz sine tone attenuated
    hum_tone = _sine_stereo(sr, 1.0, 55.0, 0.5)
    dehummed = apply_op(hum_tone, "de_hum", sr)
    hum_orig_rms = float(np.sqrt(np.mean(hum_tone ** 2)))
    hum_out_rms = float(np.sqrt(np.mean(dehummed ** 2)))
    assert hum_out_rms < hum_orig_rms * 0.4

    # 2. air_boost: 14 kHz sine tone boosted
    air_tone = _sine_stereo(sr, 1.0, 14000.0, 0.2)
    boosted = apply_op(air_tone, "air_boost", sr)
    air_orig_rms = float(np.sqrt(np.mean(air_tone ** 2)))
    air_out_rms = float(np.sqrt(np.mean(boosted ** 2)))
    assert air_out_rms > air_orig_rms * 1.2

    # 3. de_click: isolated Dirac impulse spike gets smoothed
    click_tone = _sine_stereo(sr, 0.1, 440.0, 0.05)
    click_tone[:, int(sr * 0.05)] = 0.95
    declicked = apply_op(click_tone, "de_click", sr)
    assert np.max(np.abs(declicked)) < 0.7

    # 4. noise_gate: signal below -38 dBFS (0.005 ~= -46 dBFS) is attenuated
    noise = _sine_stereo(sr, 0.5, 1000.0, 0.005)
    gated = apply_op(noise, "noise_gate", sr)
    assert np.max(np.abs(gated)) < 0.002

    # 5. transient_tame: loud peaks above 0.7 are compressed smoothly
    loud = _sine_stereo(sr, 0.5, 440.0, 0.95)
    tamed = apply_op(loud, "transient_tame", sr)
    assert np.max(np.abs(tamed)) < 0.95
    assert np.isfinite(tamed).all()