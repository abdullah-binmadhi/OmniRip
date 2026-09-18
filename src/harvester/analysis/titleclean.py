"""Deterministic query construction for the P2P hunt.

Implements docs/03 Phase 2.1: NFKD normalization, diacritic folding, noise-token
stripping, and the ordered multi-query strategy (feat kept -> stripped -> title-only).
"""

from __future__ import annotations

import re
import unicodedata

_ELLIPSIS = "[...]"
_BRACKET_NOISE = re.compile(r"\[[^\]]{0,40}\]")
_PARENTHETICAL_NOISE = re.compile(r"\(([^()]{0,60})\)")
_NOISE_TOKENS = (
    "official video",
    "official audio",
    "official music video",
    "lyric video",
    "lyrics",
    "audio",
    "hd",
    "hq",
    "4k",
    "mv",
    "video",
    "remaster",
    "remastered",
    "explicit",
    "mono",
    "stereo",
    "digital",
    "edit",
    "single",
)

_LEADING_TRACK = re.compile(r"^\s*(?:\(?\d{1,3}\)?[.\s-]*|\d{1,3}[\s.-]+)")
_WHITESPACE = re.compile(r"\s+")
_TRAILING_PUNCTUATION = re.compile(r"[\s\-–—:;,./\\\"']+$")
_LEADING_PUNCTUATION = re.compile(r"^[\s\-–—:;,./\\\"']+")
_FEAT_RE = re.compile(r"\((?:feat|ft|featuring|with)[.\s]+[^()]*\)", re.IGNORECASE)


def fold_unicode(text: str) -> str:
    """NFKD-normalize and fold diacritics to ASCII while keeping the case."""

    normalized = unicodedata.normalize("NFKD", text)
    folded = "".join(character for character in normalized if not unicodedata.combining(character))
    return folded


def _strip_noise(text: str, *, strip_feat: bool) -> str:
    text = _BRACKET_NOISE.sub(" ", text)
    text = _PARENTHETICAL_NOISE.sub(_ellipsis_if_noise, text)
    if strip_feat:
        text = _FEAT_RE.sub(" ", text)
    for token in _NOISE_TOKENS:
        text = re.sub(rf"\b{re.escape(token)}\b", " ", text, flags=re.IGNORECASE)
    return text


def _ellipsis_if_noise(match: re.Match[str]) -> str:
    inner = match.group(1).strip().lower()
    if not inner:
        return " "
    if any(token in inner for token in _NOISE_TOKENS) or inner in _NOISE_TOKENS:
        return " "
    if re.fullmatch(r"[0-9]{4}", inner.strip()):
        return " "
    return match.group(0)


def _normalize(text: str) -> str:
    text = fold_unicode(text)
    text = _strip_noise(text, strip_feat=False)
    text = _LEADING_TRACK.sub("", text)
    text = _LEADING_PUNCTUATION.sub("", text)
    text = _TRAILING_PUNCTUATION.sub("", text)
    return _WHITESPACE.sub(" ", text).strip()


def clean_title(title: str) -> str:
    """Return the canonical cleaned title for display and queries."""

    return _normalize(title)


def build_queries(artist: str, title: str) -> tuple[str, ...]:
    """Return the ordered multi-query strategy: feat kept, feat stripped, title only."""

    if not title and not artist:
        return ()
    artist_cleaned = _normalize(artist) if artist else ""
    title_cleaned = _normalize(title) if title else ""

    queries: list[str] = []
    if artist_cleaned and title_cleaned:
        candidate = f"{artist_cleaned} - {title_cleaned}"
        if candidate not in queries:
            queries.append(candidate)
    if title_cleaned:
        stripped = _WHITESPACE.sub(" ", _strip_noise(title_cleaned, strip_feat=True)).strip()
        if artist_cleaned and stripped:
            candidate = f"{artist_cleaned} {stripped}"
            if candidate not in queries:
                queries.append(candidate)
        if stripped and stripped != title_cleaned:
            if len(queries) < 3 and stripped not in queries:
                queries.append(stripped)
        elif title_cleaned and len(queries) < 3 and title_cleaned not in queries:
            queries.append(title_cleaned)
    return tuple(queries[:3])


__all__ = ["build_queries", "clean_title", "fold_unicode"]
