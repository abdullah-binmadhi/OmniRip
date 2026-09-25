"""Guided repair executor (docs/01 D35).

Turns a ``RepairPlan`` into three deliverables — an enhanced repaired master,
a clean acapella and a clean instrumental (karaoke) — reusing the existing
separation, remediation and enhancement engines:

1. Separate (cached) when stems are needed.
2. Sanity-check the LR4 recombination identity against the decoded source.
3. Apply each enabled symptom's operation to its target stem, whole-track or
   over the chosen sections, with click-free crossfades.
4. Recombine the edited stems into the repaired stereo mix.
5. Enhance the repaired mix and write MP3 + provenance tags; write the two
   stems as 32-bit PCM WAV.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from harvester.analysis.enhancement.eq import (
    MasteringEQSettings,
    apply_mastering_eq,
    is_flat,
)
from harvester.analysis.enhancement.presets import PRESETS, EnhancementPreset
from harvester.analysis.enhancement.repair_ops import (
    load_stereo,
    render_ranges,
    verify_reconstruction,
    write_pcm32,
)
from harvester.analysis.enhancement.repair_plan import (
    OUTPUT_INST,
    OUTPUT_MASTER,
    OUTPUT_VOCALS,
    TARGET_INST,
    TARGET_VOCALS,
    RepairPlan,
    op_for,
)

logger = logging.getLogger(__name__)

ProgressFn = Callable[[float, str], None]
SeparateFn = Callable[[Path, RepairPlan, Path, ProgressFn | None], tuple[Path, Path]]

ENHANCEMENT_SAMPLE_RATE: int = 48000


@dataclass(frozen=True, slots=True)
class RepairResult:
    """Where the three deliverables landed, plus QC notes."""

    master: Path | None
    vocals: Path | None
    inst: Path | None
    residual_worst_db: float | None
    notes: tuple[str, ...]


def _default_separate(
    source: Path,
    plan: RepairPlan,
    stem_dir: Path,
    progress: ProgressFn | None,
) -> tuple[Path, Path]:
    from harvester.analysis.enhancement.stem_separator import StemSeparator

    separator = StemSeparator()
    result = separator.separate_file(
        source,
        output_dir=stem_dir,
        mode="ensemble",
        progress_callback=progress,
        bs_roformer_weight=plan.blend_weight if plan.blend_weight is not None else 0.70,
        dereverb_intensity=0.0,
        vocal_flags="natural",
        inst_flags="natural",
        force_reseparate=False,
    )
    return result.vocals_path, result.instrumental_path


def _report(progress: ProgressFn | None, pct: float, step: str) -> None:
    if progress is not None:
        progress(pct, step)


def execute_repair(
    source: Path,
    plan: RepairPlan,
    *,
    output_dir: Path,
    sample_rate: int = 44100,
    cutoff_hz: float = 15500.0,
    stem_dir: Path | None = None,
    separate: SeparateFn | None = None,
    exporter: object | None = None,
    eq_by_target: Mapping[str, MasteringEQSettings] | None = None,
    master_preset: EnhancementPreset | None = None,
    extra_tags: Mapping[str, str] | None = None,
    progress: ProgressFn | None = None,
) -> RepairResult:
    """Run a repair plan and write the three deliverables into ``output_dir``."""
    from harvester.analysis.enhancement.segment_analysis import estimate_duration

    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    duration_s = estimate_duration(source)
    problems = plan.validate(duration_s)
    if problems:
        raise ValueError("Invalid repair plan: " + "; ".join(problems))

    notes: list[str] = []
    vocals_path: Path | None = None
    inst_path: Path | None = None
    vocals_audio: np.ndarray | None = None
    inst_audio: np.ndarray | None = None
    residual_worst: float | None = None

    if plan.needs_stems():
        from harvester.analysis.enhancement.stem_separator import stem_dir_for

        stem_dir = Path(stem_dir) if stem_dir is not None else stem_dir_for(source)
        _report(progress, 10.0, "Repair: separating vocals and instrumental...")
        separate_fn = separate or _default_separate
        vocals_path, inst_path = separate_fn(source, plan, stem_dir, progress)
        vocals_audio, stem_sr = load_stereo(vocals_path)
        inst_audio, _ = load_stereo(inst_path)
        sample_rate = stem_sr

        if exporter is None:
            from harvester.services.enhancement.exporter import EnhancementExporter

            exporter = EnhancementExporter()
        reference = exporter.decode_audio_ffmpeg(source, sample_rate=sample_rate)
        reference_mono = reference.mean(axis=0)
        residual_worst, violating = verify_reconstruction(
            reference_mono,
            {"vocals": vocals_path, "inst": inst_path},
            sample_rate=sample_rate,
        )
        notes.append(f"Stem recombination residual: worst {residual_worst:.1f} dBFS/segment")
        if violating:
            notes.append(f"WARNING: {len(violating)} segment(s) exceeded the reconstruction budget")

        _report(progress, 45.0, "Repair: applying fixes to the selected sections...")
        for spec in plan.enabled():
            choice = plan.choices.get(spec.key)
            if choice is None or not choice.enabled:
                continue
            seg_fn = op_for(spec.key, choice.intensity)
            if seg_fn is None:
                continue
            for target in spec.targets:
                if target == TARGET_VOCALS and vocals_audio is not None:
                    vocals_audio = render_ranges(vocals_audio, sample_rate, choice.ranges, seg_fn)
                elif target == TARGET_INST and inst_audio is not None:
                    inst_audio = render_ranges(inst_audio, sample_rate, choice.ranges, seg_fn)
            notes.append(f"{spec.label}: applied{' (sections)' if choice.ranges else ' (whole track)'}")

    vocals_export = vocals_audio
    inst_export = inst_audio
    if eq_by_target:
        vocals_eq = eq_by_target.get("vocals")
        if vocals_export is not None and vocals_eq is not None and not is_flat(vocals_eq):
            vocals_export = apply_mastering_eq(vocals_export, vocals_eq, sample_rate=sample_rate)
            notes.append("Vocals stem EQ applied")
        inst_eq = eq_by_target.get("instrumental")
        if inst_export is not None and inst_eq is not None and not is_flat(inst_eq):
            inst_export = apply_mastering_eq(inst_export, inst_eq, sample_rate=sample_rate)
            notes.append("Instrumental stem EQ applied")

    if OUTPUT_VOCALS in plan.outputs and vocals_export is not None:
        dest = output_dir / f"{source.stem}_vocals.wav"
        write_pcm32(vocals_export, dest, sample_rate)
        vocals_out: Path | None = dest
    else:
        vocals_out = None

    if OUTPUT_INST in plan.outputs and inst_export is not None:
        dest = output_dir / f"{source.stem}_instrumental.wav"
        write_pcm32(inst_export, dest, sample_rate)
        inst_out: Path | None = dest
    else:
        inst_out = None

    master_out: Path | None = None
    if OUTPUT_MASTER in plan.outputs:
        if vocals_audio is not None and inst_audio is not None:
            n = min(vocals_audio.shape[1], inst_audio.shape[1])
            master_audio = (vocals_audio[:, :n] + inst_audio[:, :n]).astype(np.float32)
        else:
            if exporter is None:
                from harvester.services.enhancement.exporter import EnhancementExporter

                exporter = EnhancementExporter()
            master_audio = exporter.decode_audio_ffmpeg(source, sample_rate=sample_rate)

        from harvester.analysis.enhancement.dsp import resample_audio

        enhanced_source = resample_audio(master_audio, sample_rate, ENHANCEMENT_SAMPLE_RATE)
        preset: EnhancementPreset = master_preset or PRESETS.get(
            plan.enhance_preset_id, PRESETS["fast_balanced"]
        )
        _report(progress, 75.0, f"Repair: rendering enhanced master ({preset.name})...")
        enhanced = exporter.render_audio_buffer(
            enhanced_source,
            preset=preset,
            cutoff_hz=cutoff_hz,
            eq_settings=(eq_by_target or {}).get("master"),
            progress_callback=progress,
        )
        master_out = output_dir / f"{source.stem}.repaired.mp3"
        exporter.encode_mp3_ffmpeg(enhanced, master_out)
        exporter._apply_provenance_tags(
            source, master_out, preset, extra_tags=extra_tags
        )
        notes.append(f"Enhanced master rendered with '{preset.name}'")

    _report(progress, 100.0, "Repair: done.")
    logger.info("Repair finished for %s: master=%s", source.name, master_out)
    return RepairResult(
        master=master_out,
        vocals=vocals_out,
        inst=inst_out,
        residual_worst_db=residual_worst,
        notes=tuple(notes),
    )


__all__ = ["ENHANCEMENT_SAMPLE_RATE", "RepairResult", "SeparateFn", "execute_repair"]
