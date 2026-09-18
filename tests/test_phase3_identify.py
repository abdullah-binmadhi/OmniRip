"""Phase 3 identity fallback-chain and identity-shift unit tests (docs/03 Phase 3)."""

from __future__ import annotations

from harvester.models import CanonicalMetadata, Mode, TrackJob
from harvester.pipeline.phase3_identify import (
    _identity_shift,
    _orig_year,
    identify_from_fallback,
    metadata_from_orig_tags,
    metadata_from_query,
)


def test_metadata_from_orig_tags_populates_fields() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.orig_tags = {"title": "T", "artist": "A", "album": "Al", "date": ["1987-05-01"]}

    metadata = metadata_from_orig_tags(job)

    assert metadata.title == "T"
    assert metadata.artist == "A"
    assert metadata.album == "Al"
    assert metadata.year == 1987
    assert metadata.source == "original_tags"


def test_metadata_from_orig_tags_handles_list_values() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.orig_tags = {"title": ["Track"], "artist": ["Artist"]}

    metadata = metadata_from_orig_tags(job)

    assert metadata.title == "Track"
    assert metadata.artist == "Artist"


def test_metadata_from_query_splits_artist_title() -> None:
    metadata = metadata_from_query("Artist - Title")
    assert metadata.title == "Title"
    assert metadata.artist == "Artist"
    assert metadata.source == "filename"


def test_metadata_from_query_plain_stem() -> None:
    metadata = metadata_from_query("JustTitle")
    assert metadata.title == "JustTitle"
    assert metadata.artists == ()


def test_identity_shift_detects_title_divergence() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.orig_tags = {"title": "Original Title"}
    job.canonical_meta = CanonicalMetadata(title="Completely Different")

    assert _identity_shift(job) is True


def test_identity_shift_false_for_matching_title() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.orig_tags = {"title": "Same Title"}
    job.canonical_meta = CanonicalMetadata(title="Same Title")

    assert _identity_shift(job) is False


def test_identity_shift_detects_mbid_mismatch() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.orig_tags = {"musicbrainz_trackid": "rec-a"}
    job.canonical_meta = CanonicalMetadata(mb_recording_id="rec-b")

    assert _identity_shift(job) is True


def test_identity_shift_ignored_for_mode_a() -> None:
    job = TrackJob(mode=Mode.SINGLE_URL)
    job.orig_tags = {"title": "X"}
    job.canonical_meta = CanonicalMetadata(title="Y")

    assert _identity_shift(job) is False


def test_identify_from_fallback_uses_orig_tags_for_batch() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.orig_tags = {"title": "T", "artist": "A"}

    metadata = identify_from_fallback(job)

    assert metadata.source == "original_tags"


def test_identify_from_fallback_uses_filename_query() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT, query_raw="Artist - Track")

    metadata = identify_from_fallback(job)

    assert metadata.source == "filename"
    assert metadata.title == "Track"


def test_orig_year_extracts_four_digit_prefix() -> None:
    job = TrackJob(mode=Mode.BATCH_AUDIT)
    job.orig_tags = {"date": ["1987-05-01"]}

    assert _orig_year(job) == 1987

    job.orig_tags = {"year": "2001"}
    assert _orig_year(job) == 2001

    job.orig_tags = {}
    assert _orig_year(job) is None