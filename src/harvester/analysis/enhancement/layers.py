"""
Layer Studio Analysis Engine.

Builds a Photoshop/Lightroom-style layered timeline from a separated track:

- Each source stem (vocals / bass / drums / other) becomes a timeline row.
- The track is sliced into fixed 1-second segments (columns).
- Each cell carries that source's RMS level in that second plus detected
  acoustic issues (vocal bleed, ghost whispers, sibilance, low-mid mud).
- Playback sync, click-to-seek, and per-second editing live in the
  LayerStudio widget; this module is the pure-data backend.

The per-source stems are either:
  * Neural (ensemble): BS-RoFormer raw sources LR4-blended against the
    HDEMUCS raw sources below ``crossover_hz`` (low anchor = HDEMUCS).
  * Eco: a 2-layer fallback (vocals + instrumental) since mid/side phase
    matrixing cannot split drums/bass/other reliably.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

SEGMENT_SIZE_S: float = 1.0

LAYER_ORDER: tuple[str, ...] = ("vocals", "bass", "drums", "other", "mix")

LAYER_LABELS: dict[str, str] = {
    "vocals": "VOCALS",
    "bass": "BASS",
    "drums": "DRUMS",
    "other": "OTHER",
    "mix": "MIX",
}

# Acoustic issue fingerprint bands (Hz), reusing acoustic_detector semantics
VOCAL_CORE_BAND: tuple[float, float] = (300.0, 3500.0)
WHISPER_BAND: tuple[float, float] = (1000.0, 2800.0)
SIBILANCE_BAND: tuple[float, float] = (5500.0, 8500.0)
MUD_BAND: tuple[float, float] = (250.0, 350.0)
LOW_END_BAND: tuple[float, float] = (30.0, 120.0)

ISSUE_LABELS: dict[str, str] = {
    "vocal_bleed": "Vocal bleed (instruments leaking voice band)",
    "whisper": "Ghost whispers (side-channel vocal leakage)",
    "sizzle": "Sibilance harshness (5.5-8.5 kHz)",
    "mud": "Low-mid mud (250-350 Hz boxiness)",
    "sub_rumble": "Sub rumble (30-120 Hz energy)",
}

ISSUE_COLORS: dict[str, str] = {
    "vocal_bleed": "#ff3366",
    "whisper": "#ffcc00",
    "sizzle": "#ffffff",
    "mud": "#cc6633",
    "sub_rumble": "#9966ff",
}


@dataclass
class LayerIssue:
    """An acoustically flagged defect at one specific second of one layer."""

    kind: str
    layer: str
    severity: float = 0.0  # 0.0-1.0 confidence of the defect

    @property
    def label(self) -> str:
        return ISSUE_LABELS.get(self.kind, self.kind.replace("_", " ").title())

    @property
    def color(self) -> str:
        return ISSUE_COLORS.get(self.kind, "#ff3366")


@dataclass
class LayerSegment:
    """One fixed-size slice of the timeline for a single second."""

    index: int
    start_s: float
    end_s: float
    levels: dict[str, float] = field(default_factory=dict)
    issues: list[LayerIssue] = field(default_factory=list)

    @property
    def primary_issue(self) -> LayerIssue | None:
        if not self.issues:
            return None
        return max(self.issues, key=lambda i: i.severity)


@dataclass
class LayerSource:
    """One separated source stem (its WAV path + per-second RMS envelope)."""

    name: str
    path: Path
    rms: np.ndarray  # (n_segments,) RMS in dBFS, clipped to [-60, 0]
    peak: np.ndarray  # (n_segments,) peak amplitude 0..1

    def level(self, segment_idx: int) -> float:
        """Normalized 0..1 level for a segment (for grid bar height)."""
        if segment_idx < 0 or segment_idx >= self.rms.shape[0]:
            return 0.0
        return float(np.clip((self.rms[segment_idx] + 60.0) / 60.0, 0.0, 1.0))


@dataclass
class LayerTrack:
    """Full-layer model for one separated track."""

    duration_s: float
    sample_rate: int
    segment_size_s: float = SEGMENT_SIZE_S
    sources: dict[str, LayerSource] = field(default_factory=dict)
    segments: list[LayerSegment] = field(default_factory=list)
    engine: str = "neural"

    @property
    def n_segments(self) -> int:
        return len(self.segments)

    @property
    def active_layers(self) -> list[str]:
        return [name for name in LAYER_ORDER[:-1] if name in self.sources]

    def segment_at(self, seconds: float) -> LayerSegment | None:
        idx = int(seconds // self.segment_size_s)
        if 0 <= idx < len(self.segments):
            return self.segments[idx]
        return None


# Long-track hardening (M3): budget + run-length rendering threshold
LONG_TRACK_SECONDS: float = 600.0
ANALYSIS_MS_PER_SECOND_BUDGET: float = 100.0  # generous ceiling for per-second analysis


@dataclass
class CellRun:
    """A maximal run of adjacent identical cells in one layer (run-length collapse)."""

    layer: str
    start_idx: int
    count: int
    level_bin: int  # 0..8 quantized level bucket
    op: str | None  # staged edit op, if any
    issue_kind: str | None  # primary issue kind covering the whole run, if any

    @property
    def end_idx(self) -> int:
        """Exclusive end segment index."""
        return self.start_idx + self.count


def _cell_identity(
    src: LayerSource,
    seg: LayerSegment,
    seg_idx: int,
    op_lookup: object | None,
) -> tuple[int, str | None, str | None]:
    """Tuple used to merge consecutive identical cells in one layer."""
    level = src.level(seg_idx)
    level_bin = min(8, int(round(level * 8)))
    issue = None
    for i in seg.issues:
        if i.layer == src.name:
            issue = i.kind
            break
    op = None
    if op_lookup is not None and hasattr(op_lookup, "get"):
        op = op_lookup.get(src.name, seg_idx)  # type: ignore[attr-defined]
    return level_bin, issue, op


def run_length_collapse(
    track: LayerTrack,
    edit_plan: object | None = None,
    split_at: set[int] | None = None,
) -> dict[str, list[CellRun]]:
    """Collapse identical adjacent cells into run-length cells per layer.

    Two cells merge when they share the same quantized level bucket, primary
    issue kind, and staged edit op. ``split_at`` forces a run boundary at the
    given segment indices (used to keep the playhead/selection cell standalone).
    """
    runs: dict[str, list[CellRun]] = {}
    boundaries: set[int] = set()
    if split_at:
        for idx in split_at:
            boundaries.add(idx)
            boundaries.add(idx + 1)
    for layer_name in track.active_layers:
        src = track.sources.get(layer_name)
        if src is None:
            continue
        row: list[CellRun] = []
        current: CellRun | None = None
        current_key: tuple[int, str | None, str | None] | None = None
        for seg_idx in range(track.n_segments):
            seg = track.segments[seg_idx]
            key = _cell_identity(src, seg, seg_idx, edit_plan)
            if current is not None and seg_idx not in boundaries and key == current_key:
                current.count += 1
                continue
            current = CellRun(
                layer=layer_name,
                start_idx=seg_idx,
                count=1,
                level_bin=key[0],
                op=key[2],
                issue_kind=key[1],
            )
            current_key = key
            row.append(current)
        runs[layer_name] = row
    return runs


def estimate_duration(path: Path) -> float:
    """Return audio duration in seconds using soundfile, falling back to wav header."""
    try:
        import soundfile as sf

        info = sf.info(str(path))
        return float(info.frames) / float(info.samplerate)
    except Exception as sf_err:
        logger.debug("soundfile duration failed for %s: %s", path, sf_err)
    try:
        import wave

        with wave.open(str(path), "rb") as wav:
            return wav.getnframes() / float(wav.getframerate())
    except Exception as wav_err:
        logger.debug("wave duration failed for %s: %s", path, wav_err)
    return 0.0


def compute_source_envelope(
    path: Path,
    sr: int,
    n_segments: int,
    segment_size_s: float = SEGMENT_SIZE_S,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute per-second RMS (dBFS, clipped to [-60, 0]) and peak amplitude
    envelopes for a stem file. Vectorized; loads only the needed samples.
    """
    import soundfile as sf

    data, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
    audio = data.T
    if sr != file_sr:
        sr = file_sr

    seg_len = int(segment_size_s * sr)
    target_samples = seg_len * n_segments
    if audio.shape[1] < target_samples:
        pad = np.zeros((audio.shape[0], target_samples - audio.shape[1]), dtype=np.float32)
        audio = np.concatenate([audio, pad], axis=1)
    else:
        audio = audio[:, :target_samples]

    mono = audio.mean(axis=0)
    segs = mono.reshape(n_segments, seg_len)

    rms = np.sqrt(np.mean(segs.astype(np.float64) ** 2, axis=1) + 1e-9)
    rms = np.clip(20.0 * np.log10(np.maximum(rms, 1e-6)), -60.0, 0.0).astype(np.float32)
    peak = np.max(np.abs(segs), axis=1).astype(np.float32)
    return rms, peak


