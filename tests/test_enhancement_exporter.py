"""Tests for EnhancementExporter and Presets (Milestone 10-D)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf
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
    assert "OmniRip Enhanced Derivative" in comm_frames[0].text[0]


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

    # Generate clean normalized broadband audio with reference octave energy
    np.random.seed(42)
    t = np.linspace(0, 1.0, n, endpoint=False)
    base = 0.2 * np.sin(2 * np.pi * 1000 * t) + 0.2 * np.sin(2 * np.pi * 10000 * t)
    noise_l = np.random.normal(0, 0.05, n)
    noise_r = np.random.normal(0, 0.05, n)
    audio_in = np.stack([base + noise_l, base - noise_r], axis=0).astype(np.float32)
    audio_in = audio_in / np.max(np.abs(audio_in)) * 0.6

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


def test_enhancement_exporter_neural_toggle():
    """Verify that EnhancementExporter toggles neural acceleration across all providers."""
    exporter = EnhancementExporter(neural_enabled=False)
    assert not exporter.neural_enabled
    assert not exporter._providers["nvsr"].neural_enabled
    assert not exporter._providers["flashsr"].neural_enabled
    assert not exporter._providers["hybrid"].neural_enabled

    exporter.set_neural_enabled(True)
    assert exporter.neural_enabled
    assert exporter._providers["nvsr"].neural_enabled
    assert exporter._providers["flashsr"].neural_enabled
    assert exporter._providers["hybrid"].neural_enabled

    exporter.set_neural_enabled(False)
    assert not exporter.neural_enabled
    assert not exporter._providers["nvsr"].neural_enabled


def test_export_progress_callback_granularity(tmp_path: Path):
    """Verify that export_enhanced_derivative calls progress_callback with granular AI telemetry."""
    exporter = EnhancementExporter()
    source_path = tmp_path / "sample.mp3"
    source_path.write_bytes(b"DUMMY_MP3_CONTENT")

    dummy_audio = np.random.normal(0, 0.1, (2, 48000)).astype(np.float32)
    progress_log: list[tuple[float, str]] = []

    def on_progress(pct: float, msg: str) -> None:
        progress_log.append((pct, msg))

    with patch.object(exporter, "decode_audio_ffmpeg", return_value=dummy_audio):
        with patch.object(exporter, "encode_mp3_ffmpeg"):
            with patch.object(exporter, "_apply_provenance_tags"):
                # Test with fast_balanced (NVSR neural preset)
                out_path = exporter.export_enhanced_derivative(
                    input_path=source_path,
                    preset=PRESETS["fast_balanced"],
                    progress_callback=on_progress,
                )
                assert out_path.exists() or out_path.name.endswith(".enhanced.mp3")

    # Verify milestones were recorded
    percentages = [p[0] for p in progress_log]
    messages = [p[1] for p in progress_log]

    assert 10.0 in percentages
    assert 35.0 in percentages
    assert 72.0 in percentages or 70.0 in percentages
    assert 100.0 in percentages

    # Crucial: verify intermediate AI telemetry between 35% and 70%
    intermediate_pcts = [pct for pct in percentages if 35.0 < pct < 70.0]
    assert len(intermediate_pcts) >= 3, (
        f"Expected intermediate AI progress updates, got: {percentages}"
    )

    # Verify AI messages contain telemetry descriptors
    all_msgs_str = " ".join(messages)
    assert "AI Core" in all_msgs_str or "AI Engine" in all_msgs_str
    assert "Spectral Balancer" in all_msgs_str or "Mastering Limiter" in all_msgs_str


def _write_source(tmp_path: Path, seconds: float = 2.0, sr: int = 48000) -> Path:
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    tone = 0.3 * np.sin(2 * np.pi * 1000.0 * t)
    source = tmp_path / "lossless_src.wav"
    sf.write(source, np.stack([tone, tone], axis=1), sr)
    return source


def test_export_enhanced_lossless_writes_24bit_flac_and_wav(tmp_path: Path):
    """FLAC/WAV exports are 24-bit 48 kHz and carry provenance tags."""
    from mutagen.flac import FLAC
    from mutagen.wave import WAVE

    source = _write_source(tmp_path)
    exporter = EnhancementExporter(neural_enabled=False)
    preset = PRESETS["conservative"]

    extra = {"GENRE": "House", "GENRE_MIX": "house,disco", "GENRE_INTENSITY": "bold"}
    flac_path = exporter.export_enhanced_lossless(source, preset, fmt="flac", extra_tags=extra)
    wav_path = exporter.export_enhanced_lossless(source, preset, fmt="wav", extra_tags=extra)

    assert flac_path.name == "lossless_src.enhanced.flac"
    assert wav_path.name == "lossless_src.enhanced.wav"
    for path in (flac_path, wav_path):
        info = sf.info(str(path))
        assert info.samplerate == 48000
        assert info.subtype == "PCM_24"

    flac = FLAC(flac_path)
    assert flac["DERIVED_FROM_LOSSY"] == ["true"]
    assert flac["LOSSLESS_SOURCE"] == ["false"]
    assert flac["SYNTHETIC_HIGH_BAND"] == ["true"]
    assert flac["ENHANCEMENT_PRESET"] == [preset.name]
    assert flac["GENRE"] == ["House"]
    assert flac["GENRE_MIX"] == ["house,disco"]
    assert flac["GENRE_INTENSITY"] == ["bold"]

    wave_tags = WAVE(wav_path).tags
    assert wave_tags is not None
    txxx = {str(frame.desc): frame.text for frame in wave_tags.getall("TXXX")}
    assert txxx["DERIVED_FROM_LOSSY"] == ["true"]
    assert txxx["ENHANCEMENT_PRESET"] == [preset.name]
    assert txxx["GENRE"] == ["House"]
    assert txxx["GENRE_MIX"] == ["house,disco"]
    assert txxx["GENRE_INTENSITY"] == ["bold"]


def test_export_enhanced_derivative_mp3_carries_extra_tags_in_txxx(tmp_path: Path):
    from mutagen.id3 import ID3

    source = _write_source(tmp_path)
    exporter = EnhancementExporter(neural_enabled=False)
    preset = PRESETS["conservative"]
    mp3_path = tmp_path / "out.mp3"
    extra = {"GENRE": "Techno", "GENRE_MIX": "techno,acid", "GENRE_INTENSITY": "subtle"}
    out = exporter.export_enhanced_derivative(
        source, preset, output_path=mp3_path, extra_tags=extra
    )
    assert out.exists()
    id3 = ID3(out)
    txxx = {str(frame.desc): frame.text for frame in id3.getall("TXXX")}
    assert txxx["DERIVED_FROM_LOSSY"] == ["true"]
    assert txxx["ENHANCEMENT_PRESET"] == [preset.name]
    assert txxx["GENRE"] == ["Techno"]
    assert txxx["GENRE_MIX"] == ["techno,acid"]
    assert txxx["GENRE_INTENSITY"] == ["subtle"]


def test_export_enhanced_lossless_rejects_unknown_format(tmp_path: Path):
    source = _write_source(tmp_path)
    exporter = EnhancementExporter(neural_enabled=False)
    try:
        exporter.export_enhanced_lossless(source, PRESETS["conservative"], fmt="mp4")
    except ValueError as exc:
        assert "Unsupported lossless format" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_export_enhanced_lossless_decodes_through_ffmpeg_and_renders_once(tmp_path: Path):
    """The shared render helper is used once and EQ is applied to the written master."""
    from harvester.analysis.enhancement.eq import MasteringEQSettings

    source = _write_source(tmp_path)
    exporter = EnhancementExporter(neural_enabled=False)
    eq = MasteringEQSettings()
    eq.set_band(16000, 3.0)

    with patch.object(exporter, "_render_enhanced", wraps=exporter._render_enhanced) as render:
        out = exporter.export_enhanced_lossless(
            source, PRESETS["conservative"], fmt="flac", eq_settings=eq
        )
    assert render.call_count == 1
    assert render.call_args[0][3] is eq
    assert out.exists()


def test_generate_lossless_path_preserves_requested_format():
    exporter = EnhancementExporter(neural_enabled=False)
    # Standard source file
    src = Path("/music/track.mp3")
    assert exporter.generate_lossless_path(src, "wav") == Path("/music/track.enhanced.wav")
    assert exporter.generate_lossless_path(src, "flac") == Path("/music/track.enhanced.flac")

    # Source stem ending in .enhanced
    src_enh = Path("/music/track.enhanced.mp3")
    assert exporter.generate_lossless_path(src_enh, "wav") == Path("/music/track.enhanced.wav")
    assert exporter.generate_lossless_path(src_enh, "flac") == Path("/music/track.enhanced.flac")

