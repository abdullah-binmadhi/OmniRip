"""Tests for M3 Layer Studio hardening — residual-inversion budget, de-bleed
acceptance fixture, long-track analysis budget + run-length collapse."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from harvester.analysis.enhancement.layer_editor import (
    DE_BLEED_ATTEN_DB,
    RECONSTRUCTION_BUDGET_DB,
    EditPlan,
    commit_edit_plan,
    reconstruct_mix,
    verify_mix_residual,
)
from harvester.analysis.enhancement.layers import (
    ANALYSIS_MS_PER_SECOND_BUDGET,
    LONG_TRACK_SECONDS,
    VOCAL_CORE_BAND,
    LayerSource,
    LayerTrack,
    analyze_layer_segments,
    build_layer_sources,
    build_layer_track,
    run_length_collapse,
    segment_band_level,
)
from harvester.analysis.enhancement.stem_separator import (
    _apply_lr4_crossover,
    load_audio_numpy,
    save_audio_numpy,
)


def _sine(sr: int, dur_s: float, freq_hz: float, gain: float = 0.5) -> np.ndarray:
    t = np.linspace(0, int(sr * dur_s), int(sr * dur_s), endpoint=False, dtype=np.float32)
    return np.stack([gain * np.sin(2 * np.pi * freq_hz * t),] * 2, axis=0)


def _tiled_sine(sr: int, dur_s: float, freq_hz: float, gain: float = 0.3) -> np.ndarray:
    """Constant track: one float64 second tiled N times so every segment is
    byte-identical (deterministic run-length collapse for the long-track test)."""
    n = int(sr * dur_s)
    secs = int(dur_s)
    k = np.arange(sr, dtype=np.float64)
    one = gain * np.sin(2.0 * np.pi * freq_hz * k / sr)
    sig = np.tile(one, secs).astype(np.float32)[:n]
    return np.stack([sig, sig], axis=0)


def _write_raw_sources(
    stem_dir,
    suffix: str,
    sr: int = 44100,
    dur_s: float = 3.0,
    gains: dict[str, float] | None = None,
) -> None:
    """Eight raw cache files (4 BS-RoFormer + 4 HDEMUCS low-anchor)."""
    freqs = {"vocals": 7000.0, "bass": 440.0, "drums": 8000.0, "other": 240.0}
    g = gains or {}
    for name, freq in freqs.items():
        save_audio_numpy(
            _sine(sr, dur_s, freq, g.get(name, 0.12)), stem_dir / f"{suffix}_raw_{name}.wav", sr
        )
        save_audio_numpy(
            _sine(sr, dur_s, 60.0, g.get(f"{name}_hd", 0.12)),
            stem_dir / f"{suffix}_raw_{name}_hdemucs.wav",
            sr,
        )


def _lr4_reference(suffix: str, stem_dir, sr: int = 44100) -> np.ndarray:
    """Reference mix = LR4 recombination of the summed raw sources.

    By linearity of the LR4 crossover, this equals the sum of the four
    per-source layer files exactly (up to float32 rounding).
    """
    hd_total = None
    ro_total = None
    for name in ("vocals", "bass", "drums", "other"):
        ro, _ = load_audio_numpy(stem_dir / f"{suffix}_raw_{name}.wav", target_sr=sr)
        hd, _ = load_audio_numpy(stem_dir / f"{suffix}_raw_{name}_hdemucs.wav", target_sr=sr)
        ro_mono = ro.mean(axis=0).astype(np.float64)
        hd_mono = hd.mean(axis=0).astype(np.float64)
        ro_total = ro_mono if ro_total is None else ro_total + ro_mono
        hd_total = hd_mono if hd_total is None else hd_total + hd_mono
    n = min(hd_total.shape[0], ro_total.shape[0])
    blend = _apply_lr4_crossover(
        hd_total[:n][np.newaxis, :], ro_total[:n][np.newaxis, :], sr=sr, crossover_hz=300.0
    )
    return np.asarray(blend, dtype=np.float64).reshape(-1)


def test_reconstruct_mix_inversion_within_budget(tmp_path) -> None:
    """Sum of the four layer files reconstructs the LR4 reference mix (≤ budget)."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_bs_roformer"
    _write_raw_sources(stem_dir, suffix, sr=sr, dur_s=3.0)

    sources = build_layer_sources(stem_dir, "song", "bs_roformer", sample_rate=sr)
    # The song's lanes replace the static four-stem rows where its content
    # supports a split; the children partition their parent exactly, which is
    # what keeps this reconstruction budget valid.
    lanes = set(sources)
    assert {"vocals", "other"} <= lanes
    assert ("drums" in lanes) or {"kick", "snare", "hats"} <= lanes
    assert ("bass" in lanes) or {"sub_bass", "bass"} <= lanes
    assert len(lanes) > 4

    reference = _lr4_reference(suffix, stem_dir, sr=sr)
    mix = reconstruct_mix(sources, sr)
    assert abs(mix.shape[0] - reference.shape[0]) <= sr

    _, worst, violating = verify_mix_residual(
        reference, mix, sample_rate=sr, budget_db=RECONSTRUCTION_BUDGET_DB
    )
    assert violating == [], f"reconstruction residual {worst:.1f} dBFS exceeds budget"


