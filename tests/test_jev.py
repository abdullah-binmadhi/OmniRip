from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from harvester.config import load_config
from harvester.models import Mode, P2PCandidate, TrackJob
from harvester.pipeline.orchestrator import PipelineOrchestrator
from harvester.pipeline.phase2_hunt import apply_jev_triage
from harvester.services.jev import JEV_ENDPOINT, JevService, TriageBucket, classify
from harvester.util.errors import ConfigError


def _config(tmp_path: Path, **overrides: object):
    merged: dict[str, object] = {"jev.enabled": True}
    merged.update(overrides)
    return load_config(
        environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
        cli_overrides=merged,
    )


def _candidate(index: int, **kwargs: object) -> P2PCandidate:
    defaults: dict[str, object] = {
        "username": f"peer{index}",
        "filename": f"Artist - Song {index}.flac",
        "size_bytes": 26_000_000,
        "duration_s": 240.0,
        "bit_depth": 16,
        "sample_rate": 44_100,
        "queue_length": 0,
        "user_speed_kbps": 1000,
    }
    defaults.update(kwargs)
    return P2PCandidate(**defaults)  # type: ignore[arg-type]


def _nouls(values: dict[str, float | None]) -> dict[str, object]:
    answers: dict[str, object] = {}
    for key, value in values.items():
        answers[key] = {"type": "noul", "noul": value}
    return answers


@pytest.mark.asyncio
async def test_triage_is_silent_when_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"answers": {}})

    config = _config(tmp_path, **{"jev.enabled": False})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = JevService(config, client=client)

    result = await service.triage_candidates("Artist - Song", [_candidate(0), _candidate(1)])

    assert result is None
    assert calls == []
    await client.aclose()


@pytest.mark.asyncio
async def test_triage_is_silent_without_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"answers": {}})

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = JevService(config, client=client)

    assert service.available is False
    result = await service.triage_candidates("Artist - Song", [_candidate(0)])  # type: ignore[arg-type]

    assert result is None
    assert calls == []
    await client.aclose()


@pytest.mark.asyncio
async def test_triage_batches_one_request_and_classifies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": _nouls(
                    {
                        "match_0": 0.95,
                        "counterfeit_0": 0.05,
                        "match_1": 0.90,
                        "counterfeit_1": 0.85,
                        "match_2": 0.50,
                        "counterfeit_2": 0.40,
                    }
                ),
                "usage": {"input_tokens": 100, "output_tokens": 10},
            },
        )

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = JevService(config, client=client)
    candidates = [_candidate(index) for index in range(3)]

    triage = await service.triage_candidates("Artist - Song", candidates)

    assert triage is not None
    assert [result.bucket for result in triage] == [
        TriageBucket.KEEP,
        TriageBucket.DEMOTE,
        TriageBucket.UNSURE,
    ]
    assert triage[0].match == pytest.approx(0.95)
    assert triage[1].counterfeit == pytest.approx(0.85)

    assert len(requests) == 1
    request = requests[0]
    assert str(request.url).startswith(JEV_ENDPOINT)
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "jev-latest"
    assert body["state"]["target"] == "Artist - Song"
    assert [entry["index"] for entry in body["state"]["candidates"]] == [0, 1, 2]
    assert body["state"]["candidates"][0]["filename"] == candidates[0].filename
    assert sorted(body["questions"]) == sorted(
        [f"{axis}_{index}" for index in range(3) for axis in ("match", "counterfeit")]
    )
    await client.aclose()


@pytest.mark.asyncio
async def test_triage_shortlist_keeps_only_max_candidates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "answers": _nouls(
                    {"match_0": 0.95, "counterfeit_0": 0.05, "match_1": 0.95, "counterfeit_1": 0.05}
                )
            },
        )

    config = _config(tmp_path, **{"jev.max_candidates": 2})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = JevService(config, client=client)

    triage = await service.triage_candidates(
        "Artist - Song", [_candidate(index) for index in range(5)]
    )

    assert triage is not None
    assert len(triage) == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_triage_failure_never_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = JevService(config, client=client)

    assert await service.triage_candidates("Artist - Song", [_candidate(0)]) is None  # type: ignore[arg-type]
    await client.aclose()


@pytest.mark.asyncio
async def test_triage_malformed_payload_returns_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": "jev-1.13.0"})

    config = _config(tmp_path)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = JevService(config, client=client)

    assert await service.triage_candidates("Artist - Song", [_candidate(0)]) is None  # type: ignore[arg-type]
    await client.aclose()


