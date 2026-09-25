"""Tests for the guided repair executor (services/repair.py)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from harvester.analysis.enhancement.repair_ops import load_stereo
from harvester.analysis.enhancement.repair_plan import (
    OUTPUT_MASTER,
    RepairPlan,
)
from harvester.services.repair import RepairResult, execute_repair

SR = 48000
DURATION_S = 3.0


def _tone(freq: float, seconds: float = DURATION_S, amp: float = 0.3) -> np.ndarray:
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _band_energy(signal: np.ndarray, lo: float, hi: float, sr: int = SR) -> float:
    spectrum = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(len(signal), 1.0 / sr)
    mask = (freqs >= lo) & (freqs <= hi)
    return float(np.sum(spectrum[mask] ** 2))


def _make_world(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "song.wav"
    vocals = tmp_path / "song_ensemble_vocals.wav"
    inst = tmp_path / "song_ensemble_instrumental.wav"
    vocals_audio = np.stack([_tone(1000.0), _tone(1000.0)])
    inst_audio = np.stack([_tone(220.0), _tone(220.0)])
    mix = (vocals_audio + inst_audio).astype(np.float32)
    sf.write(source, mix.T, SR)
    sf.write(vocals, vocals_audio.T, SR)
    sf.write(inst, inst_audio.T, SR)
    return source, vocals, inst


def test_execute_repair_applies_section_ops_and_writes_three_outputs(tmp_path: Path):
    source, vocals, inst = _make_world(tmp_path)
    calls: list[tuple] = []

    def fake_separate(src, plan, stem_dir, progress):
        calls.append((src, stem_dir))
        return vocals, inst

    plan = RepairPlan(enhance_preset_id="conservative")
    plan.choice("vocal_bleed").enabled = True
    plan.choice("vocal_bleed").ranges = [(1.0, 2.0)]

    out_dir = tmp_path / "out"
    result = execute_repair(
        source,
        plan,
        output_dir=out_dir,
        sample_rate=SR,
        separate=fake_separate,
    )

    assert isinstance(result, RepairResult)
    assert result.master is not None and result.master.exists() and result.master.suffix == ".mp3"
    assert result.vocals is not None and result.vocals.exists()
    assert result.inst is not None and result.inst.exists()
    assert calls and calls[0][0] == source
    assert result.residual_worst_db is not None

    edited_vocals, _ = load_stereo(result.vocals)
    original_vocals, _ = load_stereo(vocals)
    inside = slice(int(1.2 * SR), int(1.3 * SR))
    outside = slice(int(2.3 * SR), int(2.4 * SR))
    assert _band_energy(edited_vocals[0, inside], 300, 3500) < 0.1 * _band_energy(
        original_vocals[0, inside], 300, 3500
    )
    assert _band_energy(edited_vocals[0, outside], 300, 3500) > 0.9 * _band_energy(
        original_vocals[0, outside], 300, 3500
    )

    edited_inst, _ = load_stereo(result.inst)
    original_inst, _ = load_stereo(inst)
    assert np.allclose(edited_inst, original_inst, atol=1e-4)


def test_execute_repair_master_only_skips_separation(tmp_path: Path):
    source, _vocals, _inst = _make_world(tmp_path)
    called = False

    def fake_separate(src, plan, stem_dir, progress):
        nonlocal called
        called = True
        raise AssertionError("separation must not run for a master-only plan")

    plan = RepairPlan(outputs=(OUTPUT_MASTER,), enhance_preset_id="conservative")
    plan.choice("just_enhance").enabled = True

    result = execute_repair(
        source,
        plan,
        output_dir=tmp_path / "out",
        sample_rate=SR,
        separate=fake_separate,
    )
    assert not called
    assert result.master is not None and result.master.exists()
    assert result.vocals is None and result.inst is None


def test_execute_repair_rejects_invalid_plan(tmp_path: Path):
    source, _vocals, _inst = _make_world(tmp_path)
    plan = RepairPlan()
    plan.choice("vocal_bleed").enabled = True
    plan.choice("vocal_bleed").ranges = [(2.0, 1.0)]
    try:
        execute_repair(source, plan, output_dir=tmp_path / "out", sample_rate=SR)
    except ValueError as exc:
        assert "section end must be after start" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_execute_repair_bakes_target_eq_into_the_stems(tmp_path: Path):
    """Vocals/instrumental curves ride on the written stems, not the master."""
    from harvester.analysis.enhancement.eq import (
        EQ_PRESET_BANKS,
        MasteringEQSettings,
        apply_mastering_eq,
    )
    from harvester.analysis.enhancement.repair_ops import load_stereo
    from harvester.analysis.enhancement.repair_plan import OUTPUT_MASTER, RepairPlan

    source, vocals, inst = _make_world(tmp_path)

    def fake_separate(src, plan, stem_dir, progress):
        return vocals, inst

    vocal_eq = MasteringEQSettings()
    vocal_eq.set_band(1000, 6.0)  # deliberately strong so the delta is measurable
    plan = RepairPlan(outputs=(OUTPUT_MASTER, "vocals", "inst"), enhance_preset_id="conservative")
    plan.choice("just_enhance").enabled = True

    result = execute_repair(
        source,
        plan,
        output_dir=tmp_path / "out_eq",
        sample_rate=SR,
        separate=fake_separate,
        eq_by_target={"vocals": vocal_eq},
    )

    assert result.vocals is not None and result.inst is not None
    assert any("Vocals stem EQ applied" in note for note in result.notes)
    original, _ = load_stereo(vocals)
    written, _ = load_stereo(result.vocals)
    expected = apply_mastering_eq(original, vocal_eq, sample_rate=SR)
    assert np.max(np.abs(written - expected)) < 1e-4
    # The instrumental had no curve: it stays a plain copy of the edited stem.
    inst_written, _ = load_stereo(result.inst)
    inst_original, _ = load_stereo(inst)
    assert np.allclose(inst_written, inst_original, atol=1e-4)
    assert EQ_PRESET_BANKS["vocals"]  # bank exists for the UI target

    # The master artifact carries the master curve (and the neutral reconstruction).
    from unittest.mock import MagicMock

    master_eq = MasteringEQSettings()
    master_eq.set_band(16000, 2.5)
    fake_exporter = MagicMock()
    fake_exporter.decode_audio_ffmpeg.return_value = np.zeros((2, SR), dtype=np.float32)
    fake_exporter.render_audio_buffer.side_effect = lambda audio, **kw: np.asarray(audio)
    fake_exporter.encode_mp3_ffmpeg.side_effect = lambda audio, path, **kw: Path(path).write_bytes(
        b"mp3"
    )
    master_result = execute_repair(
        source,
        plan,
        output_dir=tmp_path / "out_master_eq",
        sample_rate=SR,
        separate=fake_separate,
        exporter=fake_exporter,
        eq_by_target={"vocals": vocal_eq, "master": master_eq},
    )
    assert master_result.master is not None and master_result.master.exists()
    assert fake_exporter.render_audio_buffer.call_args.kwargs["eq_settings"] is master_eq


def test_execute_repair_passes_genre_master_preset_and_tags(tmp_path: Path):
    """Genre intent reaches the Repair master render and provenance writer."""
    from unittest.mock import MagicMock

    from harvester.analysis.enhancement.presets import PRESETS

    source, _vocals, _inst = _make_world(tmp_path)
    plan = RepairPlan(outputs=(OUTPUT_MASTER,), enhance_preset_id="conservative")
    plan.choice("just_enhance").enabled = True

    fake_exporter = MagicMock()
    fake_exporter.decode_audio_ffmpeg.return_value = np.zeros((2, SR), dtype=np.float32)
    fake_exporter.render_audio_buffer.side_effect = lambda audio, **_kwargs: np.asarray(audio)
    fake_exporter.encode_mp3_ffmpeg.side_effect = lambda audio, path, **_kwargs: Path(path).write_bytes(
        b"mp3"
    )
    master_preset = PRESETS["conservative"]
    extra_tags = {
        "GENRE": "hip_hop_trap",
        "GENRE_MIX": "Hip-Hop / Trap",
        "GENRE_INTENSITY": "subtle",
    }

    result = execute_repair(
        source,
        plan,
        output_dir=tmp_path / "out_genre",
        sample_rate=SR,
        exporter=fake_exporter,
        master_preset=master_preset,
        extra_tags=extra_tags,
    )

    assert result.master is not None and result.master.exists()
    assert fake_exporter.render_audio_buffer.call_args.kwargs["preset"] is master_preset
    fake_exporter._apply_provenance_tags.assert_called_once()
    assert fake_exporter._apply_provenance_tags.call_args.kwargs["extra_tags"] == extra_tags
