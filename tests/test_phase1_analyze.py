"""Phase 1 analysis unit tests (URL validation, query building, live rejection)."""

from __future__ import annotations

import pytest

from harvester.models import Mode, TrackJob
from harvester.pipeline.phase1_analyze import analyze_url, build_query, validate_url
from harvester.util.errors import PermanentSource, ValidationError


def test_validate_url_normalizes() -> None:
    assert validate_url("  https://example.test/v?v=1  ") == "https://example.test/v?v=1"


def test_validate_url_rejects_non_http() -> None:
    with pytest.raises(ValidationError):
        validate_url("ftp://example.test/x")
    with pytest.raises(ValidationError):
        validate_url("not a url")


def test_validate_url_accepts_ytsearch_queries() -> None:
    assert validate_url("ytsearch1:Imogen Heap Headlock") == "ytsearch1:Imogen Heap Headlock"
    assert validate_url("  ytsearch:anything at all  ") == "ytsearch:anything at all"


def test_build_query_from_artist_and_title() -> None:
    assert build_query({"artist": "A", "title": "T"}) == "A - T"


def test_build_query_from_uploader_and_track() -> None:
    assert build_query({"uploader": "Channel", "track": "Song"}) == "Channel - Song"


def test_build_query_keeps_title_separator() -> None:
    assert build_query({"title": "A - B"}) == "A - B"


def test_build_query_plain_title_and_empty() -> None:
    assert build_query({"title": "JustTitle"}) == "JustTitle"
    assert build_query({}) == ""


@pytest.mark.asyncio
async def test_analyze_url_rejects_live_streams() -> None:
    class FakeYtdlp:
        async def probe_url(self, url: str, *, job_id: str | None = None):
            return {"is_live": True, "title": "x"}

    job = TrackJob(mode=Mode.SINGLE_URL, input_url="https://example.test/v")

    with pytest.raises(PermanentSource):
        await analyze_url(job, FakeYtdlp())


@pytest.mark.asyncio
async def test_analyze_url_populates_meta_and_query() -> None:
    class FakeYtdlp:
        async def probe_url(self, url: str, *, job_id: str | None = None):
            return {"title": "Song", "uploader": "Channel", "duration": 10}

    job = TrackJob(mode=Mode.SINGLE_URL, input_url="https://example.test/v")

    await analyze_url(job, FakeYtdlp())

    assert job.probe_meta["title"] == "Song"
    assert job.query_raw == "Channel - Song"


@pytest.mark.asyncio
async def test_analyze_url_resolves_search_to_first_entry() -> None:
    class FakeYtdlp:
        async def probe_url(self, url: str, *, job_id: str | None = None):
            return {
                "_type": "playlist",
                "title": "Search results",
                "entries": [
                    {"webpage_url": "https://example.test/song", "title": "Headlock", "uploader": "Imogen Heap"},
                ],
            }

    job = TrackJob(mode=Mode.SINGLE_URL, input_url="ytsearch1:Imogen Heap Headlock")

    await analyze_url(job, FakeYtdlp())

    assert job.input_url == "https://example.test/song"
    assert job.probe_meta["webpage_url"] == "https://example.test/song"
    assert job.query_raw == "Imogen Heap - Headlock"


@pytest.mark.asyncio
async def test_analyze_url_rejects_empty_search_results() -> None:
    class EmptySearchYtdlp:
        async def probe_url(self, url: str, *, job_id: str | None = None):
            return {"_type": "playlist", "entries": []}

    job = TrackJob(mode=Mode.SINGLE_URL, input_url="ytsearch1:Nothing Found Here")

    with pytest.raises(ValidationError):
        await analyze_url(job, EmptySearchYtdlp())
