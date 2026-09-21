"""
Layer Terminal sidecar — JSON IPC between the main app and the detached
layer terminal window.

Two channels live side by side on disk:

1. **Sidecar** (``layer_sidecar.json``) — the ``LayerTrack`` plus the pending
   ``EditPlan``. The main app writes it, the detached terminal stages edits on
   top of it and writes them back for the main app to apply.
2. **Transport** (``layer_sidecar.transport.json``) — the live playhead /
   playing state the main app owns (it owns audio output) plus the terminal-on
   the-main-app requests (seek / play-pause). Polled at ~5 Hz both ways, so the
   detached timeline moves with the song and can drive playback.

Pure ``json``/``pathlib``/``dataclasses`` — no third-party dependencies.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from harvester.analysis.enhancement.lane_plan import decode_plan, encode_plan
from harvester.analysis.enhancement.layer_editor import EditPlan
from harvester.analysis.enhancement.layers import (
    LayerIssue,
    LayerSegment,
    LayerSource,
    LayerTrack,
)

SCHEMA_VERSION = 2
TRANSPORT_SCHEMA_VERSION = 1

# EditPlan cell keys (layer, segment_idx) are serialized to "layer:idx" strings.
_CELL_KEY_SEP = ":"


@dataclass(frozen=True, slots=True)
class TransportState:
    """Live playback state (main app → terminal) and requests (terminal → app)."""

    playhead_s: float = 0.0
    playing: bool = False
    duration_s: float = 0.0
    seek_request: float | None = None
    play_request: bool | None = None
    written_at: float = 0.0


def _updated(state: TransportState, **changes: object) -> TransportState:
    """Copy the state with fresh fields, keeping any untouched pending request."""
    return replace(state, written_at=time.time(), **changes)  # type: ignore[arg-type]


def transport_path(sidecar_path: Path) -> Path:
    """``…/layer_sidecar.json`` → ``…/layer_sidecar.transport.json``."""
    sidecar_path = Path(sidecar_path)
    return sidecar_path.with_name(f"{sidecar_path.stem}.transport.json")


def write_transport(path: Path, state: TransportState) -> None:
    """Atomically publish the transport state (readers never see a torn file)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": TRANSPORT_SCHEMA_VERSION,
        "playhead_s": round(float(state.playhead_s), 3),
        "playing": bool(state.playing),
        "duration_s": round(float(state.duration_s), 3),
        "seek_request": None if state.seek_request is None else round(float(state.seek_request), 3),
        "play_request": state.play_request,
        "written_at": float(state.written_at or time.time()),
    }
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def read_transport(path: Path) -> TransportState:
    """Read the transport state; a missing/corrupt/stale file reads as idle."""
    path = Path(path)
    if not path.exists():
        return TransportState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return TransportState()
    if not isinstance(data, dict):
        return TransportState()

    def _float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    def _optional_float(value: object) -> float | None:
        if value is None:
            return None
        return _float(value)

    play_request = data.get("play_request")
    return TransportState(
        playhead_s=max(0.0, _float(data.get("playhead_s"))),
        playing=bool(data.get("playing")),
        duration_s=max(0.0, _float(data.get("duration_s"))),
        seek_request=_optional_float(data.get("seek_request")),
        play_request=None if play_request is None else bool(play_request),
        written_at=_float(data.get("written_at")),
    )


def request_seek(sidecar_path: Path, seconds: float) -> TransportState:
    """Terminal → main app: jump playback to ``seconds``."""
    path = transport_path(sidecar_path)
    state = _updated(read_transport(path), seek_request=max(0.0, float(seconds)))
    write_transport(path, state)
    return state


def request_play_state(sidecar_path: Path, play: bool) -> TransportState:
    """Terminal → main app: start or pause playback."""
    path = transport_path(sidecar_path)
    state = _updated(read_transport(path), play_request=bool(play))
    write_transport(path, state)
    return state


def consume_requests(sidecar_path: Path) -> tuple[float | None, bool | None]:
    """Main app: take the pending seek/play request and clear it atomically."""
    path = transport_path(sidecar_path)
    state = read_transport(path)
    if state.seek_request is None and state.play_request is None:
        return None, None
    write_transport(path, _updated(state, seek_request=None, play_request=None))
    return state.seek_request, state.play_request


def _encode_plan(edit_plan: EditPlan | dict[tuple[str, int], str]) -> dict[str, str]:
    """Flatten an EditPlan (or a {cell: op} dict) into a JSON-safe string map."""
    if isinstance(edit_plan, EditPlan):
        cells = edit_plan.edits
    else:
        cells = edit_plan or {}
    return {
        f"{layer}{_CELL_KEY_SEP}{seg_idx}": op for (layer, seg_idx), op in cells.items()
    }


