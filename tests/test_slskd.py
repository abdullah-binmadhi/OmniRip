import json
from pathlib import Path

import httpx
import pytest

from harvester.config import load_config
from harvester.models import P2PCandidate
from harvester.services.slskd import SlskdService
from harvester.util.circuit import BreakerState


def _config(tmp_path: Path):
    return load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides={"slskd.download_dir": str(tmp_path / "downloads")},
    )


@pytest.mark.asyncio
async def test_health_check_and_openapi_verification(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v0/session":
            return httpx.Response(200, json={"state": "Connected"})
        if request.url.path == "/swagger/v0/swagger.json":
            return httpx.Response(
                200,
                json={
                    "paths": {
                        "/api/v0/searches": {},
                        "/api/v0/session": {},
                        "/api/v0/transfers/downloads": {},
                    }
                },
            )
        return httpx.Response(404)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://slskd.test")
    service = SlskdService(config, client=client)

    assert await service.check_health()
    assert await service.ensure_openapi_verified()
    assert service.breaker.state is BreakerState.CLOSED
    await client.aclose()


@pytest.mark.asyncio
async def test_search_parses_responses_and_stops_on_complete(tmp_path: Path) -> None:
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v0/searches":
            return httpx.Response(201, json={"id": 7})
        if request.url.path == "/api/v0/searches/7":
            calls["count"] += 1
            return httpx.Response(
                200,
                json={
                    "id": 7,
                    "isComplete": True,
                    "responses": [
                        {
                            "user": "peer",
                            "speed": 1200,
                            "queueLength": 0,
                            "files": [
                                {
                                    "filename": "artist - song.flac",
                                    "size": 40000000,
                                    "duration": 240,
                                    "bitDepth": 24,
                                    "sampleRate": 96000,
                                }
                            ],
                        }
                    ],
                },
            )
        return httpx.Response(404)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://slskd.test")
    service = SlskdService(config, client=client)

    responses = await service.search(["artist - song"], timeout_s=10.0, poll_interval_s=0.0)

    assert len(responses) == 1
    assert responses[0].user == "peer"
    assert responses[0].files[0].bit_depth == 24
    await client.aclose()


@pytest.mark.asyncio
async def test_openapi_version_templates_normalize_and_pick_0_26_route(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v0/session":
            return httpx.Response(200, json={})
        if request.url.path == "/swagger/v0/swagger.json":
            # slskd 0.26 serves templated version segments and the new transfer route.
            return httpx.Response(
                200,
                json={
                    "paths": {
                        "/api/v{version}/searches": {},
                        "/api/v0/session": {},
                        "/api/v{version}/transfers/downloads": {},
                        "/api/v{version}/transfers/downloads/{username}": {},
                    }
                },
            )
        return httpx.Response(404)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://slskd.test")
    service = SlskdService(config, client=client)

    assert await service.check_health()
    assert await service.ensure_openapi_verified()
    assert service._download_route == "/api/v0/transfers/downloads/{username}"
    await client.aclose()


@pytest.mark.asyncio
async def test_openapi_version_templates_pick_legacy_users_route(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/swagger/v0/swagger.json":
            # A pre-0.26 daemon exposes the users/{username}/downloads route.
            return httpx.Response(
                200,
                json={
                    "paths": {
                        "/api/v0/searches": {},
                        "/api/v0/session": {},
                        "/api/v0/transfers/downloads": {},
                        "/api/v0/users/{username}/downloads/{id}": {},
                    }
                },
            )
        return httpx.Response(404)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://slskd.test")
    service = SlskdService(config, client=client)

    assert await service.ensure_openapi_verified()
    assert service._download_route == "/api/v0/users/{username}/downloads/{token}"
    await client.aclose()


@pytest.mark.asyncio
async def test_download_uses_legacy_object_body_for_legacy_route(tmp_path: Path) -> None:
    download_dir = tmp_path / "downloads"
    completed = download_dir / "peer" / "artist - song.flac"
    completed.parent.mkdir(parents=True)
    completed.write_bytes(b"fake flac bytes")
    posted: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/swagger/v0/swagger.json":
            return httpx.Response(
                200,
                json={"paths": {"/api/v0/users/{username}/downloads/{id}": {}}},
            )
        if request.method == "GET" and request.url.path == "/api/v0/session":
            return httpx.Response(200, json={})
        if request.method == "POST" and request.url.path == "/api/v0/users/peer/downloads/download":
            posted.append(json.loads(request.content))
            return httpx.Response(200, json={})
        if request.url.path == "/api/v0/transfers/downloads":
            return httpx.Response(
                200,
                json=[
                    {
                        "user": "peer",
                        "filename": "artist - song.flac",
                        "state": "Completed",
                        "bytesTransferred": 11,
                    }
                ],
            )
        return httpx.Response(404)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://slskd.test")
    service = SlskdService(config, client=client)
    candidate = P2PCandidate(username="peer", filename="artist - song.flac")

    result = await service.download(candidate, download_dir=download_dir)

    assert result == tmp_path / "downloads" / "peer" / "artist - song.flac"
    assert posted[0] == {"files": [{"filename": "artist - song.flac"}], "username": "peer"}
    await client.aclose()


@pytest.mark.asyncio
async def test_download_completes_and_locates_file(tmp_path: Path) -> None:
    download_dir = tmp_path / "downloads"
    completed = download_dir / "peer" / "artist - song.flac"
    completed.parent.mkdir(parents=True)
    completed.write_bytes(b"fake flac bytes")
    posted: list[dict] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/swagger/v0/swagger.json":
            return httpx.Response(
                200,
                json={"paths": {"/api/v{version}/transfers/downloads/{username}": {}}},
            )
        if request.method == "GET" and request.url.path == "/api/v0/session":
            return httpx.Response(200, json={})
        if request.method == "POST" and request.url.path == "/api/v0/transfers/downloads/peer":
            posted.append(json.loads(request.content))
            return httpx.Response(200, json={})
        if request.url.path == "/api/v0/transfers/downloads":
            return httpx.Response(
                200,
                json=[
                    {
                        "user": "peer",
                        "filename": "artist - song.flac",
                        "state": "Completed",
                        "bytesTransferred": 11,
                    }
                ],
            )
        return httpx.Response(404)

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://slskd.test")
    service = SlskdService(config, client=client)
    candidate = P2PCandidate(username="peer", filename="artist - song.flac")

    result = await service.download(candidate, download_dir=download_dir)

    assert result == tmp_path / "downloads" / "peer" / "artist - song.flac"
    assert result.read_bytes() == b"fake flac bytes"
    assert posted[0] == [{"filename": "artist - song.flac"}]
    await client.aclose()
