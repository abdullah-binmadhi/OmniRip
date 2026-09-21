"""Tests for the layer terminal JSON sidecar (layer_sidecar.py)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from harvester.analysis.enhancement.layer_editor import EditPlan
from harvester.analysis.enhancement.layers import (
    LayerIssue,
    LayerSegment,
    LayerSource,
    LayerTrack,
)
from harvester.ipc.layer_sidecar import (
    TransportState,
    consume_requests,
    read_sidecar,
    read_transport,
    request_play_state,
    request_seek,
    transport_path,
    write_sidecar,
    write_transport,
)


def _build_track(stem_dir) -> LayerTrack:
    """A fully-populated in-memory LayerTrack (no WAVs needed for the sidecar)."""
    sr = 44100
    sources = {
        "vocals": LayerSource(
            name="vocals",
            path=Path(stem_dir) / "song_bs_roformer_layer_vocals.wav",
            rms=np.asarray([-18.5, -20.1], dtype=np.float32),
            peak=np.asarray([0.92, 0.71], dtype=np.float32),
        ),
        "bass": LayerSource(
            name="bass",
            path=Path(stem_dir) / "song_bs_roformer_layer_bass.wav",
            rms=np.asarray([-22.0, -23.4], dtype=np.float32),
            peak=np.asarray([0.4, 0.3], dtype=np.float32),
        ),
    }
    segments = [
        LayerSegment(
            index=0,
            start_s=0.0,
            end_s=1.0,
            levels={"vocals": 0.69, "bass": 0.63},
            issues=[
                LayerIssue("vocal_bleed", "bass", 0.82),
            ],
        ),
        LayerSegment(
            index=1,
            start_s=1.0,
            end_s=2.0,
            levels={"vocals": 0.66, "bass": 0.61},
            issues=[],
        ),
    ]
    return LayerTrack(
        duration_s=2.0,
        sample_rate=sr,
        segment_size_s=1.0,
        sources=sources,
        segments=segments,
        engine="bs_roformer",
    )


def test_write_read_roundtrip(tmp_path) -> None:
    """A LayerTrack + EditPlan round-trips through the JSON sidecar field-for-field."""
    sidecar = tmp_path / "layer_sidecar.json"
    track = _build_track(tmp_path)
    plan = EditPlan()
    plan.add("bass", 0, "mute")
    plan.add("vocals", 1, "de_bleed")

    write_sidecar(track, plan, sidecar)
    assert sidecar.exists()

    restored, restored_plan = read_sidecar(sidecar)

    assert restored.duration_s == track.duration_s
    assert restored.sample_rate == track.sample_rate
    assert restored.segment_size_s == track.segment_size_s
    assert restored.engine == "bs_roformer"
    assert set(restored.sources) == {"vocals", "bass"}
    assert restored.n_segments == 2

    for name in ("vocals", "bass"):
        src = restored.sources[name]
        orig = track.sources[name]
        assert src.name == orig.name
        assert str(src.path) == str(orig.path)
        assert np.allclose(src.rms, orig.rms)
        assert np.allclose(src.peak, orig.peak)

    seg = restored.segments[0]
    assert seg.index == 0
    assert seg.levels["bass"] == pytest.approx(0.63)
    assert len(seg.issues) == 1
    issue = seg.issues[0]
    assert (issue.kind, issue.layer, issue.severity) == ("vocal_bleed", "bass", 0.82)

    assert restored_plan == {("bass", 0): "mute", ("vocals", 1): "de_bleed"}


def test_sidecar_missing_file_raises(tmp_path) -> None:
    """read_sidecar on a nonexistent path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_sidecar(tmp_path / "does_not_exist.json")


