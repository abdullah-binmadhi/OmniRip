"""Tests for song-driven dynamic lane detection (dynamic_layers.py)."""

from __future__ import annotations

import numpy as np

from harvester.analysis.enhancement.dynamic_layers import (
    FAMILY_SPLITS,
    PRESENCE_MIN_RATIO,
    apply_lane_path,
    expand_dynamic_lanes,
    is_present,
    lane_envelope,
    lane_presence,
)
from harvester.analysis.enhancement.stem_separator import save_audio_numpy

SR = 44100


def _tone(freqs: dict[float, float], dur_s: float = 4.0, sr: int = SR) -> np.ndarray:
    """Stereo tone bed: {frequency_hz: gain} summed across the whole file."""
    n = int(sr * dur_s)
    t = np.linspace(0, dur_s, n, endpoint=False, dtype=np.float64)
    sig = np.zeros(n, dtype=np.float64)
    for freq, gain in freqs.items():
        sig += gain * np.sin(2 * np.pi * freq * t)
    stereo = np.stack([sig, sig]).astype(np.float32)
    return np.clip(stereo, -1.0, 1.0)


def _write(path, audio: np.ndarray, sr: int = SR) -> None:
    save_audio_numpy(audio, path, sr)


def test_lane_path_partitions_the_parent_signal() -> None:
    """Kick + snare + hats sum back to the drums stem (mix-invariant split)."""
    drums = _tone({60.0: 0.4, 900.0: 0.3, 9000.0: 0.2})
    specs = {spec.name: spec for spec in FAMILY_SPLITS["drums"]}

    kick = apply_lane_path(drums, SR, specs["kick"].splits)
    snare = apply_lane_path(drums, SR, specs["snare"].splits)
    hats = apply_lane_path(drums, SR, specs["hats"].splits)

    total = kick + snare + hats
    residual = np.abs(total - drums).max()
    assert residual < 1e-3, f"lane partition leaked {residual:.5f}"

    # Each lane actually carries its own band.
    assert lane_envelope(kick, SR).mean() > -12.0
    assert lane_envelope(snare, SR).mean() > -20.0
    assert lane_envelope(hats, SR).mean() > -25.0
    # …and none of them carries the others' content.
    assert lane_envelope(hats, SR).mean() < lane_envelope(kick, SR).mean()


def test_presence_gate_rejects_absent_lanes() -> None:
    """Pure sub content is "kick only": the cymbal lanes read as absent."""
    kick_only = _tone({60.0: 0.6})
    specs = {spec.name: spec for spec in FAMILY_SPLITS["drums"]}

    assert is_present(apply_lane_path(kick_only, SR, specs["kick"].splits), SR) is True
    assert is_present(apply_lane_path(kick_only, SR, specs["snare"].splits), SR) is False
    assert is_present(apply_lane_path(kick_only, SR, specs["hats"].splits), SR) is False

    silence = np.zeros((2, SR), dtype=np.float32)
    active, mean_db = lane_presence(silence, SR)
    assert active < PRESENCE_MIN_RATIO
    assert mean_db <= -50.0


