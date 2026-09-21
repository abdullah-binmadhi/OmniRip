"""Tests for the hosted MVSEP client (docs/13 D26) — no network, no key."""

from pathlib import Path

import httpx
import pytest

from harvester.processing import HOSTED_RAW_TOKEN
from harvester.services.mvsep import (
    DEFAULT_SEP_TYPE,
    SEP_TYPES,
    MvsepClient,
    lane_key_for_token,
)

_KEY = "test-key-1234567890"


def _client(handler, key: str | None = _KEY) -> tuple[MvsepClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://mvsep.com/api"
    )
    return MvsepClient(api_key=key, client=http, poll_interval_s=0.01), http


def _job_handler(*, statuses: list[str], files: list[dict[str, str]], algorithm: str = "MVSep"):
    calls = {"poll": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/separation/create"):
            return httpx.Response(200, json={"success": True, "data": {"hash": "job-1"}})
        if request.url.path.endswith("/separation/get"):
            index = min(calls["poll"], len(statuses) - 1)
            calls["poll"] += 1
            status = statuses[index]
            if status == "done":
                return httpx.Response(
                    200,
                    json={
                        "success": True,
                        "status": "done",
                        "data": {"algorithm": algorithm, "files": files},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "status": status,
                    "data": {"current_order": 3, "eta_seconds": 7},
                },
            )
        if request.url.path.startswith("/files/"):
            return httpx.Response(200, content=b"RIFFfake")
        return httpx.Response(404)

    return handler


def test_lane_key_mapping() -> None:
    assert lane_key_for_token("vocals-lead") == "lead_vocals"
    assert lane_key_for_token("vocals-back") == "back_vocals"
    assert lane_key_for_token("digital-piano") == "digital_piano"
    # Sums of other stems are downloaded but never rendered as lanes.
    assert lane_key_for_token("instrum-only") is None
    assert lane_key_for_token("back-instrum") is None
    # Unknown tokens become their own lane (53-stem models ship new names).
    assert lane_key_for_token("pedal-steel-guitar") == "pedal_steel_guitar"
    assert lane_key_for_token("") is None


@pytest.mark.asyncio
async def test_sep_type_resolution() -> None:
    client = MvsepClient(api_key=_KEY)
    try:
        assert await client.sep_type_for("karaoke_lead_back") == SEP_TYPES["karaoke_lead_back"]
        assert await client.sep_type_for("126") == 126
        assert await client.sep_type_for("") == SEP_TYPES[DEFAULT_SEP_TYPE]
    finally:
        await client.close()


def test_available_requires_a_key() -> None:
    assert MvsepClient(api_key="").available is False
    assert MvsepClient(api_key="abc").available is True


@pytest.mark.asyncio
async def test_separate_without_key_raises() -> None:
    client = MvsepClient(api_key="")
    with pytest.raises(RuntimeError, match="MVSEP_API_KEY"):
        await client.separate(Path("x.mp3"), Path("."), output_prefix="x_ensemble")


@pytest.mark.asyncio
async def test_separate_downloads_lane_stems_and_skips_sums(tmp_path: Path) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3fake")
    stem_dir = tmp_path / "stems"
    files = [
        {
            "download_filename": "job_mt_6_vocals-lead.wav",
            "url": "https://mvsep.com/files/lead.wav",
        },
        {
            "download_filename": "job_mt_6_vocals-back.wav",
            "url": "https://mvsep.com/files/back.wav",
        },
        {
            "download_filename": "job_mt_6_instrum-only.wav",
            "url": "https://mvsep.com/files/inst.wav",
        },
    ]
    client, http = _client(
        _job_handler(statuses=["waiting", "processing", "done"], files=files)
    )
    progress: list[tuple[float, str]] = []
    try:
        result = await client.separate(
            source,
            stem_dir,
            output_prefix="song_ensemble",
            sep_type="karaoke_lead_back",
            progress=lambda pct, step: progress.append((pct, step)),
        )
    finally:
        await client.close()
        await http.aclose()

    assert result.sep_type == SEP_TYPES["karaoke_lead_back"]
    assert result.algorithm == "MVSep"
    assert result.lane_keys == ("lead_vocals", "back_vocals")
    assert result.skipped == ("instrum-only",)
    lead = stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}lead_vocals.wav"
    back = stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}back_vocals.wav"
    assert lead.read_bytes() == b"RIFFfake"
    assert back.is_file()
    assert not (stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}instrum_only.wav").exists()
    assert "Hosted" in result.describe() and "LEAD VOCALS" in result.describe()
    assert progress and any("queue" in step for _, step in progress)


@pytest.mark.asyncio
async def test_failed_job_reports_status_without_raising(tmp_path: Path) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3fake")

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/separation/create"):
            return httpx.Response(200, json={"success": True, "data": {"hash": "job-2"}})
        return httpx.Response(
            200,
            json={
                "success": True,
                "status": "error",
                "data": {"message": "model unavailable"},
            },
        )

    client, http = _client(handler)
    try:
        result = await client.separate(source, tmp_path, output_prefix="song_ensemble")
    finally:
        await client.close()
        await http.aclose()
    assert result.stems == ()
    assert "error" in result.message and "model unavailable" in result.message


@pytest.mark.asyncio
async def test_invalid_key_error_never_echoes_the_key(tmp_path: Path) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3fake")

    async def handler(request: httpx.Request) -> httpx.Response:
        # A hostile server that echoes the token back in the error body.
        return httpx.Response(400, text=f"invalid api_token {_KEY}")

    client, http = _client(handler)
    try:
        with pytest.raises(RuntimeError) as excinfo:
            await client.separate(source, tmp_path, output_prefix="song_ensemble")
    finally:
        await client.close()
        await http.aclose()
    assert _KEY not in str(excinfo.value)
    assert "400" in str(excinfo.value)


@pytest.mark.asyncio
async def test_account_check_rejects_bad_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"success": False, "errors": ["invalid token"]})

    client, http = _client(handler)
    try:
        with pytest.raises(RuntimeError, match="rejected the API key"):
            await client.account()
    finally:
        await client.close()
        await http.aclose()
