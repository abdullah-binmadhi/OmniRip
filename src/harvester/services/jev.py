"""TypeSafe Jev advisory triage for P2P candidates.

Jev is a System One model: send it ``state`` and typed questions, get back
calibrated probabilities instead of generated text. It judges text only — it
never hears audio and never sees spectral data — so this module uses it exactly
where the deterministic scoring cannot look: what a filename *claims* to be
(a different song, a cover/karaoke version, a counterfeit or spam lure).

The weighted scoring in :mod:`harvester.analysis.scoring` (docs/06 §7-§8) stays
authoritative. Triage only re-buckets candidates Jev clearly judges wrong;
everything in the uncertain band keeps its deterministic order. The whole
feature is opt-in (``[jev] enabled``) and never fails a job: every error path
logs a warning and returns ``None`` so the hunt continues unchanged.

One batched request per search — two Nouls per candidate (match, counterfeit)
— mirroring the "parallel questions" design: independent judgments about the
same state belong in a single call.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx

from harvester.config import AppConfig
from harvester.models import P2PCandidate

__all__ = [
    "JEV_ENDPOINT",
    "CandidateTriage",
    "JevService",
    "TriageBucket",
]

JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"

# Policy bands for Jev's nouls. A noul near 0.5 means "unsure", not medium, so
# the band between the two lines is deliberately wide. These are application
# policy, not model behaviour: tune them with real search data.
_KEEP_MIN = 0.70
_DEMOTE_MAX = 0.30
_COUNTERFEIT_MIN = 0.70
_COUNTERFEIT_MAX = 0.30


class TriageBucket(StrEnum):
    """Advisory placement for one candidate; order is keep < unsure < demote."""

    KEEP = "keep"
    UNSURE = "unsure"
    DEMOTE = "demote"


@dataclass(frozen=True, slots=True)
class CandidateTriage:
    """Jev's two nouls for one candidate, classified into a policy bucket."""

    bucket: TriageBucket
    match: float | None = None
    counterfeit: float | None = None


class JevService:
    """Batched Jev triage over the top search candidates; failures are silent."""

    def __init__(
        self,
        config: AppConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._client = client
        self.logger = logging.getLogger("harvester.services.jev")

    @property
    def api_key(self) -> str:
        return os.environ.get(self.config.jev.api_key_env, "").strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def available(self) -> bool:
        return self.config.jev.enabled and self.configured

    async def triage_candidates(
        self,
        target: str,
        candidates: Sequence[P2PCandidate],
    ) -> list[CandidateTriage] | None:
        """Judge the shortlist; return one result per candidate, or None.

        Only the first ``jev.max_candidates`` are sent (two questions each, one
        request). ``None`` means "no advisory layer for this search".
        """

        if not self.available or not candidates:
            return None
        shortlist = list(candidates[: max(1, self.config.jev.max_candidates)])
        state = _build_state(target, shortlist)
        questions = _build_questions(len(shortlist))
        answers = await self._request(state, questions)
        if answers is None:
            return None
        results = [classify(answers, index) for index in range(len(shortlist))]
        demoted = sum(1 for result in results if result.bucket is TriageBucket.DEMOTE)
        unsure = sum(1 for result in results if result.bucket is TriageBucket.UNSURE)
        self.logger.info(
            "Jev triage: %d candidate(s), %d demoted, %d unsure",
            len(results),
            demoted,
            unsure,
        )
        return results

    async def _request(
        self,
        state: Mapping[str, Any],
        questions: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        client = await self._get_client()
        body = {
            "state": state,
            "model": self.config.jev.model,
            "questions": questions,
        }
        try:
            response = await client.post(
                JEV_ENDPOINT,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("Jev triage request failed: %s", exc)
            return None
        if not isinstance(payload, Mapping):
            return None
        answers = payload.get("answers")
        if not isinstance(answers, Mapping):
            self.logger.warning("Jev response carried no answers map")
            return None
        return answers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeouts.jev_s),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def classify(answers: Mapping[str, Any], index: int) -> CandidateTriage:
    """Map one candidate's noul answers to a bucket using the policy bands."""

    match = _noul(answers, f"match_{index}")
    counterfeit = _noul(answers, f"counterfeit_{index}")
    if counterfeit is not None and counterfeit >= _COUNTERFEIT_MIN:
        return CandidateTriage(TriageBucket.DEMOTE, match, counterfeit)
    if match is not None and match <= _DEMOTE_MAX:
        return CandidateTriage(TriageBucket.DEMOTE, match, counterfeit)
    if (
        match is not None
        and match >= _KEEP_MIN
        and (counterfeit is None or counterfeit <= _COUNTERFEIT_MAX)
    ):
        return CandidateTriage(TriageBucket.KEEP, match, counterfeit)
    return CandidateTriage(TriageBucket.UNSURE, match, counterfeit)


def _noul(answers: Mapping[str, Any], key: str) -> float | None:
    answer = answers.get(key)
    if not isinstance(answer, Mapping):
        return None
    value = answer.get("noul")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _build_state(target: str, candidates: Sequence[P2PCandidate]) -> dict[str, Any]:
    return {
        "target": target,
        "candidates": [
            {
                "index": index,
                "filename": candidate.filename,
                "username": candidate.username,
                "bit_depth": candidate.bit_depth,
                "sample_rate": candidate.sample_rate,
                "duration_s": candidate.duration_s,
            }
            for index, candidate in enumerate(candidates)
        ],
    }


def _build_questions(count: int) -> dict[str, Any]:
    questions: dict[str, Any] = {}
    for index in range(count):
        questions[f"match_{index}"] = {
            "type": "noul",
            "instructions": (
                f"Does `candidates[{index}].filename` name the same artist and song as "
                "`target` — a plausible release of that recording — rather than a "
                "different song, a cover/karaoke/instrumental version, or a non-music "
                "file?"
            ),
            "criteria": {
                "true": "The filename identifies the requested artist and song",
                "false": "A different song, a version substitute, or not music",
            },
        }
        questions[f"counterfeit_{index}"] = {
            "type": "noul",
            "instructions": (
                f"Does `candidates[{index}].filename` advertise itself like a counterfeit "
                "or spam upload — fake lossless or bitrate claims, download-site tags, "
                "bait keywords — rather than an ordinary music release?"
            ),
            "criteria": {
                "true": "Counterfeit or spam markers in the filename",
                "false": "An ordinary release filename",
            },
        }
    return questions