def test_expand_dynamic_lanes_splits_drums_and_bass(tmp_path) -> None:
    """A full-band song yields kick/snare/hats plus sub_bass/bass lanes on disk."""
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_ensemble"
    _write(stem_dir / f"{suffix}_layer_drums.wav", _tone({60.0: 0.4, 900.0: 0.3, 9000.0: 0.2}))
    _write(stem_dir / f"{suffix}_layer_bass.wav", _tone({45.0: 0.4, 150.0: 0.3}))
    _write(stem_dir / f"{suffix}_layer_vocals.wav", _tone({800.0: 0.3}))
    _write(stem_dir / f"{suffix}_layer_other.wav", _tone({2000.0: 0.2}))

    sources = {
        "vocals": stem_dir / f"{suffix}_layer_vocals.wav",
        "drums": stem_dir / f"{suffix}_layer_drums.wav",
        "bass": stem_dir / f"{suffix}_layer_bass.wav",
        "other": stem_dir / f"{suffix}_layer_other.wav",
    }
    lanes, report = expand_dynamic_lanes(sources, sample_rate=SR, stem_dir=stem_dir, suffix=suffix)

    assert set(lanes) == {"vocals", "kick", "snare", "hats", "sub_bass", "bass", "other"}
    assert report.splits["drums"] == ("kick", "snare", "hats")
    assert report.splits["bass"] == ("sub_bass", "bass")
    assert "drums → kick/snare/hats" in report.summary()
    for name in ("kick", "snare", "hats", "sub_bass", "bass"):
        path = lanes[name]
        assert path.exists() and path.stat().st_size > 44, name
    # The upper bass half uses its own file token so the parent is never clobbered.
    assert lanes["bass"].name == f"{suffix}_layer_bass_upper.wav"
    assert sources["bass"].exists()


def test_expand_dynamic_lanes_keeps_family_whole_when_a_child_is_silent(tmp_path) -> None:
    """A drum stem with no cymbal content stays a single drums lane."""
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_ensemble"
    _write(stem_dir / f"{suffix}_layer_drums.wav", _tone({60.0: 0.5, 200.0: 0.2}))
    sources = {"drums": stem_dir / f"{suffix}_layer_drums.wav"}

    lanes, report = expand_dynamic_lanes(sources, sample_rate=SR, stem_dir=stem_dir, suffix=suffix)

    assert set(lanes) == {"drums"}
    assert report.kept_whole == ("drums",)
    assert report.summary() == "drums (whole)"
    assert not (stem_dir / f"{suffix}_layer_hats.wav").exists()


def test_expand_dynamic_lanes_picks_up_neural_extra_lanes(tmp_path) -> None:
    """An extra raw source in the stem dir (e.g. guitar from a 6-source model)
    becomes a first-class lane."""
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_ensemble"
    _write(stem_dir / f"{suffix}_raw_guitar.wav", _tone({1500.0: 0.3}))
    sources = {"vocals": stem_dir / f"{suffix}_layer_vocals.wav"}
    _write(sources["vocals"], _tone({800.0: 0.3}))

    lanes, report = expand_dynamic_lanes(sources, sample_rate=SR, stem_dir=stem_dir, suffix=suffix)

    assert "guitar" in lanes
    assert report.extras == ("guitar",)
    assert "+guitar" in report.summary()


def test_expand_dynamic_lanes_reuses_cached_child_files(tmp_path) -> None:
    """Rebuilds reuse the child lane WAVs (committed edits survive a rebuild)."""
    from harvester.analysis.enhancement.stem_separator import load_audio_numpy

    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_ensemble"
    parent = stem_dir / f"{suffix}_layer_drums.wav"
    _write(parent, _tone({60.0: 0.4, 900.0: 0.3, 9000.0: 0.2}))

    first, _ = expand_dynamic_lanes({"drums": parent}, sample_rate=SR, stem_dir=stem_dir, suffix=suffix)
    kick_path = first["kick"]
    # Simulate a committed surgical edit by rewriting the cached lane quietly.
    _write(kick_path, _tone({60.0: 0.02}))

    second, _ = expand_dynamic_lanes({"drums": parent}, sample_rate=SR, stem_dir=stem_dir, suffix=suffix)

    assert second["kick"] == kick_path
    rebuilt, _sr = load_audio_numpy(kick_path, target_sr=SR)
    assert lane_envelope(rebuilt, SR).mean() < -30.0  # edit survived, not re-derived


def test_lane_envelope_reports_per_second_levels() -> None:
    """A loud first second and a quiet second show up in the lane envelope."""
    audio = _tone({500.0: 0.8}, dur_s=2.0)
    audio[:, SR:] *= 0.01
    env = lane_envelope(audio, SR, segment_size_s=1.0)
    assert env.shape == (2,)
    assert env[0] > env[1]
