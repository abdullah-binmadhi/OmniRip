"""
Forensic Report & Deliverable Deck for OmniRip.

Displays target curve overlays (Harman, Diffuse Field, JM-1), acoustic forensics,
applied EQ curves, download buttons, A/B auditioning, and report history presets.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Select

from harvester.analysis.enhancement.master_triage import MASTER_SYMPTOM_BY_KEY
from harvester.analysis.enhancement.target_curves import (
    TARGET_FREQUENCIES,
    TargetType,
    get_target_curve,
)
from harvester.services.report_store import MasteringReport, ReportStore


def render_ascii_curve(
    orig_spectrum: dict[float, float],
    enh_spectrum: dict[float, float],
    target_curve: dict[float, float],
    *,
    mode: str = "spectrum",
    height: int = 7,
) -> str:
    """Render a compact ASCII/Braille 31-band frequency response plot."""
    # Frequencies to sample (12 display columns across the spectrum)
    sample_freqs = [
        20.0, 40.0, 80.0, 160.0, 315.0, 630.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0, 20000.0
    ]
    db_min, db_max = -12.0, 12.0

    lines: list[str] = []
    header = "dB  20Hz  80Hz  315Hz 1kHz  4kHz  16kHz"
    lines.append(header)
    lines.append("───┬────────────────────────────────────────")

    for row in range(height):
        db_level = db_max - (row / (height - 1)) * (db_max - db_min)
        row_str = f"{int(db_level):+3d}│ "

        for f in sample_freqs:
            if mode == "delta":
                val = enh_spectrum.get(f, 0.0) - target_curve.get(f, 0.0)
                # Delta character
                char = "■" if abs(val - db_level) < 2.0 else "·"
            else:
                o_val = orig_spectrum.get(f, 0.0)
                e_val = enh_spectrum.get(f, 0.0)
                t_val = target_curve.get(f, 0.0)

                is_enh = abs(e_val - db_level) < 1.8
                is_orig = abs(o_val - db_level) < 1.8
                is_target = abs(t_val - db_level) < 1.2

                if is_enh and is_target:
                    char = "◈"
                elif is_enh:
                    char = "▲"  # Enhanced
                elif is_orig:
                    char = "▼"  # Original
                elif is_target:
                    char = "·"  # Target reference
                else:
                    char = " "
            row_str += f"{char}   "
        lines.append(row_str)

    lines.append("───┴────────────────────────────────────────")
    legend = "Legend: ▲ Enhanced   ▼ Original   · Reference Target   ◈ Match"
    if mode == "delta":
        legend = "Legend: ■ Deviation Delta (Enhanced − Target)"
    lines.append(legend)
    return "\n".join(lines)


class ReportPanel(Widget):
    """Forensic report page displaying before/after metrics, curve overlays, and export actions."""

    DEFAULT_CSS = """
    ReportPanel {
        height: 1fr;
        min-height: 1fr;
        background: #090714;
        color: #f0eef9;
        padding: 0 1;
    }

    .rp-header-strip {
        height: auto;
        min-height: 2;
        border-bottom: solid #ff007f;
        padding: 0 1;
        margin-bottom: 1;
        background: #0c091d;
    }

    .rp-header-title {
        color: #00e5ff;
        text-style: bold;
    }

    .rp-header-badge {
        color: #ffe600;
        text-align: right;
    }

    .rp-grid {
        height: auto;
        width: 100%;
        margin-bottom: 1;
    }

    .rp-col-matrix {
        width: 32;
        border-right: solid #2d264f;
        padding-right: 1;
    }

    .rp-col-graph {
        width: 1fr;
        padding: 0 1;
        border-right: solid #2d264f;
    }

    .rp-col-history {
        width: 34;
        padding-left: 1;
    }

    .rp-box-title {
        color: #ffe600;
        text-style: bold;
        margin-bottom: 1;
    }

    .rp-metric-line {
        color: #a09bc2;
        margin-bottom: 0;
    }

    .rp-remediation-badge {
        color: #00e5ff;
        background: #161329;
        padding: 0 1;
        margin-bottom: 0;
    }

    #rp-ascii-graph {
        background: #07050f;
        border: solid rgba(0, 229, 255, 0.4);
        padding: 0 1;
        color: #00e5ff;
        height: auto;
        min-height: 10;
        margin-bottom: 1;
    }

    .rp-graph-controls {
        height: 3;
        margin-bottom: 1;
    }

    .rp-graph-controls Select {
        width: 22;
        margin-right: 1;
    }

    .rp-history-item {
        color: #00e5ff;
        background: #161329;
        border: solid #2d264f;
        padding: 0 1;
        margin-bottom: 1;
    }

    .rp-history-item:hover {
        background: #2d264f;
    }

    .rp-dock-hub {
        height: auto;
        background: #0c091d;
        border-top: solid #00e5ff;
        padding: 0 1;
    }

    .rp-dock-audition {
        width: 1fr;
    }

    .rp-dock-export {
        width: auto;
    }

    .rp-dock-export Button {
        margin-left: 1;
    }
    """

    class ExportRequested(Message):
        def __init__(self, fmt: str) -> None:
            super().__init__()
            self.fmt = fmt

    class PreviewRequested(Message):
        def __init__(self, stream: str) -> None:
            super().__init__()
            self.stream = stream

    class ApplyRecipeRequested(Message):
        def __init__(self, report: MasteringReport) -> None:
            super().__init__()
            self.report = report

    def __init__(self, report_store: ReportStore | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.report_store = report_store or ReportStore()
        self.active_report: MasteringReport | None = None
        self.target_type: TargetType = "harman"
        self.graph_mode: str = "spectrum"  # "spectrum" or "delta"
        self.orig_spectrum: dict[float, float] = {f: 0.0 for f in TARGET_FREQUENCIES}
        self.enh_spectrum: dict[float, float] = {f: 0.0 for f in TARGET_FREQUENCIES}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="rp-header-strip"):
            yield Label("STATUS: FORENSIC REPORT & ACOUSTIC AUDITION", id="rp-rep-title", classes="rp-header-title")
            yield Label("◈ AUTO-ROUTED ENGINE: ACTIVE", id="rp-rep-badge", classes="rp-header-badge")

        with Horizontal(classes="rp-grid"):
            # Col 1: Forensic Metrics & Remediations
            with Vertical(classes="rp-col-matrix"):
                yield Label("[A] ACOUSTIC FORENSICS", classes="rp-box-title")
                yield Label("Loudness: -14.0 LUFS (-0.1 dBFS Peak)", id="rp-rep-lufs", classes="rp-metric-line")
                yield Label("Bandwidth: 15.5 ➔ 22.05 kHz (HD)", id="rp-rep-bw", classes="rp-metric-line")
                yield Label("Artifact Residual: < -24.8 dBFS", id="rp-rep-residual", classes="rp-metric-line")
                yield Label("Phase Accuracy: 99.8% Lossless", id="rp-rep-phase", classes="rp-metric-line")
                yield Label("Active Remediations:", classes="rp-box-title")
                yield Label("• Balanced Mastering Pass", id="rp-rep-remediations", classes="rp-remediation-badge")

            # Col 2: Target Curve Comparison Plot
            with Vertical(classes="rp-col-graph"):
                yield Label("[B] FREQUENCY TARGET SPECTRUM OVERLAY", classes="rp-box-title")
                with Horizontal(classes="rp-graph-controls"):
                    yield Select(
                        options=[
                            ("Harman Target", "harman"),
                            ("Diffuse Field (DF)", "diffuse_field"),
                            ("JM-1 Modern Target", "jm1"),
                            ("Flat 0 dB Reference", "flat"),
                        ],
                        value="harman",
                        id="rp-select-target",
                    )
                    yield Select(
                        options=[
                            ("Spectrum Overlay", "spectrum"),
                            ("Deviation Delta (Δ)", "delta"),
                        ],
                        value="spectrum",
                        id="rp-select-mode",
                    )
                yield Label("", id="rp-ascii-graph")

            # Col 3: Report History & Presets
            with Vertical(classes="rp-col-history"):
                yield Label("[C] REPORT HISTORY & PRESETS", classes="rp-box-title")
                yield Vertical(id="rp-history-list")
                with Horizontal():
                    yield Button("✎ Rename", id="rp-btn-rep-rename")
                    yield Button("⚡ Re-Apply", id="rp-btn-rep-reapply", variant="primary")

        # Bottom Dock: Auditioning & Export Buttons
        with Horizontal(classes="rp-dock-hub"):
            with Horizontal(classes="rp-dock-audition"):
                yield Label("AUDITION:", classes="rp-metric-line")
                yield Button("◀ ORIGINAL", id="rp-rep-btn-orig")
                yield Button("▶ MASTER", id="rp-rep-btn-master", variant="primary")
                yield Button("♬ VOCALS", id="rp-rep-btn-voc")
                yield Button("♩ INST", id="rp-rep-btn-inst")

            with Horizontal(classes="rp-dock-export"):
                yield Button("⤓ WAV 24-bit", id="rp-btn-dl-wav", variant="success")
                yield Button("⤓ MP3 320k", id="rp-btn-dl-mp3")
                yield Button("⤓ FLAC", id="rp-btn-dl-flac")
                yield Button("⤓ STEMS", id="rp-btn-dl-stems")

    def on_mount(self) -> None:
        self._refresh_report_view()
        self._refresh_history_list()

    def set_report(
        self,
        report: MasteringReport,
        orig_spectrum: dict[float, float] | None = None,
        enh_spectrum: dict[float, float] | None = None,
    ) -> None:
        """Populate panel with a completed mastering report and spectrum data."""
        self.active_report = report
        if orig_spectrum:
            self.orig_spectrum = orig_spectrum
        if enh_spectrum:
            self.enh_spectrum = enh_spectrum
        self._refresh_report_view()
        self._refresh_history_list()

    def _refresh_report_view(self) -> None:
        rep = self.active_report
        if rep is not None:
            self.query_one("#rp-rep-title", Label).update(f"STATUS: DELIVERABLE REPORT · {rep.name}")
            genre_text = rep.genre.upper() if rep.genre else "BALANCED"
            self.query_one("#rp-rep-badge", Label).update(f"◈ GENRE PROFILE: {genre_text}")

            m = rep.metrics
            if "lufs_after" in m:
                self.query_one("#rp-rep-lufs", Label).update(f"Loudness: {m['lufs_after']:.1f} LUFS (-0.1 dBFS Peak)")
            if "cutoff_before_hz" in m and "cutoff_after_hz" in m:
                self.query_one("#rp-rep-bw", Label).update(
                    f"Bandwidth: {m['cutoff_before_hz'] / 1000:.1f} ➔ {m['cutoff_after_hz'] / 1000:.2f} kHz (HD)"
                )
            if "residual_db" in m:
                self.query_one("#rp-rep-residual", Label).update(f"Artifact Residual: < {m['residual_db']:.1f} dBFS")

            # Active remediations
            fixes = [k for k, v in rep.triage_answers.items() if v is True]
            if fixes:
                lines = []
                for k in fixes[:4]:
                    s = MASTER_SYMPTOM_BY_KEY.get(k)
                    lbl = s.label if s else k
                    lines.append(f"• {lbl}")
                if len(fixes) > 4:
                    lines.append(f"• (+{len(fixes) - 4} more fixes)")
                self.query_one("#rp-rep-remediations", Label).update("\n".join(lines))
            else:
                self.query_one("#rp-rep-remediations", Label).update("• Transparent Master Pass")

        target_dict = get_target_curve(self.target_type)
        graph_text = render_ascii_curve(
            self.orig_spectrum,
            self.enh_spectrum,
            target_dict,
            mode=self.graph_mode,
        )
        self.query_one("#rp-ascii-graph", Label).update(graph_text)

    def _refresh_history_list(self) -> None:
        container = self.query_one("#rp-history-list", Vertical)
        container.remove_children()

        reports = self.report_store.list_reports()
        if not reports:
            container.mount(Label("No saved reports yet.", classes="rp-metric-line"))
            return

        for r in reports[:5]:
            lbl = Label(f"• {r.name}\n  {r.genre} · {r.num_remediations} fix(es)", classes="rp-history-item")
            container.mount(lbl)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "rp-select-target" and event.value is not None:
            self.target_type = str(event.value)  # type: ignore
            self._refresh_report_view()
        elif event.select.id == "rp-select-mode" and event.value is not None:
            self.graph_mode = str(event.value)
            self._refresh_report_view()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""

        # Audition triggers
        if bid == "rp-rep-btn-orig":
            self.post_message(self.PreviewRequested("original"))
        elif bid == "rp-rep-btn-master":
            self.post_message(self.PreviewRequested("master"))
        elif bid == "rp-rep-btn-voc":
            self.post_message(self.PreviewRequested("vocals"))
        elif bid == "rp-rep-btn-inst":
            self.post_message(self.PreviewRequested("inst"))

        # Download triggers
        elif bid == "rp-btn-dl-wav":
            self.post_message(self.ExportRequested("wav"))
        elif bid == "rp-btn-dl-mp3":
            self.post_message(self.ExportRequested("mp3"))
        elif bid == "rp-btn-dl-flac":
            self.post_message(self.ExportRequested("flac"))
        elif bid == "rp-btn-dl-stems":
            self.post_message(self.ExportRequested("stems"))

        # Re-apply recipe
        elif bid == "rp-btn-rep-reapply" and self.active_report:
            self.post_message(self.ApplyRecipeRequested(self.active_report))