def _load_segment(
    path: Path, seg_idx: int, segment_size_s: float, sr: int
) -> tuple[np.ndarray, int] | None:
    """Load one segment window as a 2D (channels, samples) floor-level mono array."""
    import soundfile as sf

    try:
        start = int(seg_idx * segment_size_s * sr)
        seg_len = int(segment_size_s * sr)
        data, file_sr = sf.read(
            str(path), dtype="float32", start=start, frames=seg_len, always_2d=True
        )
        if data.shape[0] == 0:
            return None
        audio = data.T
        return audio, file_sr
    except Exception as exc:
        logger.debug("segment load failed for %s: %s", path, exc)
        return None


def _band_db(mono: np.ndarray, sr: int, band: tuple[float, float]) -> float:
    """Mean spectral energy (dB) of one band using FFT windowing."""
    n = mono.shape[0]
    if n < 128:
        return -60.0
    winsz = min(2048, n)
    window = np.hanning(winsz)
    seg = mono[:winsz]
    mag = np.abs(np.fft.rfft(seg * window))
    freqs = np.fft.rfftfreq(winsz, d=1.0 / sr)
    mask = (freqs >= band[0]) & (freqs <= band[1])
    if not np.any(mask):
        return -60.0
    return float(20.0 * np.log10(np.mean(mag[mask]) + 1e-9))


