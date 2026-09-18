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