def test_edited_seconds_are_the_only_budget_violations(tmp_path) -> None:
    """Committing edits leaves every unedited second sample-identical (≤ budget)."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_bs_roformer"
    _write_raw_sources(stem_dir, suffix, sr=sr, dur_s=3.0)
    sources = build_layer_sources(stem_dir, "song", "bs_roformer", sample_rate=sr)

    pre = reconstruct_mix(sources, sr)
    plan = EditPlan()
    edited_lanes = sorted(set(sources))[:2]
    assert len(edited_lanes) == 2
    plan.add(edited_lanes[0], 1, "mute")
    plan.add(edited_lanes[1], 2, "mute")
    commit_edit_plan(plan, sources, sample_rate=sr)
    post = reconstruct_mix(sources, sr)

    _, worst, violating = verify_mix_residual(
        pre, post, sample_rate=sr, budget_db=RECONSTRUCTION_BUDGET_DB
    )
    assert set(violating) == {1, 2}, (
        f"unedited seconds leaked reconstruction residual ({worst:.1f} dBFS worst)"
    )


def test_de_bleed_drops_vocal_band_leak_at_least_20_db(tmp_path) -> None:
    """Injected vocal-band burst → exact vocal_bleed flag → de-bleed commit drops
    in-band residual ≥ 20 dB (the M3 acceptance threshold)."""
    sr = 44100
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    suffix = "song_bs_roformer"

    # Bass: 90 Hz sub everywhere, but second 1 carries a loud 1000 Hz vocal-band burst
    for name, freq, gain, extra in (
        ("bass", 90.0, 0.4, {1: 0.9}),
        ("vocals", 500.0, 0.3, None),
        ("drums", 500.0, 0.3, None),
        ("other", 500.0, 0.3, None),
    ):
        n = int(sr * 3)
        t = np.linspace(0, 3, n, endpoint=False, dtype=np.float32)
        sig = gain * np.sin(2 * np.pi * freq * t, dtype=np.float32)
        if extra:
            for seg_idx, g in extra.items():
                seg_t = np.linspace(0, 1, sr, endpoint=False, dtype=np.float32)
                start = seg_idx * sr
                sig[start : start + sr] = g * np.sin(2 * np.pi * 1000.0 * seg_t, dtype=np.float32)
        save_audio_numpy(np.stack([sig, sig], axis=0), stem_dir / f"{suffix}_raw_{name}.wav", sr)
        save_audio_numpy(
            np.stack([sig, sig], axis=0),
            stem_dir / f"{suffix}_raw_{name}_hdemucs.wav",
            sr,
        )

    track = build_layer_track(stem_dir, "song", "bs_roformer", duration_s=3.0, sample_rate=sr)
    bass = track.sources["bass"]
    assert bass is not None
    kinds = {i.kind for i in track.segments[1].issues if i.layer == "bass"}
    assert "vocal_bleed" in kinds
    assert all(
        "vocal_bleed" not in {i.kind for i in track.segments[s].issues if i.layer == "bass"}
        for s in (0, 2)
    )

    layer_path = bass.path
    pre_db = segment_band_level(layer_path, 1, VOCAL_CORE_BAND, sr=sr)
    assert pre_db > -40.0

    plan = EditPlan()
    plan.add("bass", 1, "de_bleed")
    paths = build_layer_sources(stem_dir, "song", "bs_roformer", sample_rate=sr)
    written = commit_edit_plan(plan, paths, sample_rate=sr)
    assert set(written) == {"bass"}

    post_db = segment_band_level(layer_path, 1, VOCAL_CORE_BAND, sr=sr)
    assert pre_db - post_db >= 20.0, (
        f"de-bleed ({DE_BLEED_ATTEN_DB} dB) only cut in-band leak by {pre_db - post_db:.1f} dB"
    )


def test_run_length_collapse_merges_identical_cells() -> None:
    """Adjacent identical cells collapse to one run; ops/issues/levels split them."""
    from pathlib import Path

    from harvester.analysis.enhancement.layers import LayerSegment

    n = 6
    track = LayerTrack(duration_s=float(n), sample_rate=44100)

    def source(name: str, rms_db: list[float]) -> LayerSource:
        return LayerSource(
            name=name,
            path=Path(f"{name}.wav"),
            rms=np.array(rms_db, dtype=np.float32),
            peak=np.full(n, 0.5, dtype=np.float32),
        )

    track.sources = {
        "bass": source("bass", [-10.0] * n),
        "drums": source("drums", [-10, -10, -30, -30, -10, -10]),
        "vocals": source("vocals", [-40.0] * n),
        "other": source("other", [-40.0] * n),
    }
    track.segments = [
        LayerSegment(
            index=i,
            start_s=float(i),
            end_s=float(i + 1),
            levels={name: s.level(i) for name, s in track.sources.items()},
            issues=[],
        )
        for i in range(n)
    ]

    no_plan = run_length_collapse(track)
    assert len(no_plan["bass"]) == 1
    assert no_plan["bass"][0].count == 6
    # Drums alternate 7/7 | 4/4 | 7/7 -> three runs
    assert [r.count for r in no_plan["drums"]] == [2, 2, 2]
    for _layer, runs in no_plan.items():
        assert sum(r.count for r in runs) == n
        assert all(r.start_idx + r.count == r.end_idx for r in runs)

    plan = EditPlan()
    plan.add("drums", 2, "mute")
    plan.add("drums", 3, "mute")
    with_plan = run_length_collapse(track, edit_plan=plan)
    muted = [r for r in with_plan["drums"] if r.op == "mute"]
    assert len(muted) == 1 and muted[0].count == 2 and muted[0].start_idx == 2

    # split_at forces a boundary through the merged mute run
    split = run_length_collapse(track, edit_plan=plan, split_at={2})
    muted_split = [r for r in split["drums"] if r.op == "mute"]
    assert [r.count for r in muted_split] == [1, 1]


def test_long_track_analysis_respects_per_second_budget_and_collapses(tmp_path) -> None:
    """600 s track: per-second analysis stays inside budget and a constant layer
    collapses to a single run-length cell."""
    sr = 8000
    dur_s = 600.0
    assert dur_s >= LONG_TRACK_SECONDS
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()

    sources: dict[str, Path] = {}
    for name, freq in (("vocals", 1000.0), ("bass", 200.0), ("drums", 1000.0), ("other", 1500.0)):
        p = stem_dir / f"layer_{name}.wav"
        save_audio_numpy(_tiled_sine(sr, dur_s, freq, gain=0.3), p, sr)
        sources[name] = p

    started = time.perf_counter()
    layer_sources, segments = analyze_layer_segments(sources, dur_s, sample_rate=sr)
    elapsed_ms = (time.perf_counter() - started) * 1e3

    budget_ms = dur_s * ANALYSIS_MS_PER_SECOND_BUDGET
    assert elapsed_ms <= budget_ms, (
        f"analysis took {elapsed_ms:.0f} ms, budget is {budget_ms:.0f} ms "
        f"({ANALYSIS_MS_PER_SECOND_BUDGET} ms/s)"
    )
    track = LayerTrack(
        duration_s=dur_s,
        sample_rate=sr,
        sources=layer_sources,
        segments=segments,
    )
    assert track.n_segments == 600

    runs = run_length_collapse(track)
    for layer, row in runs.items():
        assert len(row) == 1, f"{layer} constant cell stream split into {len(row)} runs"
        assert row[0].count == 600


def test_widget_renders_long_track_as_run_length_cells() -> None:
    """LayerStudio falls back to run-length rendering for tracks ≥ 600 seconds."""
    from harvester.analysis.enhancement.layers import LayerSegment
    from harvester.ui.layer_studio import LayerStudio

    n = 600
    track = LayerTrack(duration_s=600.0, sample_rate=8000)
    track.sources = {
        name: LayerSource(
            name=name,
            path=Path(f"{name}.wav"),
            rms=np.full(n, -10.0, dtype=np.float32),
            peak=np.full(n, 0.5, dtype=np.float32),
        )
        for name in ("vocals", "bass", "drums", "other")
    }
    track.segments = [
        LayerSegment(
            index=i,
            start_s=float(i),
            end_s=float(i + 1),
            levels={name: s.level(i) for name, s in track.sources.items()},
            issues=[],
        )
        for i in range(n)
    ]

    widget = LayerStudio()
    widget.track = track
    out = widget.render()
    # level -10 dB -> bin 7 -> "▇"; collapsed row renders the constant run across
    # the visible window without flattening alignments or crashing.
    assert "VOCALS" in out.plain
    assert any(g in out.plain for g in ("▇▇", "⣶⣶", "⣿⣿"))