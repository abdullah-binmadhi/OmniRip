"""Tests for Layer Studio analysis engine (layers.py) and the LayerStudio widget."""

from __future__ import annotations

import numpy as np
from textual.app import App, ComposeResult

from harvester.analysis.enhancement.layers import (
    build_layer_sources,
    build_layer_track,
    compute_source_envelope,
)
from harvester.analysis.enhancement.stem_separator import save_audio_numpy
from harvester.ui.layer_studio import LayerStudio


def _write_source(
    stem_dir,
    name: str,
    sr: int = 44100,
    dur_s: float = 2.0,
    freq_hz: float = 440.0,
    gain: float = 0.5,
    second_band: dict[int, float] | None = None,
    second_freq: float = 1000.0,
) -> None:
    """Write a synthetic stereo WAV source; optional per-second gain override."""
    n = int(sr * dur_s)
    seg_len = int(sr)
    sig = np.zeros(n, dtype=np.float32)
    t = np.linspace(0, dur_s, n, endpoint=False, dtype=np.float32)
    sig = gain * np.sin(2 * np.pi * freq_hz * t, dtype=np.float32)
    if second_band:
        for seg_idx, g in second_band.items():
            start = seg_idx * seg_len
            seg_t = np.linspace(0, 1.0, seg_len, endpoint=False, dtype=np.float32)
            sig[start:start + seg_len] = g * np.sin(
                2 * np.pi * second_freq * seg_t, dtype=np.float32
            )
    stereo = np.stack([sig, sig], axis=0)
    save_audio_numpy(stereo, stem_dir / name, sr)


def test_compute_source_envelope_signal_levels(tmp_path) -> None:
    """RMS dBFS envelope reports a loud second near 0 dB and quiet second near -60."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    _write_source(stem_dir, "layer_vocals.wav", sr=sr, dur_s=2.0, freq_hz=1000.0, gain=0.8)
    rms, peak = compute_source_envelope(stem_dir / "layer_vocals.wav", sr=sr, n_segments=2)
    assert rms.shape == (2,)
    assert peak.shape == (2,)
    assert peak[0] > 0.5
    assert rms[0] > -15.0
    assert rms[0] < 0.0


def test_build_layer_sources_detects_dynamic_lanes(tmp_path) -> None:
    """Raw source stems get blended into per-layer WAVs, then split into the
    lanes this song actually contains (cached on disk)."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_bs_roformer"
    for name in ("vocals", "bass", "drums", "other"):
        _write_source(stem_dir, f"{suffix}_raw_{name}.wav", sr=sr, freq_hz=400.0, gain=0.5)
        _write_source(stem_dir, f"{suffix}_raw_{name}_hdemucs.wav", sr=sr, freq_hz=90.0, gain=0.5)

    sources = build_layer_sources(stem_dir, "song", "bs_roformer", sample_rate=sr)

    # The bass stem carries both sub (90 Hz) and body (400 Hz) content, so it is
    # detected as two lanes; the drums stem has no cymbal-band content, so it
    # survives whole (presence gate) rather than becoming three silent lanes.
    assert set(sources) == {"vocals", "bass", "sub_bass", "drums", "other"}
    assert "sub_bass" in sources
    for name, path in sources.items():
        assert path.exists(), name
        assert path.stat().st_size > 44, name
    assert sources["vocals"].name == f"{suffix}_layer_vocals.wav"
    assert sources["sub_bass"].name == f"{suffix}_layer_sub_bass.wav"
    # The upper half of the bass split keeps the parent's lane name but never
    # clobbers the unfiltered parent file.
    assert sources["bass"].name == f"{suffix}_layer_bass_upper.wav"