def segment_band_level(
    path: Path,
    seg_idx: int,
    band: tuple[float, float],
    segment_size_s: float = SEGMENT_SIZE_S,
    sr: int | None = None,
    margin_s: float = 0.03,
) -> float:
    """In-band spectral level (dB) of one segment window.

    ``margin_s`` skips the leading/trailing fade zone so crossfade edges do
    not dilute the measured band energy (M3 de-bleed acceptance).
    """
    window = _load_segment(path, seg_idx, segment_size_s, sr or 44100)
    if window is None:
        return -60.0
    audio, file_sr = window
    mono = audio.mean(axis=0)
    if margin_s > 0.0:
        skip = int(margin_s * file_sr)
        if mono.shape[0] > 2 * skip:
            mono = mono[skip:-skip]
    if np.max(np.abs(mono)) <= 1e-4:
        return -60.0
    return _band_db(mono, file_sr, band)


def _detect_segment_issues(
    audio: np.ndarray, sr: int, source_name: str, envelope_db: float
) -> list[LayerIssue]:
    """Detect acoustic defects for one source stem in one second."""
    issues: list[LayerIssue] = []
    if audio.size == 0 or envelope_db < -55.0:
        return issues

    mono_energy_db = 20.0 * np.log10(np.sqrt(np.mean(audio.mean(0) ** 2)) + 1e-9)
    mono = audio.mean(axis=0)

    if source_name in ("bass", "drums", "other"):
        vocal_energy = _band_db(mono, sr, VOCAL_CORE_BAND)
        if vocal_energy > mono_energy_db + 6.0:
            sev = float(np.clip((vocal_energy - mono_energy_db - 6.0) / 18.0, 0.0, 1.0))
            issues.append(LayerIssue("vocal_bleed", source_name, round(sev, 3)))

    if source_name in ("vocals", "other") and audio.shape[0] > 1:
        side = audio[1] - audio[0]
        side_db = float(20.0 * np.log10(np.sqrt(np.mean(side**2)) + 1e-9))
        mid_db = float(20.0 * np.log10(np.sqrt(np.mean(audio.mean(0) ** 2)) + 1e-9))
        if side_db > mid_db + 4.0:
            sev = float(np.clip((side_db - mid_db - 4.0) / 15.0, 0.0, 1.0))
            issues.append(LayerIssue("whisper", source_name, round(sev, 3)))

    if source_name == "vocals":
        sib = _band_db(mono, sr, SIBILANCE_BAND)
        if sib > mono_energy_db + 8.0:
            sev = float(np.clip((sib - mono_energy_db - 8.0) / 18.0, 0.0, 1.0))
            issues.append(LayerIssue("sizzle", source_name, round(sev, 3)))

    if source_name in ("vocals", "other"):
        mud = _band_db(mono, sr, MUD_BAND)
        if mud > mono_energy_db + 8.0:
            sev = float(np.clip((mud - mono_energy_db - 8.0) / 16.0, 0.0, 1.0))
            issues.append(LayerIssue("mud", source_name, round(sev, 3)))

    if source_name in ("bass", "drums"):
        low = _band_db(mono, sr, LOW_END_BAND)
        if low > -24.0:
            sev = float(np.clip((low + 24.0) / 20.0, 0.0, 1.0))
            issues.append(LayerIssue("sub_rumble", source_name, round(sev, 3)))

    return issues


