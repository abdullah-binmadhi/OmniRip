"""Tests for EnhancementExporter and Presets (Milestone 10-D)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
from mutagen.id3 import ID3

from harvester.analysis.enhancement.presets import PRESETS
from harvester.services.enhancement.exporter import EnhancementExporter


def test_presets_coverage():
    """Verify all 5 planned presets exist and have valid attributes."""
    expected = ["conservative", "fast_balanced", "de_sizzle", "extended_air", "narrow_stereo"]
    for key in expected:
        assert key in PRESETS
        preset = PRESETS[key]
        assert preset.id == key
        assert preset.ceiling_dbfs <= 0.0
        assert preset.residual_stereo_width <= 1.0


def test_render_audio_buffer_all_presets():
    """Verify render_audio_buffer produces valid audio for every preset."""
    exporter = EnhancementExporter()
    sr = 48000
    n = 24000
    # Stereo input signal
    audio_in = np.random.normal(0, 0.2, (2, n)).astype(np.float32)

    for _preset_name, preset in PRESETS.items():
        out = exporter.render_audio_buffer(
            audio_in, preset=preset, cutoff_hz=15000.0, sample_rate=sr
        )
        assert out.shape == (2, n)
        # Peak must not exceed ceiling
        ceiling_linear = 10.0 ** (preset.ceiling_dbfs / 20.0)
        assert np.max(np.abs(out)) <= ceiling_linear + 1e-4


def test_apply_provenance_tags(tmp_path: Path):
    """Verify that ID3 provenance tags are correctly added to MP3 derivative."""
    exporter = EnhancementExporter()

    source_path = tmp_path / "original_track.mp3"
    target_path = tmp_path / "original_track.enhanced.mp3"

    # Create dummy files
    source_path.write_bytes(b"dummy_mp3_data")
    target_path.write_bytes(b"dummy_mp3_data")

    preset = PRESETS["fast_balanced"]
    exporter._apply_provenance_tags(source_path, target_path, preset)

    # Read tags back from disk
    saved_id3 = ID3(target_path)
    frames = {f.desc: f.text[0] for f in saved_id3.getall("TXXX")}
    assert frames.get("DERIVED_FROM_LOSSY") == "true"
    assert frames.get("LOSSLESS_SOURCE") == "false"
    assert frames.get("SYNTHETIC_HIGH_BAND") == "true"
    assert frames.get("ENHANCEMENT_PRESET") == preset.name

    comm_frames = saved_id3.getall("COMM")
    assert len(comm_frames) > 0
    assert "OmniRip M10 Enhanced Derivative" in comm_frames[0].text[0]


def test_export_preserves_original_master(tmp_path: Path):
    """Verify that exporting never alters or removes the original file."""
    exporter = EnhancementExporter()
    source_path = tmp_path / "sample.mp3"
    original_content = b"ORIGINAL_MASTER_BYTES_DO_NOT_TOUCH"
    source_path.write_bytes(original_content)

    dummy_audio = np.zeros((2, 4800), dtype=np.float32)
    with patch.object(exporter, "decode_audio_ffmpeg", return_value=dummy_audio):
        with patch.object(exporter, "encode_mp3_ffmpeg"):
            with patch.object(exporter, "_apply_provenance_tags"):
                out_file = exporter.export_enhanced_derivative(
                    input_path=source_path,
                    preset=PRESETS["conservative"],
                )
                assert out_file == tmp_path / "sample.enhanced.mp3"
                # Check original master is identical
                assert source_path.read_bytes() == original_content


def test_dsp_gain_slope_stereo_verification():
    """Verify preset parameters (gain, decay slope, stereo width) modify audio."""
    exporter = EnhancementExporter()
    sr = 48000
    n = 48000
    cutoff_hz = 15000.0

    # Generate stereo test signal with wide stereo content
    t = np.linspace(0, 1.0, n, endpoint=False)
    left = np.sin(2 * np.pi * 1000 * t) + 0.5 * np.sin(2 * np.pi * 5000 * t)
    right = np.sin(2 * np.pi * 1000 * t) - 0.5 * np.sin(2 * np.pi * 5000 * t)
    audio_in = np.stack([left, right], axis=0).astype(np.float32)

    # 1. Test Gain & Slope: extended_air (+0.8 dB, 4.0 dB/oct) vs de_sizzle (-2.5 dB, 6.0 dB/oct)
    out_air = exporter.render_audio_buffer(
        audio_in, preset=PRESETS["extended_air"], cutoff_hz=cutoff_hz, sample_rate=sr
    )
    out_sizzle = exporter.render_audio_buffer(
        audio_in, preset=PRESETS["de_sizzle"], cutoff_hz=cutoff_hz, sample_rate=sr
    )

    # Compute high-frequency energy (>15 kHz) via FFT
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    high_mask = freqs >= cutoff_hz

    fft_air = np.fft.rfft(out_air, axis=1)
    fft_sizzle = np.fft.rfft(out_sizzle, axis=1)

    energy_air = np.sum(np.abs(fft_air[:, high_mask]) ** 2)
    energy_sizzle = np.sum(np.abs(fft_sizzle[:, high_mask]) ** 2)

    # Air boost + gentler slope must have noticeably greater high-frequency energy than de-sizzle
    assert energy_air > energy_sizzle

    # 2. Test Stereo Focus: narrow_stereo (0.65) vs fast_balanced (1.0)
    out_normal = exporter.render_audio_buffer(
        audio_in, preset=PRESETS["fast_balanced"], cutoff_hz=cutoff_hz, sample_rate=sr
    )
    out_narrow = exporter.render_audio_buffer(
        audio_in, preset=PRESETS["narrow_stereo"], cutoff_hz=cutoff_hz, sample_rate=sr
    )

    # Compute side channel in the high band (L - R)
    side_normal = out_normal[0] - out_normal[1]
    side_narrow = out_narrow[0] - out_narrow[1]

    fft_side_normal = np.fft.rfft(side_normal)
    fft_side_narrow = np.fft.rfft(side_narrow)

    side_energy_normal = np.sum(np.abs(fft_side_normal[high_mask]) ** 2)
    side_energy_narrow = np.sum(np.abs(fft_side_narrow[high_mask]) ** 2)

    # Narrow stereo (65%) must reduce side channel energy in the synthesized high frequencies
    assert side_energy_narrow < side_energy_normal

