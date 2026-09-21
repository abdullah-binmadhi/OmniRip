"""Frontmatter codec tests: round-trip, tolerant parsing, status edits (docs/15)."""

from __future__ import annotations

import pytest

from harvester.services.obsidian.frontmatter import (
    encode_frontmatter,
    parse_frontmatter,
    parse_value,
    set_status,
)


def test_roundtrip_scalars_and_collections() -> None:
    data = {
        "omnirip": "omnirip",
        "title": "Chandelier",
        "artist": "Sia",
        "tracks": 2,
        "cutoff_hz": 21000.0,
        "identity_shift": False,
        "note": None,
        "tags": ["omnirip", "library"],
        "statuses": {"upgraded": 1, "failed": 2},
    }
    parsed, body = parse_frontmatter(encode_frontmatter(data))

    assert body == ""
    assert parsed == data


def test_values_needing_quoting_roundtrip() -> None:
    for value in ("", "true", "yes", "12", "has:colon", "has # hash", "- leading", " spaced "):
        parsed, _ = parse_frontmatter(encode_frontmatter({"key": value}))
        assert parsed["key"] == value, value


def test_string_with_colon_and_hash_is_quoted() -> None:
    text = encode_frontmatter({"title": "Note: feat. #2"})
    assert "'Note: feat. #2'" in text


def test_leading_boundary_is_required() -> None:
    parsed, body = parse_frontmatter("# just a note\n\ntext")
    assert parsed == {}
    assert body.startswith("# just a note")


def test_parse_value_types() -> None:
    assert parse_value(" 12 ") == 12
    assert parse_value("12.5") == 12.5
    assert parse_value("true") is True
    assert parse_value("false") is False
    assert parse_value("null") is None
    assert parse_value("'quoted value'") == "quoted value"
    assert parse_value("plain") == "plain"
    assert parse_value("[a, b, 2]") == ["a", "b", 2]


def test_parse_skips_comments_and_blank_lines() -> None:
    text = "---\n# a comment\n\ntitle: Song\nvalue: 3 # trailing\n---\nbody"
    parsed, body = parse_frontmatter(text)

    assert parsed == {"title": "Song", "value": 3}
    assert body == "body"


def test_set_status_preserves_existing_frontmatter() -> None:
    text = "---\ntitle: Song\nstatus: want\n---\n# Song\n"
    updated = set_status(text, "done")

    parsed, body = parse_frontmatter(updated)
    assert parsed["title"] == "Song"
    assert parsed["status"] == "done"
    assert body == "# Song\n"


def test_set_status_adds_frontmatter_when_absent_and_keeps_body() -> None:
    updated = set_status("# Song\n\nnotes\n", "queued")

    parsed, body = parse_frontmatter(updated)
    assert parsed == {"status": "queued"}
    assert body.startswith("# Song")


def test_unsupported_values_are_rejected() -> None:
    with pytest.raises(TypeError, match="unsupported frontmatter value"):
        encode_frontmatter({"key": object()})