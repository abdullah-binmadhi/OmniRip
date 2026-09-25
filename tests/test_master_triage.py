"""Unit tests for the 20-Question Master Remediation Engine."""

from __future__ import annotations

import numpy as np

from harvester.analysis.enhancement.master_triage import (
    MASTER_SYMPTOM_BY_KEY,
    MASTER_SYMPTOMS,
    apply_master_remediation,
)

SR = 44100


def _generate_synthetic_mix(duration_s: float = 1.0) -> np.ndarray:
    """Generate stereo test signal with bass, mids, highs, and stereo spread."""
    t = np.linspace(0, duration_s, int(SR * duration_s), endpoint=False, dtype=np.float32)
    # Bass: 60 Hz + 120 Hz
    bass = 0.4 * np.sin(2 * np.pi * 60 * t) + 0.2 * np.sin(2 * np.pi * 120 * t)
    # Mids / Vocals: 1 kHz + 2.5 kHz
    mids = 0.3 * np.sin(2 * np.pi * 1000 * t) + 0.25 * np.sin(2 * np.pi * 2500 * t)
    # Highs: 8 kHz + 14 kHz
    highs = 0.15 * np.sin(2 * np.pi * 8000 * t) + 0.1 * np.sin(2 * np.pi * 14000 * t)

    left = bass + mids + highs
    # Stereo offset for right channel
    right = bass + 0.8 * mids + 1.2 * highs + 0.1 * np.sin(2 * np.pi * 3000 * t)
    return np.stack([left, right], axis=0).astype(np.float32)


def test_twenty_questions_catalogue_completeness():
    assert len(MASTER_SYMPTOMS) == 20
    assert len(MASTER_SYMPTOM_BY_KEY) == 20
    # Every symptom has unique key, category, prompt, label, and callable dsp_fn
    keys = set()
    for s in MASTER_SYMPTOMS:
        assert s.key not in keys
        keys.add(s.key)
        assert len(s.prompt) > 10
        assert len(s.label) > 5
        assert callable(s.dsp_fn)


def test_each_dsp_operation_preserves_audio_format_and_shape():
    test_audio = _generate_synthetic_mix(0.5)
    expected_shape = test_audio.shape

    for s in MASTER_SYMPTOMS:
        processed = s.dsp_fn(test_audio, SR)
        assert isinstance(processed, np.ndarray)
        assert processed.shape == expected_shape
        assert processed.dtype == np.float32
        assert np.all(np.isfinite(processed)), f"Operation {s.key} generated non-finite values"


def test_apply_master_remediation_chains_multiple_fixes():
    test_audio = _generate_synthetic_mix(0.5)
    choices = {
        "too_dark": True,
        "buried_vocals": True,
        "weak_bass": True,
        "cold_digital": True,
    }
    remediated = apply_master_remediation(test_audio, SR, choices)
    assert remediated.shape == test_audio.shape
    assert remediated.dtype == np.float32
    assert not np.array_equal(test_audio, remediated)
    assert np.all(np.isfinite(remediated))


async def test_master_triage_wizard_ui_flow():
    from pathlib import Path

    from textual.app import App, ComposeResult
    from textual.widgets import Button, Label

    from harvester.analysis.enhancement.repair_plan import RepairPlan
    from harvester.ui.repair import RepairPanel

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield RepairPanel()

    app = TestApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        panel.set_track(Path("mix.wav"), 15500.0, False)
        panel.plan = RepairPlan()

        # Trigger master remediation wizard
        panel._begin_wizard(mode="master")
        await pilot.pause()

        assert panel.mode == "wizard"
        assert panel.wizard_mode == "master"
        assert len(panel._wizard_keys()) == 20

        # Check question 1 progress
        prog = app.query_one("#rp-progress", Label).render().plain
        assert "[01 / 20]" in prog
        assert "TAME SHARP HIGH FREQUENCIES" in prog

        # Answer YES to question 1
        app.query_one("#rp-ans-yes", Button).press()
        await pilot.pause()
        assert panel.plan.master_choices.get("too_bright") is True

        # Check real-time metrics label
        metrics = app.query_one("#rp-wiz-metrics-label", Label).render().plain
        assert "ACTIVE REMEDIATIONS: 1" in metrics

        # Next question
        app.query_one("#rp-btn-next", Button).press()
        await pilot.pause()
        prog2 = app.query_one("#rp-progress", Label).render().plain
        assert "[02 / 20]" in prog2

        # Fast apply button directly goes to summary
        app.query_one("#rp-btn-wiz-apply", Button).press()
        await pilot.pause()
        assert panel.mode == "summary"

        sum_text = app.query_one("#rp-summary", Label).render().plain
        assert "Active Master Remediation Filters (1):" in sum_text
        assert "Tame sharp high frequencies" in sum_text