def test_sidecar_version_mismatch_raises(tmp_path) -> None:
    """A sidecar with an unsupported version raises ValueError."""
    stale = tmp_path / "stale_sidecar.json"
    stale.write_text(json.dumps({"version": 99, "segments": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        read_sidecar(stale)


def test_sidecar_keeps_dynamic_lane_order(tmp_path) -> None:
    """Detected lanes round-trip in the main app's order (JSON sorts keys)."""
    sidecar = tmp_path / "layer_sidecar.json"
    track = _build_track(tmp_path)
    track.sources = {
        "vocals": track.sources["vocals"],
        "sub_bass": track.sources["bass"],
        "bass": track.sources["bass"],
        "guitar": track.sources["vocals"],
    }

    write_sidecar(track, EditPlan(), sidecar)
    restored, _plan = read_sidecar(sidecar)

    assert restored.active_layers == ["vocals", "sub_bass", "bass", "guitar"]


def test_sidecar_carries_lane_provenance(tmp_path) -> None:
    """The lane plan (origin/confidence/note + singers) survives the sidecar hop."""
    from harvester.analysis.enhancement.lane_plan import plan_lanes

    sidecar = tmp_path / "layer_sidecar.json"
    track = _build_track(tmp_path)
    track.lane_plan = plan_lanes(
        ["vocals", "kick", "bass"],
        splits={"drums": ("kick",)},
        credit_instruments=["double bass", "saxophone"],
        singer_count=2,
    )
    write_sidecar(track, EditPlan(), sidecar)

    restored, _plan = read_sidecar(sidecar)

    assert restored.lane_plan is not None
    assert restored.lane_plan.origin_of("kick") == "dsp-split"
    assert restored.lane_plan.singer_count == 2
    missing = restored.lane_plan.missing
    assert [m.name for m in missing] == ["saxophone"]
    assert restored.lane_plan.entry("bass") is not None
    assert "double bass" in restored.lane_plan.note_of("bass")


def test_sidecar_without_a_plan_reads_back_empty(tmp_path) -> None:
    """Older/plainer tracks still load: no plan means an empty plan, not an error."""
    sidecar = tmp_path / "layer_sidecar.json"
    write_sidecar(_build_track(tmp_path), EditPlan(), sidecar)

    restored, _plan = read_sidecar(sidecar)

    assert restored.lane_plan is not None
    assert restored.lane_plan.entries == ()
    assert restored.lane_plan.summary() == ""


def test_transport_roundtrip_and_atomic_write(tmp_path) -> None:
    """Transport state publishes playhead/playing/duration without leftover temp files."""
    sidecar = tmp_path / "layer_sidecar.json"
    path = transport_path(sidecar)
    assert path.name == "layer_sidecar.transport.json"

    write_transport(path, TransportState(playhead_s=12.5, playing=True, duration_s=214.0))
    state = read_transport(path)

    assert state.playhead_s == pytest.approx(12.5)
    assert state.playing is True
    assert state.duration_s == pytest.approx(214.0)
    assert state.seek_request is None
    assert state.written_at > 0.0
    assert not path.with_name(f"{path.name}.tmp").exists()


def test_transport_reads_missing_or_corrupt_file_as_idle(tmp_path) -> None:
    """A missing or half-written transport file must never raise in the poller."""
    sidecar = tmp_path / "layer_sidecar.json"
    path = transport_path(sidecar)

    idle = read_transport(path)
    assert (idle.playhead_s, idle.playing, idle.seek_request) == (0.0, False, None)

    path.write_text("{not json", encoding="utf-8")
    assert read_transport(path).playing is False


def test_transport_requests_flow_both_ways(tmp_path) -> None:
    """The terminal's seek/play requests survive the main app's publish loop."""
    sidecar = tmp_path / "layer_sidecar.json"
    write_transport(
        transport_path(sidecar),
        TransportState(playhead_s=3.0, playing=True, duration_s=100.0),
    )

    # Terminal asks for a seek + pause on top of the published state.
    request_seek(sidecar, 42.0)
    request_play_state(sidecar, False)
    pending = read_transport(transport_path(sidecar))
    assert pending.seek_request == pytest.approx(42.0)
    assert pending.play_request is False
    assert pending.playhead_s == pytest.approx(3.0)  # published state preserved

    # Main app consumes them once, then publishes cleanly.
    seek, play = consume_requests(sidecar)
    assert seek == pytest.approx(42.0)
    assert play is False
    assert consume_requests(sidecar) == (None, None)

    write_transport(
        transport_path(sidecar),
        TransportState(playhead_s=42.0, playing=False, duration_s=100.0),
    )
    after = read_transport(transport_path(sidecar))
    assert after.playhead_s == pytest.approx(42.0)
    assert after.seek_request is None
