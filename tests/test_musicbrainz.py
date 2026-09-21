from pathlib import Path

import httpx
import pytest

from harvester.config import load_config
from harvester.services.musicbrainz import CoverArtService


def _config(tmp_path: Path):
    return load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})


@pytest.mark.asyncio
async def test_fetch_front_returns_bytes_and_caches(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"JPEGDATA")

    config = _config(tmp_path)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://coverartarchive.org"
    )
    service = CoverArtService(config, client=client)

    first = await service.fetch_front("release-1")
    second = await service.fetch_front("release-1")

    assert first == b"JPEGDATA"
    assert second == b"JPEGDATA"
    assert (config.paths.cache / "art" / "release-1.jpg").is_file()
    await client.aclose()


@pytest.mark.asyncio
async def test_missing_cover_returns_none(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    config = _config(tmp_path)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://coverartarchive.org"
    )
    service = CoverArtService(config, client=client)

    assert await service.fetch_front("release-missing") is None
    await client.aclose()


# ----------------------------------------------------------------------
# Recording credits (docs/13): the deterministic half of the lane plan
# ----------------------------------------------------------------------

_HEADLOCK_PAYLOAD = {
    "id": "d871b5ab-0a48-4b93-95d7-be3e6a599248",
    "title": "Headlock",
    "relations": [
        {
            "type": "instrument",
            "attributes": ["double bass"],
            "artist": {"id": "a1", "name": "Mich Gerber"},
        },
        {
            "type": "vocal",
            "attributes": ["lead vocals"],
            "artist": {"id": "a2", "name": "Imogen Heap"},
        },
        {"type": "vocal", "attributes": [], "artist": {"id": "a3", "name": "Richie Mills"}},
        {"type": "producer", "attributes": [], "artist": {"id": "a2", "name": "Imogen Heap"}},
        {"type": "performance", "attributes": [], "artist": None},
    ],
}


def _credits_service(tmp_path: Path, handler) -> CoverArtService:
    config = _config(tmp_path)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://musicbrainz.org"
    )
    return CoverArtService(config, client=client)


@pytest.mark.asyncio
async def test_recording_credits_split_instruments_and_vocals(tmp_path: Path) -> None:
    """Instruments, vocals, producers and the singer count come back typed."""
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=_HEADLOCK_PAYLOAD)

    service = _credits_service(tmp_path, handler)
    credits = await service.fetch_recording_credits("d871b5ab-0a48-4b93-95d7-be3e6a599248")

    assert credits is not None
    assert credits.title == "Headlock"
    assert credits.instrument_names == ("double bass",)
    assert [c.artist for c in credits.vocals] == ["Imogen Heap", "Richie Mills"]
    assert credits.singer_count == 2
    assert [c.name for c in credits.producers] == ["producer"]
    assert credits.performers and credits.performers[0].artist == ""
    # Lane-annotating credits are instruments + vocal parts (no producers).
    assert [c.name for c in credits.lane_credits] == ["double bass", "lead vocals", "vocal"]
    # MusicBrainz requires a descriptive User-Agent and artist-rels.
    assert calls and calls[0].headers["User-Agent"].startswith("OmniRip/")
    assert "artist-rels" in str(calls[0].url)
    await service.close()


@pytest.mark.asyncio
async def test_recording_credits_are_cached_on_disk(tmp_path: Path) -> None:
    """A second lookup is served from the credits cache, not the network."""
    hits = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        hits["n"] += 1
        return httpx.Response(200, json=_HEADLOCK_PAYLOAD)

    service = _credits_service(tmp_path, handler)
    first = await service.fetch_recording_credits("mbid-1")
    second = await service.fetch_recording_credits("mbid-1")

    assert hits["n"] == 1
    assert first is not None and second is not None
    assert second.instrument_names == first.instrument_names
    assert second.singer_count == first.singer_count
    assert (service.config.paths.cache / "credits" / "mbid-1.json").is_file()
    await service.close()


@pytest.mark.asyncio
async def test_recording_credits_degrade_quietly(tmp_path: Path) -> None:
    """404/500/empty recording ids never raise — they return None."""
    async def handler(request: httpx.Request) -> httpx.Response:
        if "missing" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(500)

    service = _credits_service(tmp_path, handler)
    assert await service.fetch_recording_credits("missing") is None
    assert await service.fetch_recording_credits("boom") is None
    assert await service.fetch_recording_credits("") is None
    await service.close()


@pytest.mark.asyncio
async def test_recording_credits_without_relations_is_empty_not_an_error(tmp_path: Path) -> None:
    """An undocumented recording reports 'empty', so the UI can say so."""
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "mbid-2", "title": "Nobody Knows"})

    service = _credits_service(tmp_path, handler)
    credits = await service.fetch_recording_credits("mbid-2")

    assert credits is not None
    assert credits.empty is True
    assert credits.singer_count is None
    assert "no credits documented" in credits.summary()
    await service.close()