def _decode_plan(data: dict[str, str]) -> dict[tuple[str, int], str]:
    """Rehydrate the sidecar's string-keyed plan into {cell: op} tuples."""
    plan: dict[tuple[str, int], str] = {}
    for key, op in (data or {}).items():
        layer, _, seg = key.partition(_CELL_KEY_SEP)
        try:
            plan[(layer, int(seg))] = op
        except (TypeError, ValueError):
            continue
    return plan


def _encode_issue(issue: LayerIssue) -> dict[str, object]:
    return {"kind": issue.kind, "layer": issue.layer, "severity": issue.severity}


def _encode_segment(seg: LayerSegment) -> dict[str, object]:
    return {
        "index": seg.index,
        "start_s": seg.start_s,
        "end_s": seg.end_s,
        "levels": {name: float(level) for name, level in seg.levels.items()},
        "issues": [_encode_issue(i) for i in seg.issues],
    }


def _encode_source(src: LayerSource) -> dict[str, object]:
    return {
        "name": src.name,
        "path": str(src.path),
        "rms": [float(v) for v in src.rms],
        "peak": [float(v) for v in src.peak],
    }


def write_sidecar(
    track: LayerTrack, edit_plan: EditPlan | dict[tuple[str, int], str], path: Path
) -> None:
    """Serialize a LayerTrack + pending edit plan to the JSON sidecar."""
    payload = {
        "version": SCHEMA_VERSION,
        "duration_s": track.duration_s,
        "sample_rate": track.sample_rate,
        "segment_size_s": track.segment_size_s,
        "engine": track.engine,
        "sources": {
            name: _encode_source(src) for name, src in track.sources.items()
        },
        "layer_order": list(track.active_layers),
        # Lane provenance (docs/13): origin + confidence + note per lane, so the
        # detached terminal labels rows exactly like the workbench does.
        "lane_plan": encode_plan(track.lane_plan),
        "singer_count": None if track.lane_plan is None else track.lane_plan.singer_count,
        "credit_instruments": (
            [] if track.lane_plan is None else list(track.lane_plan.credit_instruments)
        ),
        "tag_labels": [] if track.lane_plan is None else list(track.lane_plan.tag_labels),
        "segments": [_encode_segment(seg) for seg in track.segments],
        "edit_plan": _encode_plan(edit_plan),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_sidecar(path: Path) -> tuple[LayerTrack, dict[tuple[str, int], str]]:
    """Deserialize a LayerTrack + edit plan from the JSON sidecar.

    Raises:
        FileNotFoundError: the sidecar file does not exist.
        ValueError: the sidecar carries an unsupported schema version.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Layer sidecar not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))

    version = data.get("version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported layer sidecar version {version!r} (expected {SCHEMA_VERSION})."
        )

    sources: dict[str, LayerSource] = {}
    for name, s in (data.get("sources") or {}).items():
        sources[name] = LayerSource(
            name=name,
            path=Path(s["path"]),
            rms=np.asarray(s.get("rms", []), dtype=np.float32),
            peak=np.asarray(s.get("peak", []), dtype=np.float32),
        )
    # Re-insert in the main app's detection order (JSON sorts keys), so dynamic
    # lanes keep their lane order across the sidecar hop.
    order = [str(name) for name in (data.get("layer_order") or []) if str(name) in sources]
    if order:
        sources = {name: sources[name] for name in order} | {
            name: src for name, src in sources.items() if name not in set(order)
        }

    segments: list[LayerSegment] = []
    for seg in data.get("segments") or []:
        issues = [
            LayerIssue(kind=i["kind"], layer=i["layer"], severity=float(i.get("severity", 0.0)))
            for i in seg.get("issues") or []
        ]
        segments.append(
            LayerSegment(
                index=int(seg["index"]),
                start_s=float(seg.get("start_s", 0.0)),
                end_s=float(seg.get("end_s", 0.0)),
                levels={name: float(v) for name, v in (seg.get("levels") or {}).items()},
                issues=issues,
            )
        )

    plan = decode_plan(
        data.get("lane_plan"),
        singer_count=data.get("singer_count"),
        credit_instruments=data.get("credit_instruments") or (),
        tag_labels=data.get("tag_labels") or (),
    )
    track = LayerTrack(
        duration_s=float(data.get("duration_s", 0.0)),
        sample_rate=int(data.get("sample_rate", 44100)),
        segment_size_s=float(data.get("segment_size_s", 1.0)),
        sources=sources,
        segments=segments,
        engine=str(data.get("engine", "neural")),
        lane_plan=plan,
    )
    return track, _decode_plan(data.get("edit_plan") or {})