"""Unit tests for the ReportPanel widget."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Button, Label, Select

from harvester.services.report_store import ReportStore
from harvester.ui.report import ReportPanel


class ReportTestApp(App):
    def __init__(self, store: ReportStore | None = None) -> None:
        super().__init__()
        self.store = store

    def compose(self) -> ComposeResult:
        yield ReportPanel(report_store=self.store)


async def test_report_panel_mount_and_render_ascii_graph(tmp_path: Path):
    store = ReportStore(reports_dir=tmp_path)
    app = ReportTestApp(store=store)
    async with app.run_test() as pilot:
        panel = app.query_one(ReportPanel)
        assert panel is not None

        # Verify initial graph is present
        graph = app.query_one("#rp-ascii-graph", Label).render().plain
        assert "20Hz" in graph
        assert "1kHz" in graph
        assert "Enhanced" in graph

        # Change target to Diffuse Field
        sel_target = app.query_one("#rp-select-target", Select)
        sel_target.value = "diffuse_field"
        await pilot.pause()
        assert panel.target_type == "diffuse_field"

        # Change display mode to Delta
        sel_mode = app.query_one("#rp-select-mode", Select)
        sel_mode.value = "delta"
        await pilot.pause()
        assert panel.graph_mode == "delta"
        graph_delta = app.query_one("#rp-ascii-graph", Label).render().plain
        assert "Deviation Delta" in graph_delta


async def test_report_panel_set_report_and_button_messages(tmp_path: Path):
    store = ReportStore(reports_dir=tmp_path)
    rep = store.save_report(
        track_name="Nightcall",
        track_path="nightcall.mp3",
        genre="Synthwave",
        triage_answers={"cold_digital": True, "too_dark": True},
        metrics={
            "lufs_after": -13.8,
            "cutoff_before_hz": 15400,
            "cutoff_after_hz": 22050,
            "residual_db": -25.4,
        },
    )

    app = ReportTestApp(store=store)
    async with app.run_test() as pilot:
        panel = app.query_one(ReportPanel)
        panel.set_report(rep)
        await pilot.pause()

        title = app.query_one("#rp-rep-title", Label).render().plain
        assert "Nightcall" in title

        bw = app.query_one("#rp-rep-bw", Label).render().plain
        assert "15.4" in bw
        assert "22.05" in bw

        lufs = app.query_one("#rp-rep-lufs", Label).render().plain
        assert "-13.8 LUFS" in lufs

        # Test refresh button clicks post RefreshRequested message
        refresh_btn = app.query_one("#rp-btn-graph-refresh", Button)
        assert refresh_btn is not None
        refresh_btn.press()
        await pilot.pause()

        # Verify enh_spectrum was calculated and contains ISO target frequencies
        assert len(panel.enh_spectrum) > 0
        assert 1000.0 in panel.enh_spectrum
