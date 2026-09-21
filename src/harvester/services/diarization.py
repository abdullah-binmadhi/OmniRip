"""
Speaker diarization (pyannote) — the *measured* second opinion on singer count.

MusicBrainz credits stay authoritative (docs/13 D22/D27): they are documented,
deterministic, free and do not need a model. Diarization answers a different
question — "how many voices does this recording actually contain?" — and it
needs the optional ``diarize`` extra, downloaded weights, and it is measurably
unreliable on sung material:

- *Headlock*: 1 speaker measured, 2 credited (the backing vocal sits far under
  the lead).
- A controlled two-singer splice (two singers' isolated vocals alternating every
  10 s): 3 speakers at every clustering threshold tried (0.70 / 0.80 / 0.90).

So the measured count is **advisory** and never overwrites the credit count;
the lane plan carries both, labelled.

The pipeline prefers the official ``pyannote/speaker-diarization-community-1``
and falls back to the components it wraps (``segmentation-3.0`` + the wespeaker
embedding + ``AgglomerativeClustering``) when the gated pipeline repo is not
reachable with the configured token. Runs on CPU on purpose: Apple MPS fails
inside this pipeline (``invalid low watermark ratio 1.4``).
"""

from __future__ import annotations

import importlib.util
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "DIARIZE_DEVICE",
    "DIARIZE_MODEL",
    "HF_TOKEN_VAR",
    "SEGMENTATION_MODEL",
    "EMBEDDING_MODEL",
    "DiarizationResult",
    "Diarizer",
    "SpeakerTurn",
    "pyannote_available",
]

logger = logging.getLogger(__name__)

DIARIZE_MODEL = "pyannote/speaker-diarization-community-1"
SEGMENTATION_MODEL = "pyannote/segmentation-3.0"
EMBEDDING_MODEL = "pyannote/wespeaker-voxceleb-resnet34-LM"
DIARIZE_DEVICE = "cpu"
HF_TOKEN_VAR = "HF_TOKEN"

# The 3.1-era clustering block, used by the component fallback.
_AGGLOMERATIVE = {
    "segmentation": {"min_duration_off": 0.0},
    "clustering": {
        "method": "centroid",
        "min_cluster_size": 12,
        "threshold": 0.7045654963945794,
    },
}


def pyannote_available() -> bool:
    """True when the optional ``diarize`` extra is installed (no import cost)."""
    return importlib.util.find_spec("pyannote.audio") is not None


@dataclass(frozen=True, slots=True)
class SpeakerTurn:
    """One speech turn: when, how long, and which speaker."""

    start: float
    end: float
    speaker: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(slots=True)
class DiarizationResult:
    """Outcome of one diarization pass (advisory — see the module docstring)."""

    speakers: tuple[str, ...] = ()
    turns: tuple[SpeakerTurn, ...] = ()
    model: str = ""
    device: str = DIARIZE_DEVICE
    elapsed_s: float = 0.0
    speech_s: float = 0.0
    message: str = ""

    @property
    def speaker_count(self) -> int | None:
        """Distinct speakers, or None when nothing was measured."""
        return len(self.speakers) if self.speakers else None

    def describe(self) -> str:
        if self.speaker_count is None:
            return self.message or "speakers: nothing measured"
        return (
            f"Speakers (measured, advisory): {self.speaker_count} "
            f"[{self.model.rsplit('/', 1)[-1]}, {self.device}, {self.elapsed_s:.0f}s]"
        )


