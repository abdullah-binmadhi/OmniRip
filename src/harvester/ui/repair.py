"""Guided Repair page (docs/01 D35): Quick Fix card, sequential wizard, ranges.

The panel is presentation + plan state only. It never decodes audio: the
workbench runs the acoustic detector, the repair executor and the preview
playback, and feeds results back through ``set_*`` methods. Messages out:

- ``ApplyRequested(plan, quick)`` — run the repair.
- ``PreviewRequested(output)`` — audition master/vocals/instrumental.
- ``ExportRequested`` — copy the three deliverables to the output directory.
- ``SuggestRequested(symptom)`` — workbench scans the stems for hot spots.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from harvester.analysis.enhancement.repair_plan import (
    BLOCK_INSTRUMENTAL,
    BLOCK_VOCALS,
    DEREVERB_INTENSITY,
    SYMPTOM_BY_KEY,
    SYMPTOMS,
    RepairPlan,
)

WIZARD_KEYS: tuple[str, ...] = tuple(spec.key for spec in SYMPTOMS if spec.key != "just_enhance")

STRENGTH_PRESETS: dict[str, str] = {
    "gentle": "conservative",
    "balanced": "fast_balanced",
    "strong": "extended_air",
}
PRESET_STRENGTH: dict[str, str] = {preset: name for name, preset in STRENGTH_PRESETS.items()}

BLOCK_TITLES: dict[str, str] = {
    BLOCK_VOCALS: "Vocals",
    BLOCK_INSTRUMENTAL: "Instrumental",
}


def parse_timecode(text: str) -> float | None:
    """Parse ``mm:ss`` / ``h:mm:ss`` / plain seconds into a float, or None."""
    raw = (text or "").strip()
    if not raw:
        return None
    parts = raw.split(":")
    try:
        values = [float(part) for part in parts]
    except ValueError:
        return None
    if any(value < 0 for value in values):
        return None
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return values[0] * 60.0 + values[1]
    if len(values) == 3:
        return values[0] * 3600.0 + values[1] * 60.0 + values[2]
    return None


def format_timecode(seconds: float) -> str:
    """Render seconds as ``m:ss.s`` (or ``h:mm:ss.s`` for long tracks)."""
    total = max(0.0, float(seconds))
    minutes, secs = divmod(total, 60.0)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:04.1f}"
    return f"{minutes}:{secs:04.1f}"


class RangeRow(Horizontal):
    """One ``start → end`` section row."""

    def __init__(self, start: str, end: str, index: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._start = start
        self._end = end
        self.index = index

    def compose(self) -> ComposeResult:
        yield Input(value=self._start, placeholder="0:00", classes="rp-range-input")
        yield Label("→", classes="rp-range-arrow")
        yield Input(value=self._end, placeholder="0:30", classes="rp-range-input")
        yield Button("✕", id=f"rp-range-remove-{self.index}", classes="rp-range-remove")

    @property
    def start_time(self) -> float | None:
        return parse_timecode(self.query(Input).first().value)

    @property
    def end_time(self) -> float | None:
        return parse_timecode(self.query(Input)[1].value)


class RangeEditor(Vertical):
    """Editable list of time sections; an empty list means whole track."""

    class SuggestRequested(Message):
        """Ask the workbench to detect hot spots for the active symptom."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._rows_data: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        yield Label("Sections — leave empty to fix the whole track", classes="rp-range-title")
        with Vertical(id="rp-range-rows"):
            for index, (start, end) in enumerate(self._rows_data):
                yield RangeRow(start, end, index)
        with Horizontal(id="rp-range-actions"):
            yield Button("+ Add section", id="rp-btn-range-add")
            yield Button("⌖ SUGGEST SPOTS", id="rp-btn-range-suggest")
            yield Button("⟲ Whole track", id="rp-btn-range-whole")

    def _sync_from_inputs(self) -> None:
        rows = list(self.query(RangeRow))
        if rows:
            self._rows_data = [(row.query(Input).first().value, row.query(Input)[1].value) for row in rows]

    async def add_row(self, start: str = "", end: str = "") -> None:
        self._sync_from_inputs()
        self._rows_data.append((start, end))
        await self.recompose()

    async def set_ranges(self, ranges: list[tuple[float, float]]) -> None:
        self._rows_data = [(format_timecode(t0), format_timecode(t1)) for t0, t1 in ranges]
        await self.recompose()

    async def clear_rows(self) -> None:
        self._rows_data = []
        await self.recompose()

    async def remove_row(self, index: int) -> None:
        self._sync_from_inputs()
        if 0 <= index < len(self._rows_data):
            del self._rows_data[index]
        await self.recompose()

    def get_ranges(self) -> list[tuple[float, float]]:
        ranges: list[tuple[float, float]] = []
        for row in self.query(RangeRow):
            t0 = row.start_time
            t1 = row.end_time
            if t0 is None or t1 is None or t1 <= t0:
                continue
            ranges.append((t0, t1))
        return ranges

    def set_suggest_enabled(self, enabled: bool) -> None:
        with self.app.batch_update():
            for button in self.query("#rp-btn-range-suggest"):
                button.disabled = not enabled


