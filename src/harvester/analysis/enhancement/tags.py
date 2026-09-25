"""
CLAP instrument/vocal tagging — advisory lane labels (docs/13, D25).

The tagger answers one question the separators cannot: *what is audible in this
song that no stem renders* (strings, sax, choir, a second singer). Its output is
advisory by construction:

- It never touches the spectral verdict, the tagging metadata or the mix — those
  stay deterministic (docs/01). Tags only add provenance rows to the lane plan.
- It is a "press button, wait" neural stage like separation, never part of the
  live 100 ms/s analysis budget.
- Torch/transformers are imported lazily inside the methods, so importing this
  module stays free.

Model: ``laion/clap-htsat-unfused`` (CLAP, 48 kHz input, ~614 MB). The weights
are cached once through :class:`~harvester.services.model_manager.ModelManager`
under the OmniRip model cache and loaded from there; a missing dependency, a
failed download or a scoring error degrades to ``None`` (no tags), never an
exception.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harvester.processing import TAG_THRESHOLD

logger = logging.getLogger(__name__)

__all__ = [
    "LABEL_PROMPTS",
    "TAGS_FILENAME",
    "TAGS_SCHEMA_VERSION",
    "TAG_MAX_LABELS",
    "TAG_MAX_WINDOWS",
    "TAG_THRESHOLD",
    "TAG_WINDOW_S",
    "ClapTagger",
    "TagResult",
    "labels_for_threshold",
    "read_tags",
    "store_tags",
    "tagged_labels",
    "window_bounds",
]

TAG_MODEL_REPO = "laion/clap-htsat-unfused"
TAG_WINDOW_S = 5.0
TAG_MAX_WINDOWS = 24  # evenly spaced windows; bounds the cost on long tracks
TAG_MAX_LABELS = 8  # cap on tag rows so the plan stays readable
# CLAP runs on CPU on purpose: its BatchNorm raises "Placeholder storage has not
# been allocated on MPS device!" on Apple MPS (measured), and the model is small
# enough that CPU tagging stays a few seconds per track. A non-CPU device is
# still allowed (and falls back to CPU on failure) for future/other backends.
TAG_DEVICE = "cpu"
TAGS_FILENAME = "tags.json"
TAGS_SCHEMA_VERSION = 1

# (label, text prompt). CLAP is zero-shot: the prompt wording is the label.
# Labels are deliberately coarse and mapped onto lane keys by
# content labelling: advisory track-level labels shown in Track Info
# render it, and becomes a "tags only" row when none can.
LABEL_PROMPTS: tuple[tuple[str, str], ...] = (
    ("drums", "drums and percussion playing a beat"),
    ("bass", "a bass guitar or bass synthesizer playing a bassline"),
    ("guitar", "an electric or acoustic guitar"),
    ("piano", "a piano or electric piano"),
    ("synth", "a synthesizer or keyboard pad"),
    ("strings", "a string section of violins, violas and cellos"),
    ("brass", "a brass or saxophone section"),
    ("flute", "a flute or woodwind instrument"),
    ("lead vocals", "a lead singer singing the melody"),
    ("backing vocals", "backing singers or a choir"),
    ("male vocals", "a man singing"),
    ("female vocals", "a woman singing"),
)


def window_bounds(
    duration_s: float,
    window_s: float = TAG_WINDOW_S,
    max_windows: int = TAG_MAX_WINDOWS,
) -> tuple[tuple[float, float], ...]:
    """Evenly spaced analysis windows covering a track, capped at ``max_windows``.

    Deterministic and dependency-free so the cost of a tagging pass can be
    reasoned about (and tested) without loading a model.
    """
    if duration_s <= 0 or window_s <= 0 or max_windows <= 0:
        return ()
    if duration_s <= window_s:
        return ((0.0, float(duration_s)),)
    span = duration_s - window_s
    hop = max(window_s, span / max(1, max_windows - 1))
    bounds: list[tuple[float, float]] = []
    start = 0.0
    while start < duration_s - 1e-9 and len(bounds) < max_windows:
        end = min(duration_s, start + window_s)
        bounds.append((start, end))
        if end >= duration_s - 1e-9:
            break
        start += hop
    return tuple(bounds)


@dataclass(frozen=True, slots=True)
class TagResult:
    """Audible-content labels for one track, with the scores behind them."""

    labels: tuple[str, ...] = ()
    scores: dict[str, float] | None = None
    windows: int = 0
    window_s: float = TAG_WINDOW_S
    threshold: float = TAG_THRESHOLD
    model: str = TAG_MODEL_REPO

    @property
    def score_map(self) -> dict[str, float]:
        return dict(self.scores or {})

    def describe(self) -> str:
        """One-line account for the status line / plan note."""
        if not self.labels:
            return "no extra instrumentation tagged"
        scored = self.score_map
        parts = [
            f"{label} {scored[label]:.2f}" if label in scored else label for label in self.labels
        ]
        return "tagged: " + ", ".join(parts)

    def to_payload(self) -> dict[str, object]:
        return {
            "version": TAGS_SCHEMA_VERSION,
            "model": self.model,
            "window_s": self.window_s,
            "windows": self.windows,
            "threshold": self.threshold,
            "labels": list(self.labels),
            "scores": {k: round(float(v), 4) for k, v in self.score_map.items()},
        }

    @classmethod
    def from_payload(cls, data: object) -> TagResult | None:
        """Rehydrate from ``tags.json`` (unknown shape → ``None``)."""
        if not isinstance(data, dict):
            return None
        labels = tuple(str(label) for label in (data.get("labels") or []) if str(label).strip())
        raw_scores = data.get("scores") or {}
        scores: dict[str, float] = {}
        if isinstance(raw_scores, dict):
            for key, value in raw_scores.items():
                try:
                    scores[str(key)] = float(value)
                except (TypeError, ValueError):
                    continue
        try:
            window_s = float(data.get("window_s", TAG_WINDOW_S))
        except (TypeError, ValueError):
            window_s = TAG_WINDOW_S
        try:
            threshold = float(data.get("threshold", TAG_THRESHOLD))
        except (TypeError, ValueError):
            threshold = TAG_THRESHOLD
        try:
            windows = int(data.get("windows", 0))
        except (TypeError, ValueError):
            windows = 0
        return cls(
            labels=labels,
            scores=scores,
            windows=windows,
            window_s=window_s,
            threshold=threshold,
            model=str(data.get("model", TAG_MODEL_REPO) or TAG_MODEL_REPO),
        )


def store_tags(stem_dir: Path, result: TagResult) -> Path:
    """Write ``tags.json`` next to the stems (atomic replace)."""
    stem_dir = Path(stem_dir)
    stem_dir.mkdir(parents=True, exist_ok=True)
    path = stem_dir / TAGS_FILENAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result.to_payload(), indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return path


def read_tags(stem_dir: Path | None) -> TagResult | None:
    """Read ``tags.json`` from a stem directory, if a previous pass wrote one."""
    if stem_dir is None:
        return None
    path = Path(stem_dir) / TAGS_FILENAME
    if not path.exists():
        return None
    try:
        return TagResult.from_payload(json.loads(path.read_text(encoding="utf-8")))
    except Exception as exc:  # pragma: no cover - defensive
        logger.info("tags.json unreadable (%s); ignoring tags.", exc)
        return None


def tagged_labels(stem_dir: Path | None) -> tuple[str, ...]:
    """Labels for the lane plan, or ``()`` when nothing was tagged."""
    result = read_tags(stem_dir)
    return result.labels if result is not None else ()


class ClapTagger:
    """Runs the CLAP zero-shot tagger over evenly spaced windows of a track."""

    def __init__(
        self,
        *,
        cache_dir: Path | None = None,
        threshold: float = TAG_THRESHOLD,
        max_labels: int = TAG_MAX_LABELS,
        max_windows: int = TAG_MAX_WINDOWS,
        window_s: float = TAG_WINDOW_S,
        model_repo: str = TAG_MODEL_REPO,
        device: str = TAG_DEVICE,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.threshold = float(threshold)
        self.max_labels = int(max_labels)
        self.max_windows = int(max_windows)
        self.window_s = float(window_s)
        self.model_repo = model_repo
        self.device = device

    # -- model ---------------------------------------------------------------

    def available(self) -> bool:
        """True when the tagging stack can be imported at all."""
        try:
            import transformers  # noqa: F401
        except Exception as exc:
            logger.info("CLAP tagging unavailable (%s).", exc)
            return False
        return True

    def _model_dir(self) -> Path | None:
        """Local snapshot directory for the CLAP repo (downloaded once)."""
        from harvester.services.model_manager import ModelManager

        manager = ModelManager(self.cache_dir)
        target = manager.cache_dir / self.model_repo.split("/")[-1]
        if (target / "config.json").exists() and any(
            (target / name).exists() for name in ("pytorch_model.bin", "model.safetensors")
        ):
            return target
        try:
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=self.model_repo,
                local_dir=str(target),
                allow_patterns=[
                    "config.json",
                    "preprocessor_config.json",
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                    "vocab.json",
                    "merges.txt",
                    "*.bin",
                    "*.safetensors",
                ],
            )
        except Exception as exc:
            logger.info("CLAP download failed (%s); skipping tags.", exc)
            return None
        if not (target / "config.json").exists():
            return None
        return target

    def _load_model(self) -> tuple[Any, Any] | None:
        """Load the CLAP model + processor from the local snapshot."""
        try:
            from transformers import ClapModel, ClapProcessor
        except Exception as exc:
            logger.info("transformers CLAP classes unavailable (%s); skipping tags.", exc)
            return None
        local_dir = self._model_dir()
        if local_dir is None:
            return None
        try:
            model = ClapModel.from_pretrained(str(local_dir))
            processor = ClapProcessor.from_pretrained(str(local_dir))
        except Exception as exc:
            logger.info("CLAP load failed (%s); skipping tags.", exc)
            return None
        model.eval()
        return model, processor

    # -- scoring -------------------------------------------------------------

    def _score_windows(
        self, model: Any, processor: Any, windows: list[Any], sample_rate: int, device: str
    ) -> list[dict[str, float]]:
        """Per-window label scores: the softmax *share* of each label.

        CLAP similarities are not calibrated probabilities, so a raw sigmoid
        would report "0.5" for labels the model has no opinion about. The share
        of the label mass is self-normalising instead: a clearly present
        instrument takes most of the mass, an unknown track spreads it evenly
        (1/12 ≈ 8 %) and therefore reports nothing.
        """
        import torch

        prompts = [prompt for _, prompt in LABEL_PROMPTS]
        text_inputs = processor(text=prompts, return_tensors="pt", padding=True)
        try:
            audio_inputs = processor(audio=windows, sampling_rate=sample_rate, return_tensors="pt")
        except (TypeError, ValueError):
            # transformers < 5 spells this argument ``audios``.
            audio_inputs = processor(
                audios=windows, sampling_rate=sample_rate, return_tensors="pt"
            )
        input_ids = text_inputs["input_ids"].to(device)
        text_mask = text_inputs.get("attention_mask")
        features = audio_inputs["input_features"].to(device)
        longer = audio_inputs.get("is_longer")
        if longer is None:
            longer = torch.zeros(features.shape[0], dtype=torch.bool)
        with torch.no_grad():
            out = model(
                input_features=features,
                is_longer=longer.to(device),
                input_ids=input_ids,
                attention_mask=None if text_mask is None else text_mask.to(device),
            )
        logits = out.logits_per_audio
        shares = torch.softmax(logits.float(), dim=-1).detach().cpu().numpy()
        rows: list[dict[str, float]] = []
        for row in shares:
            rows.append(
                {
                    label: float(row[index])
                    for index, (label, _prompt) in enumerate(LABEL_PROMPTS)
                }
            )
        return rows

    def tag_file(
        self,
        path: Path,
        *,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> TagResult | None:
        """Tag a whole file. Returns ``None`` when tagging is unavailable."""
        from harvester.analysis.enhancement.stem_separator import load_audio_numpy

        path = Path(path)
        if not path.exists():
            return None

        loaded = self._load_model()
        if loaded is None:
            return None
        model, processor = loaded

        try:
            audio, sample_rate = load_audio_numpy(path, target_sr=48000)
        except Exception as exc:
            logger.info("tagging could not read %s (%s).", path, exc)
            return None
        if getattr(audio, "ndim", 1) > 1:
            import numpy as np

            audio = np.asarray(audio).mean(axis=0)
        duration = float(len(audio)) / float(sample_rate or 48000)
        bounds = window_bounds(duration, self.window_s, self.max_windows)
        if not bounds:
            return None

        windows = [
            audio[int(start * sample_rate) : int(end * sample_rate)] for start, end in bounds
        ]
        if progress_callback:
            progress_callback(5.0, f"Tagging: scoring {len(windows)} window(s)…")

        device = self.device or TAG_DEVICE
        try:
            rows = self._score_windows(model, processor, windows, sample_rate, device)
        except Exception as exc:
            if device == "cpu":
                logger.info("CLAP scoring failed (%s); skipping tags.", exc)
                return None
            logger.info("CLAP scoring failed on %s (%s); retrying on CPU.", device, exc)
            try:
                rows = self._score_windows(model, processor, windows, sample_rate, "cpu")
            except Exception as cpu_exc:
                logger.info("CLAP scoring failed on CPU too (%s); skipping tags.", cpu_exc)
                return None

        if not rows:
            return None
        means: dict[str, float] = {}
        for label, _prompt in LABEL_PROMPTS:
            means[label] = sum(row.get(label, 0.0) for row in rows) / len(rows)
        kept = labels_for_threshold(means, self.threshold, self.max_labels)
        result = TagResult(
            labels=tuple(kept),
            scores={label: means[label] for label in means},
            windows=len(rows),
            window_s=self.window_s,
            threshold=self.threshold,
            model=self.model_repo,
        )
        if progress_callback:
            progress_callback(100.0, f"Tags ready — {result.describe()}.")
        return result

    def tag_and_store(
        self,
        path: Path,
        stem_dir: Path,
        *,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> TagResult | None:
        """Tag a file and persist the result as ``tags.json`` in ``stem_dir``."""
        result = self.tag_file(path, progress_callback=progress_callback)
        if result is None:
            return None
        store_tags(stem_dir, result)
        return result


def labels_for_threshold(scores: dict[str, float], threshold: float, limit: int) -> tuple[str, ...]:
    """Labels at or above ``threshold``, best first, capped at ``limit``."""
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return tuple(label for label, score in ordered[:limit] if score >= threshold)