class Diarizer:
    """Lazy pyannote wrapper: load once, diarize a file, report a speaker count."""

    def __init__(
        self,
        *,
        model: str = DIARIZE_MODEL,
        device: str = DIARIZE_DEVICE,
        token: str | None = None,
        allow_component_fallback: bool = True,
    ) -> None:
        self.model = model
        self.device = device
        self._token = (token if token is not None else os.environ.get(HF_TOKEN_VAR, "")) or ""
        self.allow_component_fallback = allow_component_fallback
        self._pipeline: Any | None = None
        self._loaded_model = ""

    # -- loading ----------------------------------------------------------
    def _load_pipeline(self) -> tuple[Any, str]:
        """Load the official pipeline, else the components it wraps."""
        if self._pipeline is not None:
            return self._pipeline, self._loaded_model
        if not pyannote_available():
            raise RuntimeError("pyannote.audio is not installed (pip install '.[diarize]')")

        from pyannote.audio import Pipeline

        token = self._token or None
        try:
            pipeline = Pipeline.from_pretrained(self.model, token=token)
            self._pipeline, self._loaded_model = pipeline, self.model
            return pipeline, self._loaded_model
        except Exception as exc:
            if not self.allow_component_fallback:
                raise
            logger.info(
                "diarization pipeline %s unavailable (%s) — building it from components",
                self.model,
                type(exc).__name__,
            )
        self._pipeline, self._loaded_model = self._load_component_pipeline(token)
        return self._pipeline, self._loaded_model

    def _load_component_pipeline(self, token: str | None) -> tuple[Any, str]:
        """segmentation-3.0 + wespeaker embedding + AgglomerativeClustering."""
        import pyannote.audio.pipelines.speaker_diarization as speaker_diarization
        from pyannote.audio import Model
        from pyannote.audio.pipelines import SpeakerDiarization

        # The default PLDA calibration lives in the gated pipeline repo; PLDA is
        # optional for the agglomerative path (3.1-era pipelines ran without it).
        original = getattr(speaker_diarization, "get_plda", None)
        speaker_diarization.get_plda = lambda *args, **kwargs: None
        try:
            segmentation = Model.from_pretrained(SEGMENTATION_MODEL, token=token)
            embedding = Model.from_pretrained(EMBEDDING_MODEL, token=token)
            if segmentation is None or embedding is None:  # pragma: no cover - defensive
                raise RuntimeError("pyannote component models could not be loaded")
            pipeline = SpeakerDiarization(
                segmentation=segmentation,
                embedding=embedding,
                plda="",
                clustering="AgglomerativeClustering",
            )
            pipeline.instantiate(_AGGLOMERATIVE)
        finally:
            if original is not None:
                speaker_diarization.get_plda = original
        return pipeline, f"{SEGMENTATION_MODEL}+{EMBEDDING_MODEL.split('/')[-1]}"

    # -- work -------------------------------------------------------------
    def diarize(
        self,
        source: Path,
        *,
        max_seconds: float = 0.0,
        num_speakers: int | None = None,
        progress: Callable[[float, str], None] | None = None,
    ) -> DiarizationResult:
        """Measure speakers in ``source`` (mono downmix, CPU by default)."""
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"audio not found: {source}")

        def _progress(pct: float, step: str) -> None:
            if progress is not None:
                progress(pct, step)

        _progress(5.0, "loading diarization models…")
        pipeline, loaded = self._load_pipeline()
        if self.device and self.device != "cpu":
            try:
                import torch

                pipeline.to(torch.device(self.device))
            except Exception as exc:
                logger.info("diarization device %s unusable (%s) — using CPU", self.device, exc)
                self.device = "cpu"

        import numpy as np
        import torch

        from harvester.analysis.enhancement.stem_separator import load_audio_numpy

        _progress(15.0, "loading audio…")
        audio, sample_rate = load_audio_numpy(source)
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim == 2:
            audio = audio.mean(axis=0)
        if max_seconds and max_seconds > 0:
            audio = audio[: int(max_seconds * sample_rate)]
        waveform = torch.from_numpy(audio).unsqueeze(0)

        _progress(25.0, "diarizing (this can take a while)…")
        started = time.perf_counter()
        kwargs: dict[str, Any] = {}
        if num_speakers:
            kwargs["num_speakers"] = int(num_speakers)
        output = pipeline({"waveform": waveform, "sample_rate": sample_rate}, **kwargs)
        elapsed = time.perf_counter() - started

        annotation = getattr(output, "speaker_diarization", None)
        if annotation is None:
            annotation = getattr(output, "exclusive_speaker_diarization", None) or output
        turns = tuple(
            SpeakerTurn(start=float(seg.start), end=float(seg.end), speaker=str(label))
            for seg, _, label in annotation.itertracks(yield_label=True)
        )
        speakers = tuple(sorted({turn.speaker for turn in turns}))
        result = DiarizationResult(
            speakers=speakers,
            turns=turns,
            model=loaded,
            device=self.device,
            elapsed_s=elapsed,
            speech_s=sum(turn.duration for turn in turns),
        )
        _progress(100.0, result.describe())
        return result

    def close(self) -> None:
        self._pipeline = None
        self._loaded_model = ""
