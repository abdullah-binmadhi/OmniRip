from pathlib import Path

import httpx
import pytest

from harvester.config import load_config
from harvester.services.acoustid import AcoustidService, Fingerprint

_RESPONSE = {
    "status": "ok",
    "results": [
        {
            "score": 0.95,
            "recordings": [
                {
                    "id": "rec-1",
                    "title": "Real Title",
                    "artists": [{"id": "art-1", "name": "Real Artist"}],
                    "isrcs": ["USABC1234567"],
                    "releases": [
                        {"id": "rel-modern", "title": "Reissue", "date": {"year": 2010}},
                        {"id": "rel-original", "title": "Album", "date": {"year": 1979}},
                    ],
                }
            ],
        }
    ],
}


def _config(tmp_path: Path):
    return load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"acoustid.cache_ttl_days": 90},
    )


@pytest.mark.asyncio
async def test_lookup_maps_fields_and_prefers_earliest_release(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ACOUSTID_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_RESPONSE)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AcoustidService(config, client=client)

    metadata = await service.lookup(Fingerprint(duration=120.0, value="abc"))

    assert metadata is not None
    assert metadata.title == "Real Title"
    assert metadata.artist == "Real Artist"
    assert metadata.album == "Album"
    assert metadata.year == 1979
    assert metadata.isrc == "USABC1234567"
    assert metadata.mb_recording_id == "rec-1"
    assert metadata.mb_release_id == "rel-original"
    assert metadata.source == "acoustid"
    await client.aclose()


@pytest.mark.asyncio
async def test_lookup_uses_cache_and_skips_network(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ACOUSTID_API_KEY", "test-key")
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_RESPONSE)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AcoustidService(config, client=client)
    fingerprint = Fingerprint(duration=120.0, value="stable-fingerprint")

    first = await service.lookup(fingerprint)
    second = await service.lookup(fingerprint)

    assert first is not None and second is not None
    assert second.title == first.title
    assert calls["count"] == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_low_confidence_result_is_rejected(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ACOUSTID_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "results": [{"score": 0.3, "recordings": [{"title": "Weak"}]}],
            },
        )

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AcoustidService(config, client=client)

    metadata = await service.lookup(Fingerprint(duration=10.0, value="xyz"))

    assert metadata is None
    await client.aclose()


@pytest.mark.asyncio
async def test_lookup_sends_meta_as_repeatable_params(tmp_path: Path, monkeypatch) -> None:
    """AcoustID's `meta` must repeat as separate form fields.

    A single "+"-joined string is URL-encoded to a literal '+', and AcoustID then
    answers with bare results (id + score, no recordings) — i.e. identification
    silently resolves nothing.
    """
    monkeypatch.setenv("ACOUSTID_API_KEY", "test-key")
    seen: dict[str, list[str]] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["meta"] = [
            value
            for key, value in httpx.QueryParams(request.content.decode()).multi_items()
            if key == "meta"
        ]
        return httpx.Response(200, json=_RESPONSE)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AcoustidService(config, client=client)

    metadata = await service.lookup(Fingerprint(duration=120.0, value="abc"))

    assert metadata is not None and metadata.title == "Real Title"
    assert seen["meta"] == ["recordings", "releases", "releasegroups", "isrcs"]
    await client.aclose()


@pytest.mark.asyncio
async def test_missing_api_key_returns_none_without_network(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ACOUSTID_API_KEY", raising=False)
    config = load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
    )
    service = AcoustidService(config)

    metadata = await service.lookup(Fingerprint(duration=10.0, value="xyz"))

    assert metadata is None
    assert service.configured is False
    await service.close()
