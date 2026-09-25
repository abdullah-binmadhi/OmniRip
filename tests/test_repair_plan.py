"""Tests for the repair plan model and detector-driven defaults."""

from __future__ import annotations

from dataclasses import dataclass, field

from harvester.analysis.enhancement.repair_plan import (
    OUTPUT_MASTER,
    SYMPTOMS,
    TARGET_VOCALS,
    RepairPlan,
    op_for,
    plan_from_detection,
)


@dataclass
class _Analysis:
    detected_issues: list[str] = field(default_factory=list)
    recommended_blend_weight: float = 0.70


def test_symptom_keys_are_unique_and_ops_exist_for_stem_targets():
    keys = [spec.key for spec in SYMPTOMS]
    assert len(keys) == len(set(keys))
    for spec in SYMPTOMS:
        if spec.targets:
            assert op_for(spec.key) is not None, spec.key
        else:
            assert op_for(spec.key) is None


def test_plan_from_detection_maps_issues_to_symptoms():
    plan = plan_from_detection(_Analysis(detected_issues=["sibilance", "low_mid_mud"]))
    assert plan.choice("harsh_s").enabled
    assert plan.choice("boomy").enabled
    assert not plan.choice("ghost_vocals").enabled
    assert not plan.choice("just_enhance").enabled
    assert plan.blend_weight == 0.70


def test_plan_from_detection_falls_back_to_enhance_only():
    plan = plan_from_detection(_Analysis(detected_issues=[]))
    enabled = [spec.key for spec in plan.enabled()]
    assert enabled == ["just_enhance"]


def test_plan_validation_flags_bad_ranges_and_whole_track_symptoms():
    plan = RepairPlan()
    plan.choice("vocal_bleed").enabled = True
    plan.choice("vocal_bleed").ranges = [(3.0, 2.0), (1.0, 99.0)]
    plan.choice("roomy").enabled = True
    plan.choice("roomy").ranges = [(0.0, 1.0)]
    problems = plan.validate(duration_s=10.0)
    assert any("section end must be after start" in p for p in problems)
    assert any("past the end" in p for p in problems)
    assert any("whole track" in p for p in problems)


def test_needs_stems_follows_outputs_and_targets():
    plan = RepairPlan(outputs=(OUTPUT_MASTER,))
    assert not plan.needs_stems()
    plan.choice("vocal_bleed").enabled = True
    assert plan.needs_stems()
    plan2 = RepairPlan(outputs=("vocals",))
    plan2.choice("just_enhance").enabled = True
    assert plan2.needs_stems()


def test_target_constants_used_by_specs():
    vocal_specs = [spec for spec in SYMPTOMS if TARGET_VOCALS in spec.targets]
    assert {spec.key for spec in vocal_specs} >= {"vocal_bleed", "harsh_s", "roomy"}