def test_build_layer_sources_eco_fallback(tmp_path) -> None:
    """Eco mode (no neural raw sources) falls back to vocals + instrumental mix row."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_eco"
    _write_source(stem_dir, f"{suffix}_vocals.wav", sr=sr, freq_hz=1000.0, gain=0.5)
    _write_source(stem_dir, f"{suffix}_instrumental.wav", sr=sr, freq_hz=300.0, gain=0.5)

    sources = build_layer_sources(stem_dir, "song", "eco", sample_rate=sr)

    assert "vocals" in sources
    assert "mix" in sources
    assert "drums" not in sources


def test_build_layer_track_segments_levels_and_bleed_issue(tmp_path) -> None:
    """Full pipeline builds a 2-second track; bass vocal-band burst flags vocal_bleed."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_bs_roformer"

    # Bass is mostly 90 Hz sub, but second 0 carries a loud 1000 Hz vocal-band burst
    _write_source(
        stem_dir,
        f"{suffix}_raw_bass.wav",
        sr=sr,
        freq_hz=90.0,
        gain=0.5,
        second_band={0: 0.9},
    )
    _write_source(stem_dir, f"{suffix}_raw_bass_hdemucs.wav", sr=sr, freq_hz=90.0, gain=0.5)
    for name in ("vocals", "drums", "other"):
        _write_source(stem_dir, f"{suffix}_raw_{name}.wav", sr=sr, freq_hz=500.0, gain=0.5)
        _write_source(stem_dir, f"{suffix}_raw_{name}_hdemucs.wav", sr=sr, freq_hz=500.0, gain=0.5)

    track = build_layer_track(stem_dir, "song", "bs_roformer", duration_s=2.0, sample_rate=sr)

    # 90 Hz sub + the 1000 Hz second-0 burst make the bass stem two lanes.
    assert track.active_layers == ["vocals", "drums", "sub_bass", "bass", "other"]
    assert track.n_segments == 2
    assert track.segment_at(0.4) is track.segments[0]
    assert track.segment_at(1.5) is track.segments[1]
    assert track.segments[0].levels["vocals"] > 0.0
    assert track.segments[1].levels["vocals"] > 0.0
    seg0_kinds = {issue.kind for issue in track.segments[0].issues if issue.layer == "bass"}
    assert "vocal_bleed" in seg0_kinds
    assert "bass → sub_bass/bass" in track.lane_summary
    assert "drums (whole)" in track.lane_summary


class LayerStudioTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield LayerStudio(id="test-layer-studio")


async def test_layer_studio_widget_mount_render_sync(tmp_path) -> None:
    """LayerStudio renders a grid and syncing the playhead does not raise."""
    app = LayerStudioTestApp()
    async with app.run_test() as pilot:
        studio = app.query_one("#test-layer-studio", LayerStudio)
        assert studio.track is None

        sr = 44100
        stem_dir = tmp_path / "stems"
        stem_dir.mkdir()
        suffix = "song_bs_roformer"
        for name in ("vocals", "bass"):
            _write_source(stem_dir, f"{suffix}_raw_{name}.wav", sr=sr, freq_hz=500.0, gain=0.5)
            _write_source(stem_dir, f"{suffix}_raw_{name}_hdemucs.wav", sr=sr, freq_hz=500.0, gain=0.5)
        track = build_layer_track(stem_dir, "song", "bs_roformer", duration_s=5.0, sample_rate=sr)

        studio.track = track
        await pilot.pause()
        assert studio.track is track
        assert studio.track.n_segments == 5
        rendered = str(studio.render())
        assert "VOCALS" in rendered
        assert "BASS" in rendered

        studio.playhead_s = 2.5
        await pilot.pause()
        assert studio.playhead_s == 2.5


async def test_layer_studio_edit_requested_message(tmp_path) -> None:
    """Cell edit ops emit EditRequested and render edit markers via the plan."""
    app = LayerStudioTestApp()
    async with app.run_test() as pilot:
        studio = app.query_one("#test-layer-studio", LayerStudio)
        sr = 44100
        stem_dir = tmp_path / "stems"
        stem_dir.mkdir()
        suffix = "song_bs_roformer"
        for name in ("vocals", "bass"):
            _write_source(stem_dir, f"{suffix}_raw_{name}.wav", sr=sr, freq_hz=500.0, gain=0.5)
            _write_source(stem_dir, f"{suffix}_raw_{name}_hdemucs.wav", sr=sr, freq_hz=500.0, gain=0.5)
        track = build_layer_track(stem_dir, "song", "bs_roformer", duration_s=5.0, sample_rate=sr)
        studio.track = track
        await pilot.pause()

        # Select a cell then invoke the mute action -> EditRequested(post Message)
        studio._selected_idx = 1
        studio._selected_layer = "bass"
        received: list[tuple[int, str, str]] = []
        original = studio.post_message

        def capture(msg):
            if isinstance(msg, LayerStudio.EditRequested):
                received.append((msg.segment_idx, msg.layer, msg.op))
            original(msg)

        studio.post_message = capture  # type: ignore[method-assign]
        studio.action_edit_mute()
        await pilot.pause()
        assert received == [(1, "bass", "mute")]

        # With an edit_plan set, the cell renders an edit marker.
        from harvester.analysis.enhancement.layer_editor import EditPlan

        plan = EditPlan()
        plan.add("bass", 1, "mute")
        studio.edit_plan = plan
        await pilot.pause()
        assert "✎" in str(studio.render())