def build_layer_sources(
    stem_dir: Path,
    input_stem: str,
    mode: str,
    sample_rate: int = 44100,
    crossover_hz: float = 300.0,
    progress_callback: Callable[[float, str], None] | None = None,
) -> dict[str, Path]:
    """
    Assemble per-source stems from the raw neural cache in ``stem_dir``.

    For neural/ensemble modes, BS-RoFormer raw sources are LR4-blended against
    the HDEMUCS raw sources below ``crossover_hz`` (matching the merged output
    the user auditions in VOC/INST). Eco mode falls back to vocals + inst.

    On neural mode, the 4 stems are produced from the BS-RoFormer output
    (drums/bass/other/vocals) LR4-blended per-source. Returns a dict mapping
    source name -> WAV path (created on demand and cached on disk).
    """
    from harvester.analysis.enhancement.stem_separator import (
        _apply_lr4_crossover,
        load_audio_numpy,
        save_audio_numpy,
    )

    if progress_callback:
        progress_callback(1.0, "Layer Studio: resolving raw source stems...")

    suffix = f"{input_stem}_{mode}"
    ro_vocals = stem_dir / f"{suffix}_raw_vocals.wav"
    ro_bass = stem_dir / f"{suffix}_raw_bass.wav"
    ro_drums = stem_dir / f"{suffix}_raw_drums.wav"
    ro_other = stem_dir / f"{suffix}_raw_other.wav"
    hd_vocals = stem_dir / f"{suffix}_raw_vocals_hdemucs.wav"
    hd_bass = stem_dir / f"{suffix}_raw_bass_hdemucs.wav"
    hd_drums = stem_dir / f"{suffix}_raw_drums_hdemucs.wav"
    hd_other = stem_dir / f"{suffix}_raw_other_hdemucs.wav"

    eco_vocals = stem_dir / f"{suffix}_vocals.wav"
    eco_inst = stem_dir / f"{suffix}_instrumental.wav"

    layer_map: dict[str, tuple[Path | None, Path | None]] = {
        "vocals": (ro_vocals if ro_vocals.exists() else None, hd_vocals),
        "bass": (ro_bass if ro_bass.exists() else None, hd_bass),
        "drums": (ro_drums if ro_drums.exists() else None, hd_drums),
        "other": (ro_other if ro_other.exists() else None, hd_other),
    }

    sources: dict[str, Path] = {}
    for idx, (name, (ro_path, hd_path)) in enumerate(layer_map.items()):
        if progress_callback:
            progress_callback(
                5.0 + 12.0 * (idx / max(1, len(layer_map))),
                f"Layer Studio: blending {name} (LR4)...",
            )
        layer_path = stem_dir / f"{suffix}_layer_{name}.wav"
        if layer_path.exists() and layer_path.stat().st_size > 44:
            sources[name] = layer_path
            continue

        if ro_path is None:
            continue

        ro_audio, sr = load_audio_numpy(ro_path, target_sr=sample_rate)
        min_len = ro_audio.shape[1]
        blended = ro_audio
        if hd_path is not None and hd_path.exists():
            hd_audio, _ = load_audio_numpy(hd_path, target_sr=sample_rate)
            min_len = min(ro_audio.shape[1], hd_audio.shape[1])
            blended = _apply_lr4_crossover(
                hd_audio[:, :min_len], ro_audio[:, :min_len], sr=sr, crossover_hz=crossover_hz
            )
            del hd_audio
        save_audio_numpy(blended, layer_path, sr)
        del ro_audio, blended
        sources[name] = layer_path

    # Eco fallback: only vocals + inst are available; export a 2-layer track.
    if not sources and eco_inst.exists():
        if eco_vocals.exists():
            sources["vocals"] = eco_vocals
        sources["mix"] = eco_inst

    if progress_callback:
        progress_callback(18.0, "Layer Studio: source stems ready.")
    return sources


