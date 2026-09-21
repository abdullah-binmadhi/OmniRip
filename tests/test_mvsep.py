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
async def test_new_hosted_run_replaces_previous_run_atomically(tmp_path: Path) -> None:
    """A fresh run must not leave old-model stems mixed with new ones."""
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3fake")
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    stale = stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}old_lane.wav"
    stale.write_bytes(b"OLDRUN")

    files = [
        {
            "download_filename": "job_mt_6_vocals-lead.wav",
            "url": "https://mvsep.com/files/lead.wav",
        },
    ]
    client, http = _client(_job_handler(statuses=["done"], files=files))
    try:
        result = await client.separate(
            source, stem_dir, output_prefix="song_ensemble", sep_type="karaoke_lead_back"
        )
    finally:
        await client.close()
        await http.aclose()

    assert result.lane_keys == ("lead_vocals",)
    new = stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}lead_vocals.wav"
    assert new.read_bytes() == b"RIFFfake"
    assert not stale.exists()  # old run replaced, not mixed in
    assert list(stem_dir.glob("*.old-*")) == []  # backups cleaned up


@pytest.mark.asyncio
async def test_failed_hosted_run_keeps_previous_results(tmp_path: Path) -> None:
    """A job that never reaches done must leave the old hosted stems intact."""
    source = tmp_path / "song.mp3"
    source.write_bytes(b"ID3fake")
    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    stale = stem_dir / f"song_ensemble{HOSTED_RAW_TOKEN}lead_vocals.wav"
    stale.write_bytes(b"OLDRUN")

    client, http = _client(_job_handler(statuses=["error"], files=[]))
    try:
        result = await client.separate(
            source, stem_dir, output_prefix="song_ensemble", sep_type="karaoke_lead_back"
        )
    finally:
        await client.close()
        await http.aclose()

    assert result.stems == ()
    assert stale.read_bytes() == b"OLDRUN"


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


def test_swap_hosted_run_mid_backup_failure_restores_old_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure while moving the old set aside must not split it across names."""
    from harvester.services.mvsep import _swap_hosted_run

    stem_dir = tmp_path / "stems"
    stem_dir.mkdir()
    old_a = stem_dir / "song_ensemble_hosted_raw_vocals.wav"
    old_b = stem_dir / "song_ensemble_hosted_raw_drums.wav"
    old_a.write_bytes(b"OLD-A")
    old_b.write_bytes(b"OLD-B")
    staged = [(tmp_path / "n1.wav", stem_dir / "song_ensemble_hosted_raw_new.wav")]
    (tmp_path / "n1.wav").write_bytes(b"NEW")

    real_replace = __import__("os").replace
    calls = 0

    def flaky_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 2:  # second old stem's backup move fails
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr("harvester.services.mvsep.os.replace", flaky_replace)

    with pytest.raises(OSError, match="disk full"):
        _swap_hosted_run(stem_dir, "song_ensemble", staged, "job-12345678")

    # Both old stems back under their original names; no backups left behind.
    assert old_a.read_bytes() == b"OLD-A"
    assert old_b.read_bytes() == b"OLD-B"
    assert list(stem_dir.glob("*.old-*")) == []
