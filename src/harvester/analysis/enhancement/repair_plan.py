"""Repair plan: symptom catalogue, user choices and detector-driven defaults.

This is the data model behind the guided Repair page (docs/01 D35). A
``RepairPlan`` is a set of symptom choices (enabled, ranges, strength) plus
the engine and enhancement preset; ``plan_from_detection`` builds the
zero-question Quick Fix plan from the acoustic detector's recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from harvester.analysis.enhancement.repair_ops import (
    SegmentFn,
    make_dereverb_op,
    op_air_boost,
    op_de_bleed,
    op_de_click,
    op_de_ess,
    op_de_hum,
    op_de_mud,
    op_fix_pumping,
    op_kill_whispers,
)

BLOCK_VOCALS = "vocals"
BLOCK_INSTRUMENTAL = "instrumental"
BLOCK_MASTER = "master"

TARGET_VOCALS = "vocals"
TARGET_INST = "inst"

DEREVERB_INTENSITY: dict[str, float] = {"light": 0.20, "balanced": 0.40, "strong": 0.70}


@dataclass(frozen=True, slots=True)
class SymptomSpec:
    """One user-facing symptom, its wizard block and how it is repaired."""

    key: str
    block: str
    label: str
    prompt: str
    targets: tuple[str, ...]
    range_capable: bool = True
    suggestion: tuple[str, str, str] | None = None  # (target, source_name, issue_kind)
    auto_issue: str | None = None  # detector issue that enables it automatically


SYMPTOMS: tuple[SymptomSpec, ...] = (
    SymptomSpec(
        key="vocal_bleed",
        block=BLOCK_VOCALS,
        label="Instruments bleeding into the vocals",
        prompt="Do you hear instruments bleeding into the vocals?",
        targets=(TARGET_VOCALS,),
        auto_issue="synth_bleed",
    ),
    SymptomSpec(
        key="harsh_s",
        block=BLOCK_VOCALS,
        label="Harsh S / T sounds",
        prompt="Do the vocals sound harsh on S and T sounds?",
        targets=(TARGET_VOCALS,),
        suggestion=(TARGET_VOCALS, "vocals", "sizzle"),
        auto_issue="sibilance",
    ),
    SymptomSpec(
        key="roomy",
        block=BLOCK_VOCALS,
        label="Roomy / echoey vocals",
        prompt="Do the vocals sound roomy or echoey?",
        targets=(TARGET_VOCALS,),
        range_capable=False,
    ),
    SymptomSpec(
        key="thin_vocal",
        block=BLOCK_VOCALS,
        label="Thin / dull vocals",
        prompt="Do the vocals sound thin or dull?",
        targets=(TARGET_VOCALS,),
        range_capable=False,
    ),
    SymptomSpec(
        key="vocal_dips",
        block=BLOCK_VOCALS,
        label="Volume dips / pumping",
        prompt="Do the vocals dip or pump in level?",
        targets=(TARGET_VOCALS,),
        range_capable=False,
    ),
    SymptomSpec(
        key="ghost_vocals",
        block=BLOCK_INSTRUMENTAL,
        label="Faint ghost vocals / whispers",
        prompt="Do you hear faint ghost vocals or whispers in the instrumental?",
        targets=(TARGET_INST,),
        suggestion=(TARGET_INST, "other", "vocal_bleed"),
    ),
    SymptomSpec(
        key="boomy",
        block=BLOCK_INSTRUMENTAL,
        label="Boomy / muddy low end",
        prompt="Does the low end sound boomy or muddy?",
        targets=(TARGET_VOCALS, TARGET_INST),
        suggestion=(TARGET_INST, "other", "mud"),
        auto_issue="low_mid_mud",
    ),
    SymptomSpec(
        key="rumbly",
        block=BLOCK_INSTRUMENTAL,
        label="Rumble / noisy floor",
        prompt="Do you hear rumble or a noisy floor?",
        targets=(TARGET_VOCALS, TARGET_INST),
        suggestion=(TARGET_INST, "bass", "sub_rumble"),
        auto_issue="sub_bass_rumble",
    ),
    SymptomSpec(
        key="clicks",
        block=BLOCK_INSTRUMENTAL,
        label="Clicks / pops",
        prompt="Do you hear clicks or pops?",
        targets=(TARGET_VOCALS, TARGET_INST),
    ),
    SymptomSpec(
        key="dull_cymbals",
        block=BLOCK_INSTRUMENTAL,
        label="Dull cymbals / no sparkle",
        prompt="Do the cymbals sound dull?",
        targets=(TARGET_INST,),
        range_capable=False,
    ),
    SymptomSpec(
        key="just_enhance",
        block=BLOCK_MASTER,
        label="Just make it sound better",
        prompt="Nothing specific — clean up and add air.",
        targets=(),
        range_capable=False,
    ),
)

SYMPTOM_BY_KEY: dict[str, SymptomSpec] = {spec.key: spec for spec in SYMPTOMS}

OUTPUT_MASTER = "master"
OUTPUT_VOCALS = "vocals"
OUTPUT_INST = "inst"
ALL_OUTPUTS: tuple[str, ...] = (OUTPUT_MASTER, OUTPUT_VOCALS, OUTPUT_INST)


def op_for(key: str, intensity: float = 0.40) -> SegmentFn | None:
    """Resolve the DSP operation for a symptom key (None = no stem op)."""
    if key == "vocal_bleed":
        return op_de_bleed
    if key == "harsh_s":
        return op_de_ess
    if key == "roomy":
        return make_dereverb_op(intensity)
    if key == "thin_vocal":
        return op_air_boost
    if key == "vocal_dips":
        return op_fix_pumping
    if key == "ghost_vocals":
        return op_kill_whispers
    if key == "boomy":
        return op_de_mud
    if key == "rumbly":
        return op_de_hum
    if key == "clicks":
        return op_de_click
    if key == "dull_cymbals":
        return op_air_boost
    return None


@dataclass
class SymptomChoice:
    """One answer: enabled or not, where, and how strong."""

    enabled: bool = False
    ranges: list[tuple[float, float]] | None = None
    intensity: float = 0.40


@dataclass
class RepairPlan:
    """The full repair decision set handed to the executor."""

    choices: dict[str, SymptomChoice] = field(default_factory=dict)
    engine: str = "local"
    enhance_preset_id: str = "fast_balanced"
    blend_weight: float | None = None
    outputs: tuple[str, ...] = ALL_OUTPUTS

    def enabled(self) -> list[SymptomSpec]:
        return [spec for spec in SYMPTOMS if self.choices.get(spec.key, SymptomChoice()).enabled]

    def choice(self, key: str) -> SymptomChoice:
        return self.choices.setdefault(key, SymptomChoice())

    def needs_stems(self) -> bool:
        if any(out in (OUTPUT_VOCALS, OUTPUT_INST) for out in self.outputs):
            return True
        return any(spec.targets for spec in self.enabled())

    def validate(self, duration_s: float) -> list[str]:
        problems: list[str] = []
        for spec in self.enabled():
            choice = self.choices.get(spec.key, SymptomChoice())
            if not spec.range_capable and choice.ranges:
                problems.append(f"{spec.label}: this fix applies to the whole track.")
            for t0, t1 in choice.ranges or []:
                if t1 <= t0:
                    problems.append(f"{spec.label}: section end must be after start.")
                elif t1 > duration_s + 0.05:
                    problems.append(f"{spec.label}: section runs past the end of the track.")
        return problems


def plan_from_detection(
    analysis: object,
    *,
    engine: str = "local",
    enhance_preset_id: str = "fast_balanced",
) -> RepairPlan:
    """Build the zero-question Quick Fix plan from detector recommendations."""
    issues = {str(item) for item in getattr(analysis, "detected_issues", []) or []}
    plan = RepairPlan(engine=engine, enhance_preset_id=enhance_preset_id)
    for spec in SYMPTOMS:
        if spec.auto_issue and spec.auto_issue in issues:
            plan.choice(spec.key).enabled = True
    if not any(choice.enabled for choice in plan.choices.values()):
        plan.choice("just_enhance").enabled = True
    blend = getattr(analysis, "recommended_blend_weight", None)
    if isinstance(blend, (int, float)) and 0.0 <= float(blend) <= 1.0:
        plan.blend_weight = float(blend)
    return plan


__all__ = [
    "ALL_OUTPUTS",
    "BLOCK_INSTRUMENTAL",
    "BLOCK_MASTER",
    "BLOCK_VOCALS",
    "DEREVERB_INTENSITY",
    "OUTPUT_INST",
    "OUTPUT_MASTER",
    "OUTPUT_VOCALS",
    "SYMPTOM_BY_KEY",
    "SYMPTOMS",
    "RepairPlan",
    "SymptomChoice",
    "SymptomSpec",
    "TARGET_INST",
    "TARGET_VOCALS",
    "op_for",
    "plan_from_detection",
]
