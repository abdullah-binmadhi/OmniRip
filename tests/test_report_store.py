"""Unit tests for the Persistent Report Store."""

from __future__ import annotations

from pathlib import Path

from harvester.services.report_store import ReportStore


def test_save_and_list_reports(tmp_path: Path):
    store = ReportStore(reports_dir=tmp_path)
    assert len(store.list_reports()) == 0

    rep1 = store.save_report(
        track_name="Song One",
        track_path="/path/to/one.mp3",
        genre="Classic Rock",
        triage_answers={"cold_digital": True, "too_bright": True},
        eq_bands={"62": 1.5, "1000": -0.5},
        metrics={"lufs_after": -14.0},
    )
    assert rep1.id.startswith("rep_")

    rep2 = store.save_report(
        track_name="Song Two",
        track_path="/path/to/two.mp3",
        genre="Hip-Hop",
        triage_answers={"boomy_low": True},
    )

    summaries = store.list_reports()
    assert len(summaries) == 2
    # Newest first
    assert summaries[0].id == rep2.id
    assert summaries[1].id == rep1.id
    assert summaries[1].num_remediations == 2
    assert summaries[0].num_remediations == 1


def test_get_and_rename_report(tmp_path: Path):
    store = ReportStore(reports_dir=tmp_path)
    rep = store.save_report(
        track_name="Acoustic Song",
        track_path="song.wav",
        genre="Acoustic",
        triage_answers={"too_dark": True},
        eq_bands={"16000": 2.0},
    )

    loaded = store.get_report(rep.id)
    assert loaded is not None
    assert loaded.track_name == "Acoustic Song"
    assert loaded.triage_answers.get("too_dark") is True
    assert loaded.eq_bands.get("16000") == 2.0

    # Rename
    success = store.rename_report(rep.id, "Warm Vintage Acoustic Master")
    assert success is True

    renamed = store.get_report(rep.id)
    assert renamed is not None
    assert renamed.name == "Warm Vintage Acoustic Master"


def test_delete_report(tmp_path: Path):
    store = ReportStore(reports_dir=tmp_path)
    rep = store.save_report(
        track_name="Temp Track",
        track_path="temp.mp3",
    )
    assert store.get_report(rep.id) is not None

    deleted = store.delete_report(rep.id)
    assert deleted is True
    assert store.get_report(rep.id) is None
    assert len(store.list_reports()) == 0
