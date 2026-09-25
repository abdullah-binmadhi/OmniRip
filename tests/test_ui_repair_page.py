"""Integration tests for the guided REPAIR page inside the workbench."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import soundfile as sf
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Label

from harvester.models import Mode, State, TrackJob
from harvester.services.repair import RepairResult
from harvester.ui.player import AudioPlayerWidget
from harvester.ui.repair import RangeRow, RepairPanel
from harvester.ui.workbench import WorkbenchWidget

SR = 44100


class WorkbenchTestApp(App[None]):
    def compose(self) -> ComposeResult:
        yield AudioPlayerWidget(id="audio-player")
        yield WorkbenchWidget(id="test-workbench")


def _write_track(tmp_path: Path) -> Path:
    t = np.linspace(0, 2.0, 2 * SR, endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * 1000.0 * t)
    path = tmp_path / "song.mp3"
    sf.write(path, np.stack([audio, audio], axis=1), SR)
    return path


def _load(tmp_path: Path, wb: WorkbenchWidget) -> Path:
    track = _write_track(tmp_path)
    job = TrackJob(mode=Mode.SINGLE_URL, input_path=track)
    job.output_path = track
    job.state = State.COMPLETED
    job.spectral.cutoff_hz = 15000.0
    with patch.object(wb, "_trigger_enhancement_pregeneration"):
        wb.load_job(job)
    return track


async def test_repair_page_detects_quick_fixes_and_previews(tmp_path: Path) -> None:
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        _load(tmp_path, wb)
        wb.switch_page("repair")
        await app.workers.wait_for_complete()
        await pilot.pause()

        panel = app.query_one(RepairPanel)
        assert panel.mode == "quick"
        assert panel.detection is not None
        assert wb.query_one("#wb-page-repair").styles.display != "none"

        # Prepare fake repair deliverables so preview/export have real files.
        out_dir = tmp_path / "repairs"
        out_dir.mkdir()
        master = out_dir / "song.repaired.mp3"
        master.write_bytes(b"mp3-bytes")
        vocals = tmp_path / "song_repair_vocals.wav"
        inst = tmp_path / "song_repair_instrumental.wav"
        sf.write(vocals, np.zeros((SR, 2), dtype=np.float32), SR)
        sf.write(inst, np.zeros((SR, 2), dtype=np.float32), SR)
        result = RepairResult(
            master=master,
            vocals=vocals,
            inst=inst,
            residual_worst_db=-58.0,
            notes=("Stem recombination residual: worst -58.0 dBFS/segment",),
        )

        with patch("harvester.services.repair.execute_repair", return_value=result) as run:
            app.query_one("#rp-btn-apply-quick", Button).press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()

        assert run.called
        assert panel.mode == "result"
        assert wb.path_voc == vocals and wb.path_inst == inst
        assert panel.stems_ready

        with patch.object(wb, "_route_to_player") as route:
            app.query_one("#rp-btn-prev-vocals", Button).press()
            await pilot.pause()
        route.assert_called_once()
        assert Path(route.call_args[0][0]) == vocals

        export_dir = tmp_path / "exported"
        fake_config = SimpleNamespace(general=SimpleNamespace(output_dir=str(export_dir)))
        with patch("harvester.config.load_config", return_value=fake_config):
            app.query_one("#rp-btn-export", Button).press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
        assert (export_dir / "song.repaired.mp3").exists()
        assert (export_dir / "song_vocals.wav").exists()
        assert (export_dir / "song_instrumental.wav").exists()


async def test_repair_wizard_suggests_sections_from_stems(tmp_path: Path) -> None:
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        _load(tmp_path, wb)
        wb.switch_page("repair")
        await app.workers.wait_for_complete()
        await pilot.pause()

        stems_dir = tmp_path / "stems"
        stems_dir.mkdir()
        vocals = stems_dir / "song_vocals.wav"
        sf.write(vocals, np.zeros((SR, 2), dtype=np.float32), SR)
        wb.path_voc = vocals
        wb.path_inst = vocals

        panel = app.query_one(RepairPanel)
        panel.stems_ready = True
        panel.mode = "wizard"
        panel.wizard_index = 1  # harsh_s has a detector suggestion
        panel.answers["harsh_s"] = "yes"
        assert panel.plan is not None
        panel.plan.choice("harsh_s").enabled = True
        panel._refresh()
        await pilot.pause()

        with patch(
            "harvester.analysis.enhancement.segment_analysis.suggest_ranges",
            return_value=[(2.0, 3.0), (10.5, 11.0)],
        ) as suggest:
            app.query_one("#rp-btn-range-suggest", Button).press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()

        assert suggest.called
        rows = list(panel.query(RangeRow))
        assert len(rows) == 2
        assert rows[0].query(Input).first().value == "0:02.0"


async def test_hosted_engine_defers_to_the_hosted_flow(tmp_path: Path) -> None:
    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        _load(tmp_path, wb)
        with patch.object(wb, "_hosted_available", return_value=True):
            wb.switch_page("repair")
            await app.workers.wait_for_complete()
            await pilot.pause()

        panel = app.query_one(RepairPanel)
        assert panel.hosted_available
        app.query_one("#rp-engine-hosted", Button).press()
        await pilot.pause()
        assert panel.engine == "hosted"

        with (
            patch.object(wb, "_start_hosted_separation") as hosted,
            patch.object(wb, "_hosted_available", return_value=True),
        ):
            app.query_one("#rp-btn-apply-quick", Button).press()
            await pilot.pause()
            await pilot.pause()
        hosted.assert_called_once()
        assert wb._pending_repair_plan is panel.plan


async def test_hosted_repair_stems_derivation(tmp_path: Path) -> None:
    import numpy as np
    import soundfile as sf

    from harvester.processing import HOSTED_RAW_TOKEN

    app = WorkbenchTestApp()
    async with app.run_test():
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        source = _write_track(tmp_path)
        stem_dir = tmp_path / "hosted"
        stem_dir.mkdir()

        t = np.linspace(0, 2.0, 2 * SR, endpoint=False)
        lead = 0.3 * np.sin(2 * np.pi * 440.0 * t)
        back = 0.1 * np.sin(2 * np.pi * 880.0 * t)
        sf.write(stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}lead_vocals.wav", np.stack([lead, lead], axis=1), SR)
        sf.write(stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}back_vocals.wav", np.stack([back, back], axis=1), SR)

        stems = wb._hosted_repair_stems(stem_dir, source)
        assert stems is not None
        vocals, inst = stems
        assert vocals.exists() and inst.exists()
        vocals_audio, _ = sf.read(str(vocals), dtype="float32", always_2d=True)
        assert vocals_audio.shape[1] == 2
        assert float(np.max(np.abs(vocals_audio))) > 0.05

        # An explicit instrumental lane wins over the inversion fallback.
        inst_lane = stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}instrumental.wav"
        sf.write(inst_lane, np.zeros((SR, 2), dtype=np.float32), SR)
        assert wb._hosted_repair_stems(stem_dir, source) == (vocals, inst_lane)

        # No vocals lane at all -> None (repair cannot proceed on hosted output).
        for raw in stem_dir.glob("*vocal*.wav"):
            raw.unlink()
        assert wb._hosted_repair_stems(stem_dir, source) is None


async def test_repair_page_is_visible_and_separates_without_analysis(tmp_path: Path) -> None:
    """Regression: the page rendered a zero-height panel; SEPARATE STEMS must work unfixed."""
    app = WorkbenchTestApp()
    async with app.run_test(size=(120, 44)) as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        _load(tmp_path, wb)
        wb.switch_page("repair")
        await app.workers.wait_for_complete()
        await pilot.pause()

        panel = app.query_one(RepairPanel)
        assert panel.size.height > 0
        card = panel.query_one("#rp-quick")
        assert card.styles.display == "block" and card.size.height > 0
        assert "◈" in str(panel.query_one("#rp-engine-badge", Label).render())
        assert not panel.query_one("#rp-btn-apply-quick", Button).disabled

        out_dir = tmp_path / "repairs2"
        out_dir.mkdir()
        master = out_dir / "song.repaired.mp3"
        master.write_bytes(b"mp3-bytes")
        vocals = tmp_path / "sep_vocals.wav"
        inst = tmp_path / "sep_inst.wav"
        sf.write(vocals, np.zeros((SR, 2), dtype=np.float32), SR)
        sf.write(inst, np.zeros((SR, 2), dtype=np.float32), SR)
        result = RepairResult(
            master=master, vocals=vocals, inst=inst, residual_worst_db=-60.0, notes=("ok",)
        )

        with patch("harvester.services.repair.execute_repair", return_value=result) as run:
            app.query_one("#rp-btn-separate", Button).press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()

        assert run.called
        plan = run.call_args[0][1]
        assert plan.enabled() == []
        assert panel.mode == "result"


async def test_repair_rerun_reanalyzes_the_track(tmp_path: Path) -> None:
    from harvester.analysis.enhancement.acoustic_detector import (
        analyze_track_acoustics as real_analyze,
    )

    app = WorkbenchTestApp()
    async with app.run_test() as pilot:
        wb = app.query_one("#test-workbench", WorkbenchWidget)
        _load(tmp_path, wb)
        wb.switch_page("repair")
        await app.workers.wait_for_complete()
        await pilot.pause()

        panel = app.query_one(RepairPanel)
        assert panel.detection is not None
        panel.detection = None  # simulate a stale/failed analysis
        panel.error = "boom"
        panel._refresh()
        await pilot.pause()

        with patch(
            "harvester.ui.workbench.analyze_track_acoustics",
            side_effect=real_analyze,
        ) as analyze:
            app.query_one("#rp-btn-rerun", Button).press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()

        assert analyze.called
        assert panel.detection is not None
        assert panel.error is None
        assert panel.mode == "quick"