def analyze_layer_segments(
    sources: dict[str, Path],
    duration_s: float,
    sample_rate: int = 44100,
    segment_size_s: float = SEGMENT_SIZE_S,
    progress_callback: Callable[[float, str], None] | None = None,
) -> tuple[dict[str, LayerSource], list[LayerSegment]]:
    """
    Compute per-second envelopes for every source and per-second issue flags.

    Returns (sources_with_rms, segments). Each segment carries one row of the
    grid: per-layer levels and any detected issues for that exact second.
    """
    n_segments = max(1, int(np.ceil(duration_s / segment_size_s)))
    layer_sources: dict[str, LayerSource] = {}

    items = list(sources.items())
    for idx, (name, path) in enumerate(items):
        if progress_callback:
            progress_callback(
                20.0 + 55.0 * (idx / max(1, len(items))),
                f"Layer Studio: scanning {name} timing grid...",
            )
        rms, peak = compute_source_envelope(path, sample_rate, n_segments, segment_size_s)
        layer_sources[name] = LayerSource(name=name, path=path, rms=rms, peak=peak)

    if progress_callback:
        progress_callback(82.0, "Layer Studio: flagging acoustic issues...")

    segments: list[LayerSegment] = []
    for seg_idx in range(n_segments):
        start = seg_idx * segment_size_s
        end = min(duration_s, start + segment_size_s)
        seg = LayerSegment(index=seg_idx, start_s=start, end_s=end)
        if start >= duration_s:
            segments.append(seg)
            continue
        for name, src in layer_sources.items():
            if name == "mix":
                continue
            rms_db = float(src.rms[seg_idx]) if seg_idx < src.rms.shape[0] else 0.0
            seg.levels[name] = src.level(seg_idx)
            window = _load_segment(src.path, seg_idx, segment_size_s, sample_rate)
            if window is not None:
                win_audio, win_sr = window
                if np.max(np.abs(win_audio)) > 1e-4:
                    seg.issues.extend(_detect_segment_issues(win_audio, win_sr, name, rms_db))
        segments.append(seg)

    if progress_callback:
        progress_callback(100.0, "Layer Studio: timeline ready.")
    return layer_sources, segments


def build_layer_track(
    stem_dir: Path,
    input_stem: str,
    mode: str,
    duration_s: float,
    sample_rate: int = 44100,
    segment_size_s: float = SEGMENT_SIZE_S,
    crossover_hz: float = 300.0,
    progress_callback: Callable[[float, str], None] | None = None,
) -> LayerTrack:
    """Build a complete LayerTrack from a separated stem directory."""
    sources = build_layer_sources(
        stem_dir,
        input_stem,
        mode,
        sample_rate=sample_rate,
        crossover_hz=crossover_hz,
        progress_callback=progress_callback,
    )
    layer_sources, segments = analyze_layer_segments(
        sources,
        duration_s,
        sample_rate=sample_rate,
        segment_size_s=segment_size_s,
        progress_callback=progress_callback,
    )
    return LayerTrack(
        duration_s=duration_s,
        sample_rate=sample_rate,
        segment_size_s=segment_size_s,
        sources=layer_sources,
        segments=segments,
        engine=mode,
    )