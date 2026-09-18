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