def test_classify_bands_abstain_on_uncertainty() -> None:
    """Noul near 0.5 is unsure; only clear verdicts move a candidate."""
    unsure = classify(_nouls({"match_0": 0.55, "counterfeit_0": 0.45}), 0)
    assert unsure.bucket is TriageBucket.UNSURE
    missing = classify({}, 0)
    assert missing.bucket is TriageBucket.UNSURE and missing.match is None
    contradictory = classify(_nouls({"match_0": 0.95, "counterfeit_0": 0.80}), 0)
    assert contradictory.bucket is TriageBucket.DEMOTE
    mismatch = classify(_nouls({"match_0": 0.10, "counterfeit_0": None}), 0)
    assert mismatch.bucket is TriageBucket.DEMOTE


def test_apply_triage_preserves_deterministic_order_within_buckets() -> None:
    candidates = [_candidate(index) for index in range(4)]
    triage = [
        classify(_nouls({"match_0": 0.10, "counterfeit_0": 0.05}), 0),
        classify(_nouls({"match_1": 0.95, "counterfeit_1": 0.05}), 1),
        classify(_nouls({"match_2": 0.50, "counterfeit_2": 0.40}), 2),
        classify(_nouls({"match_3": 0.95, "counterfeit_3": 0.05}), 3),
    ]

    ordered, summary = apply_jev_triage(candidates, triage)

    assert [candidate.username for candidate in ordered] == ["peer1", "peer3", "peer2", "peer0"]
    assert summary["considered"] == 4
    assert summary["demoted"] == ["Artist - Song 0.flac"]
    assert summary["reordered"] is True


def test_apply_triage_without_judgments_keeps_order() -> None:
    candidates = [_candidate(index) for index in range(3)]

    ordered, summary = apply_jev_triage(candidates, [])

    assert ordered == candidates
    assert summary == {"considered": 0, "demoted": [], "unsure": 3, "reordered": False}


def test_jev_config_defaults_and_validation(tmp_path: Path) -> None:
    defaults = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})

    assert defaults.jev.enabled is False
    assert defaults.jev.model == "jev-latest"
    assert defaults.jev.max_candidates == 8
    assert defaults.timeouts.jev_s == 15.0
    assert defaults.public_dict()["jev"]["api_key_env"] == "TYPESAFE_API_KEY"

    with pytest.raises(ConfigError, match="jev.api_key_env"):
        load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"jev.api_key_env": "not a var"},
        )
    with pytest.raises(ConfigError, match="jev.max_candidates"):
        load_config(
            environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")},
            cli_overrides={"jev.max_candidates": 0},
        )


class _FakeJev:
    """Minimal JevService stand-in for the orchestrator hook tests."""

    available = True

    def __init__(self, triage: list) -> None:
        self.triage = triage
        self.targets: list[str] = []

    async def triage_candidates(self, target: str, candidates) -> list:
        self.targets.append(target)
        return self.triage


@pytest.mark.asyncio
async def test_orchestrator_hook_reorders_and_records_summary(tmp_path: Path) -> None:
    config = _config(tmp_path)
    candidates = [_candidate(index) for index in range(2)]
    jev = _FakeJev(
        [
            classify(_nouls({"match_0": 0.10, "counterfeit_0": 0.05}), 0),
            classify(_nouls({"match_1": 0.95, "counterfeit_1": 0.05}), 1),
        ]
    )
    orchestrator = PipelineOrchestrator(config, jev=jev)  # type: ignore[arg-type]
    job = TrackJob(mode=Mode.SINGLE_URL, query_raw="Artist - Song")

    ordered = await orchestrator._triage_candidates(job, "Artist - Song", candidates)

    assert ordered == [candidates[1], candidates[0]]
    assert jev.targets == ["Artist - Song"]
    summary = job.probe_meta["jev_triage"]
    assert summary["reordered"] is True
    assert summary["demoted"] == [candidates[0].filename]


@pytest.mark.asyncio
async def test_orchestrator_hook_leaves_candidates_alone_when_disabled(tmp_path: Path) -> None:
    config = _config(tmp_path, **{"jev.enabled": False})
    orchestrator = PipelineOrchestrator(config)
    job = TrackJob(mode=Mode.SINGLE_URL, query_raw="Artist - Song")
    candidates = [_candidate(index) for index in range(2)]

    ordered = await orchestrator._triage_candidates(job, "Artist - Song", candidates)

    assert ordered == candidates
    assert "jev_triage" not in job.probe_meta