class RepairPanel(Widget):
    """The REPAIR page: Quick Fix, wizard, ranges, results."""

    DEFAULT_CSS = """
    RepairPanel {
        height: auto;
        layout: vertical;
    }
    """

    class ApplyRequested(Message):
        def __init__(self, plan: RepairPlan, quick: bool) -> None:
            super().__init__()
            self.plan = plan
            self.quick = quick

    class PreviewRequested(Message):
        def __init__(self, output: str) -> None:
            super().__init__()
            self.output = output

    class ExportRequested(Message):
        pass

    class SeparateRequested(Message):
        def __init__(self, plan: RepairPlan) -> None:
            super().__init__()
            self.plan = plan

    class RerunRequested(Message):
        pass

    class SuggestRequested(Message):
        def __init__(self, symptom: str) -> None:
            super().__init__()
            self.symptom = symptom

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.track: Any = None
        self.cutoff_hz: float = 15500.0
        self.detection: Any = None
        self.plan: RepairPlan | None = None
        self.stems_ready: bool = False
        self.result: Any = None
        self.mode: str = "idle"
        self.wizard_index: int = 0
        self.answers: dict[str, str] = {}
        self.engine: str = "local"
        self.strength: str = "balanced"
        self.hosted_available: bool = False
        self.error: str | None = None
        self.engine_status: str = ""
        self.neural_ready: bool = False

    def compose(self) -> ComposeResult:
        yield Label("GUIDED REPAIR", id="rp-title")
        yield Label("", id="rp-status")

        with Vertical(id="rp-quick"):
            yield Label("◈ ENGINE: —", id="rp-engine-badge")
            yield Label("", id="rp-issues")
            with Horizontal(id="rp-quick-actions"):
                yield Button("⚡ QUICK FIX", id="rp-btn-apply-quick", variant="success")
                yield Button("𝄢 STEMS ONLY", id="rp-btn-separate")
                yield Button("✎ CUSTOMIZE", id="rp-btn-adjust")
                yield Button("↺ RERUN ANALYSIS", id="rp-btn-rerun")
            with Horizontal(id="rp-options-row"):
                yield Label("Options:", classes="rp-engine-label")
                yield Button("⌂ LOCAL", id="rp-engine-local", variant="primary")
                yield Button("☁ HOSTED", id="rp-engine-hosted")
                yield Label("Enhance:", classes="rp-engine-label")
                yield Button("GENTLE", id="rp-card-gentle")
                yield Button("BALANCED", id="rp-card-balanced")
                yield Button("STRONG", id="rp-card-strong")

        with Vertical(id="rp-wizard"):
            yield Label("", id="rp-progress")
            yield Label("", id="rp-question")
            with Horizontal(id="rp-answer-row"):
                yield Button("Yes, I hear it", id="rp-ans-yes")
                yield Button("No", id="rp-ans-no")
                yield Button("Not sure", id="rp-ans-unsure")
            yield Label("", id="rp-detector-hint")
            with Horizontal(id="rp-strength-row"):
                yield Button("LIGHT", id="rp-strength-light")
                yield Button("BALANCED", id="rp-strength-balanced")
                yield Button("STRONG", id="rp-strength-strong")
            yield RangeEditor(id="rp-range-editor")
            with Horizontal(id="rp-wizard-nav"):
                yield Button("◂ Back", id="rp-btn-back")
                yield Button("Next ▸", id="rp-btn-next", variant="primary")
                yield Button("Cancel", id="rp-btn-wizard-cancel")

        with Vertical(id="rp-summary-pane"):
            yield Label("", id="rp-summary")
            with Horizontal(id="rp-strength-preset-row"):
                yield Label("Enhance:", classes="rp-engine-label")
                yield Button("GENTLE", id="rp-preset-gentle")
                yield Button("BALANCED", id="rp-preset-balanced")
                yield Button("STRONG", id="rp-preset-strong")
            with Horizontal(id="rp-summary-actions"):
                yield Button("⚡ APPLY PLAN", id="rp-btn-apply-plan", variant="success")
                yield Button("◂ Back", id="rp-btn-summary-back")

        with Vertical(id="rp-result"):
            yield Label("", id="rp-result-status")
            with Horizontal(id="rp-result-preview"):
                yield Button("▶ Master", id="rp-btn-prev-master")
                yield Button("▶ Vocals", id="rp-btn-prev-vocals")
                yield Button("▶ Instrumental", id="rp-btn-prev-inst")
            with Horizontal(id="rp-result-actions"):
                yield Button("⤓ EXPORT ALL", id="rp-btn-export", variant="success")
                yield Button("✗ NOT HAPPY? IMPROVE IT", id="rp-btn-improve")
                yield Button("↺ NEW ANALYSIS", id="rp-btn-reanalyze")

    # -- workbench updates -------------------------------------------------

    def on_mount(self) -> None:
        self._refresh()

    def set_track(self, path: Any, cutoff_hz: float, stems_ready: bool) -> None:
        """Point the panel at a track; changing track resets all state."""
        changed = path != self.track
        self.track = path
        self.cutoff_hz = cutoff_hz
        self.stems_ready = stems_ready
        if changed:
            self.detection = None
            self.plan = None
            self.result = None
            self.answers = {}
            self.wizard_index = 0
            self.error = None
            self.mode = "idle"
        self._refresh()

    def set_detection(self, detection: Any, plan: RepairPlan) -> None:
        """Populate the Quick Fix card from acoustic analysis."""
        self.detection = detection
        self.plan = plan
        self.error = None
        self.engine = str(getattr(plan, "engine", "local") or "local")
        self.strength = PRESET_STRENGTH.get(str(getattr(plan, "enhance_preset_id", "")), "balanced")
        self.mode = "quick"
        self._refresh()

    def set_hosted_available(self, available: bool) -> None:
        self.hosted_available = bool(available)
        self._refresh()

    def set_engine_status(self, text: str, *, neural: bool) -> None:
        """Show which separation/enhancement engine will actually run."""
        self.engine_status = text
        self.neural_ready = bool(neural)
        self._refresh()

    def set_error(self, message: str) -> None:
        """Surface an analysis failure on the page instead of staying silent."""
        self.error = message
        self.mode = "idle"
        self._refresh()

    def _separate_plan(self) -> RepairPlan:
        """A fix-free plan: separate and deliver all three outputs."""
        blend = getattr(self.plan, "blend_weight", None) if self.plan else None
        return RepairPlan(
            engine=self.engine,
            enhance_preset_id=STRENGTH_PRESETS[self.strength],
            blend_weight=blend,
        )

    def _sync_plan(self) -> None:
        if self.plan is None:
            return
        self.plan.engine = self.engine
        self.plan.enhance_preset_id = STRENGTH_PRESETS[self.strength]

    def set_stems_ready(self, ready: bool) -> None:
        self.stems_ready = ready
        self._refresh()

    def show_result(self, result: Any) -> None:
        self.result = result
        self.mode = "result"
        self._refresh()

    def set_progress(self, message: str) -> None:
        label = self.query_one("#rp-status", Label)
        label.update(message)

    async def set_suggested_ranges(self, symptom: str, ranges: list[tuple[float, float]]) -> None:
        if self.mode != "wizard" or self.current_key() != symptom:
            return
        editor = self.query_one("#rp-range-editor", RangeEditor)
        await editor.set_ranges(ranges)
        hint = self.query_one("#rp-detector-hint", Label)
        if ranges:
            hint.update(f"Analysis suggested {len(ranges)} section(s) — adjust or keep them.")
        else:
            hint.update("Analysis found no hot spots — fixing the whole track is fine.")

    # -- wizard helpers ----------------------------------------------------

    def current_key(self) -> str | None:
        if not (0 <= self.wizard_index < len(WIZARD_KEYS)):
            return None
        return WIZARD_KEYS[self.wizard_index]

    def current_spec(self) -> Any:
        key = self.current_key()
        return SYMPTOM_BY_KEY[key] if key else None

    def _detector_says(self, key: str) -> bool:
        spec = SYMPTOM_BY_KEY[key]
        if self.detection is None or not spec.auto_issue:
            return False
        issues = set(getattr(self.detection, "detected_issues", []) or [])
        return spec.auto_issue in issues

    def _begin_wizard(self) -> None:
        if self.plan is None:
            self.plan = RepairPlan()
        self.answers = {}
        for key in WIZARD_KEYS:
            choice = self.plan.choices.get(key)
            self.answers[key] = "yes" if (choice is not None and choice.enabled) else "no"
        self.wizard_index = 0
        self.mode = "wizard"
        self._refresh()

    def _answer(self, answer: str) -> None:
        key = self.current_key()
        if key is None or self.plan is None:
            return
        spec = SYMPTOM_BY_KEY[key]
        choice = self.plan.choice(key)
        self.answers[key] = answer
        if answer == "yes":
            choice.enabled = True
        elif answer == "no":
            choice.enabled = False
            choice.ranges = None
        else:
            detected = self._detector_says(key)
            choice.enabled = detected
            if not detected:
                choice.ranges = None
        if not spec.range_capable:
            choice.ranges = None
        self._refresh()

    def _wizard_range_choice(self) -> Any:
        key = self.current_key()
        if key is None or self.plan is None:
            return None
        return self.plan.choice(key)

    # -- rendering ---------------------------------------------------------

    def _refresh(self) -> None:
        try:
            self.query_one("#rp-quick").styles.display = (
                "block" if self.mode in ("idle", "quick") else "none"
            )
            self.query_one("#rp-wizard").styles.display = "block" if self.mode == "wizard" else "none"
            self.query_one("#rp-summary-pane").styles.display = (
                "block" if self.mode == "summary" else "none"
            )
            self.query_one("#rp-result").styles.display = "block" if self.mode == "result" else "none"
        except Exception:
            return

        self._render_status()
        if self.mode in ("idle", "quick"):
            self._render_quick()
        if self.mode == "wizard":
            self._render_wizard()
        elif self.mode == "summary":
            self._render_summary()
        elif self.mode == "result":
            self._render_result()

    def _render_status(self) -> None:
        label = self.query_one("#rp-status", Label)
        if self.track is None:
            label.update("No track selected — pick a track above")
            return
        name = getattr(self.track, "name", str(self.track))
        stem_state = "stems cached" if self.stems_ready else "stems not built yet"
        label.update(f"{name} · cutoff {self.cutoff_hz / 1000.0:.2f} kHz · {stem_state}")

    def _render_quick(self) -> None:
        badge = self.query_one("#rp-engine-badge", Label)
        badge.update("◈ " + (self.engine_status or "ENGINE: checking models…"))

        self.query_one("#rp-engine-local", Button).variant = (
            "primary" if self.engine == "local" else "default"
        )
        hosted_button = self.query_one("#rp-engine-hosted", Button)
        hosted_button.variant = "primary" if self.engine == "hosted" else "default"
        hosted_button.disabled = not self.hosted_available

        label = self.query_one("#rp-issues", Label)
        if self.error:
            label.update(
                f"Analysis failed: {self.error}\n"
                "Press ↺ RERUN ANALYSIS to try again, or extract the stems directly."
            )
        elif self.detection is None:
            if self.track is None:
                label.update(
                    "No track selected — pick a track above to analyze it, "
                    "or press 𝄢 STEMS ONLY once a track is loaded."
                )
            else:
                label.update("Analyzing the track…")
        else:
            summary = str(getattr(self.detection, "summary", "") or "")
            lines = [summary] if summary else []
            fixes = [spec for spec in (self.plan.enabled() if self.plan else []) if spec.key != "just_enhance"]
            if fixes:
                lines.append("Fixes ready:")
                lines.extend(f"  • {spec.label}" for spec in fixes)
            else:
                lines.append(
                    "No specific defects detected — QUICK FIX will clean up and enhance "
                    "the master and still write the stems."
                )
            label.update("\n".join(lines))

        has_track = self.track is not None
        self.query_one("#rp-btn-apply-quick", Button).disabled = self.plan is None
        self.query_one("#rp-btn-separate", Button).disabled = not has_track
        self.query_one("#rp-btn-adjust", Button).disabled = not has_track
        self.query_one("#rp-btn-rerun", Button).disabled = not has_track

        for strength_id, name in (
            ("rp-card-gentle", "gentle"),
            ("rp-card-balanced", "balanced"),
            ("rp-card-strong", "strong"),
        ):
            self.query_one(f"#{strength_id}", Button).variant = (
                "primary" if self.strength == name else "default"
            )
            self.query_one(f"#{strength_id}", Button).disabled = not has_track

    def _render_wizard(self) -> None:
        spec = self.current_spec()
        if spec is None:
            self.mode = "summary"
            self._refresh()
            return
        total = len(WIZARD_KEYS)
        block = BLOCK_TITLES.get(spec.block, spec.block.title())
        self.query_one("#rp-progress", Label).update(
            f"{block} · question {self.wizard_index + 1} of {total}"
        )
        self.query_one("#rp-question", Label).update(spec.prompt)

        answer = self.answers.get(spec.key, "no")
        for answer_id, value in (
            ("rp-ans-yes", "yes"),
            ("rp-ans-no", "no"),
            ("rp-ans-unsure", "unsure"),
        ):
            button = self.query_one(f"#{answer_id}", Button)
            button.variant = "primary" if answer == value else "default"

        hint = self.query_one("#rp-detector-hint", Label)
        if spec.auto_issue:
            state = "detected" if self._detector_says(spec.key) else "not detected"
            hint.update(f"Analysis: {state} in this track.")
        else:
            hint.update("Analysis can't judge this one — your ears decide.")

        editor = self.query_one("#rp-range-editor", RangeEditor)
        show_ranges = answer == "yes" and spec.range_capable
        editor.styles.display = "block" if show_ranges else "none"
        if show_ranges:
            editor.set_suggest_enabled(self.stems_ready)

        strength_row = self.query_one("#rp-strength-row", Horizontal)
        show_strength = answer == "yes" and spec.key == "roomy"
        strength_row.styles.display = "block" if show_strength else "none"
        if show_strength and self.plan is not None:
            intensity = self.plan.choice("roomy").intensity
            for strength_id, value in (
                ("rp-strength-light", DEREVERB_INTENSITY["light"]),
                ("rp-strength-balanced", DEREVERB_INTENSITY["balanced"]),
                ("rp-strength-strong", DEREVERB_INTENSITY["strong"]),
            ):
                self.query_one(f"#{strength_id}", Button).variant = (
                    "primary" if abs(intensity - value) < 1e-6 else "default"
                )

        self.query_one("#rp-btn-back", Button).disabled = self.wizard_index == 0

    def _render_summary(self) -> None:
        assert self.plan is not None
        lines: list[str] = []
        for spec in self.plan.enabled():
            choice = self.plan.choice(spec.key)
            if spec.key == "just_enhance":
                lines.append("• Clean up and enhance the master")
                continue
            where = "whole track"
            if choice.ranges:
                where = " + ".join(
                    f"{format_timecode(t0)}–{format_timecode(t1)}" for t0, t1 in choice.ranges
                )
            elif spec.key == "roomy":
                where = f"strength {int(round(choice.intensity * 100))}%"
            lines.append(f"• {spec.label} — {where}")
        if not any(line for line in lines):
            lines.append("• Nothing selected — the track will be enhanced as-is.")
        engine_label = "Local separation" if self.engine == "local" else "Hosted MVSEP (uploads audio)"
        lines.append("")
        lines.append(f"Engine: {engine_label} · Enhance: {self.strength.title()}")
        lines.append("Outputs: enhanced master · clean vocals · clean instrumental")
        self.query_one("#rp-summary", Label).update("\n".join(lines))
        for strength_id, name in (
            ("rp-preset-gentle", "gentle"),
            ("rp-preset-balanced", "balanced"),
            ("rp-preset-strong", "strong"),
        ):
            self.query_one(f"#{strength_id}", Button).variant = (
                "primary" if self.strength == name else "default"
            )

    def _render_result(self) -> None:
        result = self.result
        notes = list(getattr(result, "notes", []) or [])
        headline = "Repair complete"
        if notes:
            headline += " — " + notes[0]
        if len(notes) > 1:
            headline += f" (+{len(notes) - 1} more note(s))"
        self.query_one("#rp-result-status", Label).update(headline)

    # -- events ------------------------------------------------------------

    def on_range_editor_suggest_requested(self, event: RangeEditor.SuggestRequested) -> None:
        event.stop()
        key = self.current_key()
        if key is not None:
            self.post_message(self.SuggestRequested(key))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("rp-range-remove-"):
            editor = self.query_one("#rp-range-editor", RangeEditor)
            try:
                await editor.remove_row(int(button_id.rsplit("-", 1)[-1]))
            except ValueError:
                pass
            return

        if button_id == "rp-btn-range-add":
            await self.query_one("#rp-range-editor", RangeEditor).add_row()
            return
        if button_id == "rp-btn-range-whole":
            await self.query_one("#rp-range-editor", RangeEditor).clear_rows()
            return
        if button_id == "rp-btn-range-suggest":
            key = self.current_key()
            if key is not None:
                self.post_message(self.SuggestRequested(key))
            return

        if button_id == "rp-btn-apply-quick":
            self._sync_plan()
            if self.plan is not None:
                self.post_message(self.ApplyRequested(self.plan, True))
            return
        if button_id == "rp-btn-separate":
            self.post_message(self.SeparateRequested(self._separate_plan()))
            return
        if button_id == "rp-btn-rerun":
            self.post_message(self.RerunRequested())
            return
        if button_id == "rp-btn-adjust":
            self._begin_wizard()
            return

        if button_id in ("rp-ans-yes", "rp-ans-no", "rp-ans-unsure"):
            self._answer({"rp-ans-yes": "yes", "rp-ans-no": "no", "rp-ans-unsure": "unsure"}[button_id])
            return
        if button_id == "rp-btn-back":
            if self.wizard_index > 0:
                self.wizard_index -= 1
            self._refresh()
            return
        if button_id == "rp-btn-next":
            self.wizard_index = min(self.wizard_index + 1, len(WIZARD_KEYS))
            if self.wizard_index >= len(WIZARD_KEYS):
                self.mode = "summary"
            self._refresh()
            return
        if button_id == "rp-btn-wizard-cancel":
            self.mode = "quick" if self.detection is not None else "idle"
            self._refresh()
            return
        if button_id == "rp-btn-summary-back":
            self.mode = "wizard"
            self.wizard_index = len(WIZARD_KEYS) - 1
            self._refresh()
            return
        if button_id == "rp-btn-apply-plan":
            self._sync_plan()
            if self.plan is not None:
                self.post_message(self.ApplyRequested(self.plan, False))
            return

        if button_id in ("rp-engine-local", "rp-engine-hosted"):
            self.engine = "local" if button_id == "rp-engine-local" else "hosted"
            self._refresh()
            return
        if button_id in (
            "rp-preset-gentle",
            "rp-preset-balanced",
            "rp-preset-strong",
            "rp-card-gentle",
            "rp-card-balanced",
            "rp-card-strong",
        ):
            self.strength = button_id.rsplit("-", 1)[-1]
            self._sync_plan()
            self._refresh()
            return
        if button_id in ("rp-strength-light", "rp-strength-balanced", "rp-strength-strong"):
            if self.plan is not None:
                chosen = {
                    "rp-strength-light": "light",
                    "rp-strength-balanced": "balanced",
                    "rp-strength-strong": "strong",
                }[button_id]
                self.plan.choice("roomy").intensity = DEREVERB_INTENSITY[chosen]
            self._refresh()
            return

        if button_id in ("rp-btn-prev-master", "rp-btn-prev-vocals", "rp-btn-prev-inst"):
            output = {
                "rp-btn-prev-master": "master",
                "rp-btn-prev-vocals": "vocals",
                "rp-btn-prev-inst": "inst",
            }[button_id]
            self.post_message(self.PreviewRequested(output))
            return
        if button_id == "rp-btn-export":
            self.post_message(self.ExportRequested())
            return
        if button_id == "rp-btn-improve":
            self._begin_wizard()
            return
        if button_id == "rp-btn-reanalyze":
            self.detection = None
            self.plan = None
            self.result = None
            self.mode = "idle"
            self._refresh()


__all__ = ["RangeEditor", "RangeRow", "RepairPanel", "format_timecode", "parse_timecode"]
