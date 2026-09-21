"""A minimal, deterministic YAML frontmatter codec for Obsidian notes.

Deliberately stdlib-only (ladder rung 3): we only need the subset Obsidian shows
in its properties table — flat scalars plus inline lists of scalars — and we must
round-trip exactly what we write so notes stay idempotent across syncs.
The reader is tolerant of hand-written frontmatter so users may edit notes freely.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_BOUNDARY = "---"
_SCALAR_KINDS = (str, int, float, bool)

_NULLS = {"", "null", "~", "none", "None", "Null"}
_TRUES = {"true", "True", "TRUE", "yes", "Yes"}
_FALSES = {"false", "False", "FALSE", "no", "No"}


def _needs_quoting(value: str) -> bool:
    """A value must be single-quoted when a plain write would not round-trip."""
    if not value:
        return True
    if value.strip() != value:
        return True
    if value in _NULLS | _TRUES | _FALSES:
        return True
    if value.startswith(("-", "[", "{", "'", '"')):
        return True
    if any(ch in value for ch in ": #[]{}\n"):
        return True
    try:
        int(value)
        return True
    except ValueError:
        return False


def _encode_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    text = str(value)
    if _needs_quoting(text):
        return "'" + text.replace("'", "''") + "'"
    return text


def _encode_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, Mapping):
        inner = ", ".join(f"{key}: {_encode_scalar(item)}" for key, item in value.items())
        return "{" + inner + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_encode_scalar(item) for item in value) + "]"
    if not isinstance(value, _SCALAR_KINDS):
        raise TypeError(f"unsupported frontmatter value: {value!r}")
    return _encode_scalar(value)


def encode_frontmatter(data: Mapping[str, Any]) -> str:
    """Render ``data`` as an Obsidian frontmatter block including the ``---`` delimiters."""
    lines = [_BOUNDARY]
    for key, value in data.items():
        lines.append(f"{key}: {_encode_value(value)}")
    lines.append(_BOUNDARY)
    return "\n".join(lines) + "\n"


def _strip_inline_comment(line: str) -> str:
    quote: str | None = None
    for index, char in enumerate(line):
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            continue
        if char == "#" and (index == 0 or line[index - 1] in " \t"):
            return line[:index].rstrip()
    return line


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("''", "'")
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text in _NULLS:
        return None
    if text in _TRUES:
        return True
    if text in _FALSES:
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _split_top_level(text: str, separator: str) -> list[str]:
    """Split on ``separator`` at the top level, honoring single/double-quoted blocks."""
    parts: list[str] = []
    current = ""
    quote: str | None = None
    for char in text:
        if quote:
            current += char
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            current += char
        elif char == separator:
            parts.append(current)
            current = ""
        else:
            current += char
    tail = current.strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_list(raw: str) -> list[Any]:
    inner = raw[1 : raw.rindex("]")] if "]" in raw else raw[1:]
    return [_parse_scalar(_strip_inline_comment(part)) for part in _split_top_level(inner, ",")]


def _parse_map(raw: str) -> dict[str, Any]:
    inner = raw[1 : raw.rindex("}")] if "}" in raw else raw[1:]
    result: dict[str, Any] = {}
    for part in _split_top_level(inner, ","):
        key, sep, value = part.partition(":")
        if not sep:
            continue
        result[key.strip()] = _parse_scalar(_strip_inline_comment(value))
    return result


def parse_value(raw: str) -> Any:
    """Parse one frontmatter value line ``raw`` (already stripped of its key)."""
    text = raw.strip()
    if text.startswith("["):
        return _parse_list(text)
    if text.startswith("{"):
        return _parse_map(text)
    return _parse_scalar(_strip_inline_comment(text))


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split ``text`` into (frontmatter dict, body).

    Only a leading ``---``-delimited block counts; anything else is treated as body
    with an empty frontmatter dict. Values are parsed leniently so hand-written notes
    behave predictably. The body is preserved verbatim (including trailing newlines).
    """
    if not text.startswith(_BOUNDARY):
        return {}, text
    lines = text.split("\n")
    body_start = None
    for index in range(1, len(lines)):
        if lines[index].strip() == _BOUNDARY:
            body_start = index + 1
            break
    if body_start is None:
        return {}, text
    data: dict[str, Any] = {}
    for line in lines[1 : body_start - 1]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition(":")
        if not sep or not key.strip():
            continue
        data[key.strip()] = parse_value(value)
    body = "\n".join(lines[body_start:])
    return data, body


def text_with_frontmatter(data: Mapping[str, Any], body: str) -> str:
    """Reassemble a note from frontmatter data and body text."""
    encoded = encode_frontmatter(data)
    return encoded + body if not body.startswith("\n") else encoded + body.lstrip("\n")


def set_status(text: str, status: str) -> str:
    """Return ``text`` with ``status`` added or replaced in the frontmatter.

    If the note has a leading frontmatter block, the ``status`` key is updated in
    place (preserving the user's other properties). Otherwise a fresh frontmatter
    block is prepended — the body is never edited.
    """
    data, body = parse_frontmatter(text)
    data["status"] = status
    return text_with_frontmatter(data, body)


__all__ = [
    "encode_frontmatter",
    "parse_frontmatter",
    "parse_value",
    "set_status",
    "text_with_frontmatter",
]