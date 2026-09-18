from pathlib import Path

from harvester.models import (
    CanonicalMetadata,
    DownloadProgress,
    EventKind,
    JobEvent,
    Mode,
    SourceKind,
    State,
    TrackJob,
    Verdict,
)


def test_canonical_metadata_normalizes_artists_and_serializes() -> None:
    metadata = CanonicalMetadata(title="Song", artists=["A", "B"], year=2024)

    assert metadata.artist == "A / B"
    assert metadata.to_dict()["artists"] == ["A", "B"]


def test_track_job_display_name_prefers_canonical_metadata() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT, input_path=Path("/music/song.mp3"))
    job.canonical_meta = CanonicalMetadata(title="Song", artists=("Artist",))

    assert job.display_name == "Artist — Song"
    assert job.to_dict()["mode"] == "BATCH_AUDIT"


def test_job_event_serializes_enum_values() -> None:
    event = JobEvent(
        job_id="abc",
        kind=EventKind.PROGRESS,
        state=State.P2P_DOWNLOADING,
        progress=DownloadProgress(bytes_done=10, percent=25),
    )

    payload = event.to_dict()
    assert payload["kind"] == "PROGRESS"
    assert payload["state"] == "P2P_DOWNLOADING"
    assert payload["progress"]["percent"] == 25


def test_source_and_verdict_defaults_are_explicit() -> None:
    job = TrackJob(mode=Mode.SINGLE_URL)

    assert job.source_kind is SourceKind.NONE
    assert job.spectral.verdict is Verdict.NOT_APPLICABLE
