"""Widget tests for the guided Repair panel (Quick Fix, wizard, ranges, results)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label

from harvester.analysis.enhancement.acoustic_detector import AcousticAnalysisResult
from harvester.analysis.enhancement.repair_plan import RepairPlan, plan_from_detection
from harvester.ui.repair import (
    WIZARD_KEYS,
    RangeEditor,
    RangeRow,
    RepairPanel,
    format_timecode,
    parse_timecode,
)


@dataclasses.dataclass
class _Result:
    master: Path | None = None
    vocals: Path | None = None
    inst: Path | None = None
    residual_worst_db: float | None = -60.0
    notes: tuple[str, ...] = ()


class PanelApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.applied: list[tuple[RepairPlan, bool]] = []
        self.separates: list[RepairPlan] = []
        self.previews: list[str] = []
        self.exports = 0
        self.suggestions: list[str] = []

    def compose(self) -> ComposeResult:
        yield RepairPanel()

    def on_repair_panel_apply_requested(self, event: RepairPanel.ApplyRequested) -> None:
        self.applied.append((event.plan, event.quick))

    def on_repair_panel_separate_requested(self, event: RepairPanel.SeparateRequested) -> None:
        self.separates.append(event.plan)

    def on_repair_panel_preview_requested(self, event: RepairPanel.PreviewRequested) -> None:
        self.previews.append(event.output)

    def on_repair_panel_export_requested(self, event: RepairPanel.ExportRequested) -> None:
        self.exports += 1

    def on_repair_panel_suggest_requested(self, event: RepairPanel.SuggestRequested) -> None:
        self.suggestions.append(event.symptom)


def test_parse_and_format_timecode():
    assert parse_timecode("1:23") == 83.0
    assert parse_timecode("1:23.5") == 83.5
    assert parse_timecode("95") == 95.0
    assert parse_timecode("1:02:03") == 3723.0
    assert parse_timecode("") is None
    assert parse_timecode("abc") is None
    assert parse_timecode("1:x") is None
    assert parse_timecode("-1:00") is None
    assert format_timecode(83.0) == "1:23.0"
    assert format_timecode(3725.5) == "1:02:05.5"


async def test_quick_fix_card_shows_detection_and_applies():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        assert panel.mode == "idle"
        detection = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.8,
            is_pure_instrumental=False,
            detected_issues=["sibilance", "low_mid_mud"],
            summary="Vocal Track Detected (80% confidence).",
        )
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_detection(detection, plan_from_detection(detection))
        await pilot.pause()

        assert panel.mode == "quick"
        issues = str(app.query_one("#rp-issues", Label).render())
        assert "Fixes ready" in issues
        assert "Harsh S / T sounds" in issues
        assert "Boomy / muddy low end" in issues

        app.query_one("#rp-btn-apply-quick", Button).press()
        await pilot.pause()
        assert len(app.applied) == 1
        plan, quick = app.applied[0]
        assert quick is True
        assert plan.choice("harsh_s").enabled
        assert plan.choice("boomy").enabled


async def test_wizard_runs_all_questions_and_builds_a_plan():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        detection = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.8,
            is_pure_instrumental=False,
            detected_issues=["sibilance"],
            summary="Vocal Track Detected.",
        )
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_detection(detection, plan_from_detection(detection))
        await pilot.pause()

        app.query_one("#rp-btn-adjust", Button).press()
        await pilot.pause()
        assert panel.mode == "wizard"
        assert app.query_one("#rp-question", Label) is not None

        for _ in WIZARD_KEYS:
            assert app.query_one("#rp-question", Label).render().plain
            app.query_one("#rp-ans-no", Button).press()
            await pilot.pause()
            app.query_one("#rp-btn-next", Button).press()
            await pilot.pause()

        assert panel.mode == "summary"
        assert "Nothing selected" in str(app.query_one("#rp-summary", Label).render())

        app.query_one("#rp-btn-apply-plan", Button).press()
        await pilot.pause()
        assert app.applied[-1][1] is False


async def test_wizard_not_sure_uses_detector_recommendation():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        detection = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.8,
            is_pure_instrumental=False,
            detected_issues=["sibilance"],
            summary="Vocal Track Detected.",
        )
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_detection(detection, plan_from_detection(detection))
        await pilot.pause()

        # harsh_s is question 2 (index 1); answer it with "Not sure".
        panel.mode = "wizard"
        panel.wizard_index = 1
        panel._refresh()
        assert panel.current_key() == "harsh_s"
        assert panel._detector_says("harsh_s")

        app.query_one("#rp-ans-unsure", Button).press()
        await pilot.pause()
        app.query_one("#rp-btn-next", Button).press()
        await pilot.pause()
        assert panel.plan is not None
        assert panel.plan.choice("harsh_s").enabled


async def test_wizard_yes_opens_range_editor_and_suggest_message():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        panel.set_track(Path("song.mp3"), 15500.0, True)
        panel.mode = "wizard"
        panel.wizard_index = 1  # harsh_s
        stubs = RepairPlan()
        panel.plan = stubs
        panel.answers["harsh_s"] = "yes"
        stubs.choice("harsh_s").enabled = True
        panel._refresh()
        await pilot.pause()

        editor = app.query_one("#rp-range-editor", RangeEditor)
        assert editor.styles.display != "none"
        assert editor.get_ranges() == []

        app.query_one("#rp-btn-range-suggest", Button).press()
        await pilot.pause()
        assert app.suggestions == ["harsh_s"]

        await panel.set_suggested_ranges("harsh_s", [(10.0, 20.0), (65.0, 70.5)])
        await pilot.pause()
        rows = list(editor.query(RangeRow))
        assert len(rows) == 2
        assert rows[0].query(Input).first().value == "0:10.0"
        assert editor.get_ranges() == [(10.0, 20.0), (65.0, 70.5)]


async def test_roomy_strength_buttons_and_result_messages():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.mode = "wizard"
        panel.plan = RepairPlan()
        panel.wizard_index = WIZARD_KEYS.index("roomy")
        panel._refresh()
        await pilot.pause()

        app.query_one("#rp-ans-yes", Button).press()
        await pilot.pause()
        app.query_one("#rp-strength-strong", Button).press()
        await pilot.pause()
        assert panel.plan.choice("roomy").intensity > 0.6

        panel.show_result(_Result(master=Path("/tmp/master.mp3")))
        await pilot.pause()
        assert "Repair complete" in str(app.query_one("#rp-result-status", Label).render())
        app.query_one("#rp-btn-prev-master", Button).press()
        app.query_one("#rp-btn-export", Button).press()
        await pilot.pause()
        assert app.previews == ["master"]
        assert app.exports == 1


async def test_track_change_resets_panel_state():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        detection = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.5,
            is_pure_instrumental=False,
            summary="x",
        )
        panel.set_track(Path("one.mp3"), 15500.0, False)
        panel.set_detection(detection, plan_from_detection(detection))
        panel.show_result(_Result())
        await pilot.pause()
        assert panel.mode == "result"

        panel.set_track(Path("two.mp3"), 15000.0, False)
        await pilot.pause()
        assert panel.mode == "idle"
        assert panel.detection is None and panel.result is None and panel.plan is None


async def test_engine_and_strength_choices_flow_into_the_plan():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        detection = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.8,
            is_pure_instrumental=False,
            detected_issues=["sibilance"],
            summary="Vocal Track Detected.",
        )
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_detection(detection, plan_from_detection(detection))
        panel.set_hosted_available(True)
        await pilot.pause()

        app.query_one("#rp-engine-hosted", Button).press()
        await pilot.pause()
        assert panel.engine == "hosted"

        for _ in WIZARD_KEYS:
            app.query_one("#rp-btn-next", Button).press()
            await pilot.pause()
        assert panel.mode == "summary"

        app.query_one("#rp-preset-strong", Button).press()
        await pilot.pause()
        assert panel.strength == "strong"

        app.query_one("#rp-btn-apply-plan", Button).press()
        await pilot.pause()
        plan, quick = app.applied[-1]
        assert quick is False
        assert plan.engine == "hosted"
        assert plan.enhance_preset_id == "extended_air"


async def test_panel_never_collapses_and_card_is_always_visible():
    """Regression: the panel used to compute height 0 and clip every child."""
    app = PanelApp()
    async with app.run_test(size=(100, 30)) as pilot:
        panel = app.query_one(RepairPanel)
        await pilot.pause()
        assert panel.size.height > 0
        card = panel.query_one("#rp-quick")
        assert card.styles.display == "block"
        assert card.size.height > 0
        assert str(panel.query_one("#rp-issues", Label).render()).strip()
        assert panel.query_one("#rp-btn-apply-quick", Button).disabled
        assert panel.query_one("#rp-btn-separate", Button).disabled

        panel.set_track(Path("song.mp3"), 15500.0, False)
        await pilot.pause()
        # No analysis yet: stems can still be extracted, fixes cannot.
        assert panel.query_one("#rp-btn-apply-quick", Button).disabled
        assert not panel.query_one("#rp-btn-separate", Button).disabled
        assert not panel.query_one("#rp-btn-rerun", Button).disabled
        assert panel.query_one("#rp-btn-separate", Button).region.height > 0

        detection = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.8,
            is_pure_instrumental=False,
            detected_issues=["sibilance"],
            summary="Vocal Track Detected.",
        )
        panel.set_detection(detection, plan_from_detection(detection))
        await pilot.pause()
        assert not panel.query_one("#rp-btn-apply-quick", Button).disabled


async def test_error_state_is_surfaced_on_the_page():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_error("soundfile: cannot decode")
        await pilot.pause()
        text = str(panel.query_one("#rp-issues", Label).render())
        assert "Analysis failed" in text and "cannot decode" in text
        assert panel.mode == "idle"


async def test_separate_only_emits_a_fix_free_plan():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        detection = AcousticAnalysisResult(
            has_vocals=True,
            vocal_confidence=0.8,
            is_pure_instrumental=False,
            detected_issues=["sibilance"],
            summary="Vocal Track Detected.",
        )
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_detection(detection, plan_from_detection(detection))
        await pilot.pause()

        app.query_one("#rp-btn-separate", Button).press()
        await pilot.pause()
        assert len(app.separates) == 1
        plan = app.separates[0]
        assert plan.enabled() == []
        assert set(plan.outputs) == {"master", "vocals", "inst"}


async def test_card_strength_choice_updates_the_plan():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_detection(
            AcousticAnalysisResult(True, 0.5, False, summary="x"), plan_from_detection(
                AcousticAnalysisResult(True, 0.5, False, summary="x"))
        )
        await pilot.pause()
        app.query_one("#rp-card-strong", Button).press()
        await pilot.pause()
        assert panel.strength == "strong"
        assert panel.plan is not None and panel.plan.enhance_preset_id == "extended_air"


async def test_card_hides_when_wizard_summary_or_result_is_active():
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        detection = AcousticAnalysisResult(True, 0.8, False, ["sibilance"], summary="x")
        panel.set_track(Path("song.mp3"), 15500.0, False)
        panel.set_detection(detection, plan_from_detection(detection))
        await pilot.pause()
        card = panel.query_one("#rp-quick")
        assert card.styles.display == "block"

        panel._begin_wizard()
        await pilot.pause()
        assert card.styles.display == "none"
        assert panel.query_one("#rp-wizard").styles.display == "block"

        panel.mode = "summary"
        panel._refresh()
        await pilot.pause()
        assert card.styles.display == "none"
        assert panel.query_one("#rp-summary-pane").styles.display == "block"

        panel.show_result(object())
        await pilot.pause()
        assert card.styles.display == "none"
        assert panel.query_one("#rp-result").styles.display == "block"


async def test_rerun_button_emits_rerun_request():
    captured: list[str] = []

    class RerunApp(PanelApp):
        def on_repair_panel_rerun_requested(self, event: RepairPanel.RerunRequested) -> None:
            captured.append("rerun")

    app = RerunApp()
    async with app.run_test() as pilot:
        panel = app.query_one(RepairPanel)
        panel.set_track(Path("song.mp3"), 15500.0, False)
        await pilot.pause()
        app.query_one("#rp-btn-rerun", Button).press()
        await pilot.pause()
        assert captured == ["rerun"]
