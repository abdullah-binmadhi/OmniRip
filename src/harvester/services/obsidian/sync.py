"""CLI-facing orchestration for the Obsidian bridge (docs/15).

``ObsidianSync`` is the single entry point for ``OmniRip obsidian-sync`` and the
natural place for future auto-export hooks. Every operation is best-effort: callers
wrap the whole run so a broken vault never blocks ripping.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from harvester.config import ObsidianConfig
from harvester.models import State
from harvester.services.obsidian.frontmatter import encode_frontmatter
from harvester.services.obsidian.library import export_library as _export_library
from harvester.services.obsidian.sessions import export_sessions as _export_sessions
from harvester.services.obsidian.studio import export_studio as _export_studio
from harvester.services.obsidian.vault import OMNIRIP_NOTE_TYPE, VaultPaths, write_note
from harvester.services.obsidian.wants import WantNote, list_wants, queueable, settle_note

logger = logging.getLogger("harvester.obsidian")

SubmitCallback = Callable[[str], Awaitable[Any]]


class ObsidianSync:
    """Tiny facade over the vault submodules, bound to one config."""

    def __init__(self, config: ObsidianConfig, *, logger_: logging.Logger | None = None) -> None:
        self.config = config
        self.vault = VaultPaths.from_config(config)
        self.log = logger_ or logger

    def ensure(self) -> VaultPaths:
        return self.vault.ensure()

    def export_library(self, rows: Iterable[Mapping[str, Any]]) -> list[Path]:
        return _export_library(self.vault, rows)

    def export_sessions(self, reports: Iterable[Path]) -> list[Path]:
        return _export_sessions(self.vault, reports)

    def export_studio(self) -> list[Path]:
        return _export_studio(self.vault)

    def write_hub(self) -> Path:
        write_note(self.vault.hub, _hub_note())
        return self.vault.hub

    def wants(self) -> list[WantNote]:
        return list_wants(self.vault)

    async def import_wants(
        self,
        submit: SubmitCallback,
        *,
        retry_failed: bool = False,
    ) -> dict[Path, Any]:
        """Submit every queueable wants note; returns ``{note_path: job}``.

        ``submit(query)`` is awaited per note (the CLI wraps ``submit_url`` so a
        bare title becomes a ``ytsearch1:`` query). Notes are flipped to ``queued``
        as they are handed off; :meth:`settle_wants` reconciles the terminal states
        once the pipeline has run them.
        """
        notes = queueable(self.wants(), retry_failed=retry_failed)
        if not notes:
            return {}
        self.log.info("obsidian: queueing %d want note(s) from the vault", len(notes))
        pending: dict[Path, Any] = {}
        for note in notes:
            job = await submit(note.query)
            pending[note.path] = job
            job_id = str(getattr(job, "id", "?"))
            settle_note(note.path, "queued", f"{_timestamp()} queued (job {job_id})")
        return pending

    def settle_wants(self, pending: Mapping[Path, Any]) -> dict[Path, str]:
        """Record terminal job states on their wants notes; returns ``{path: status}``."""
        results: dict[Path, str] = {}
        for path, job in pending.items():
            state = getattr(job, "state", None)
            if state is State.COMPLETED:
                output = str(getattr(job, "output_path", None) or job.display_name)
                spectral = getattr(job, "spectral", None)
                extra = []
                if spectral is not None:
                    verdict_val = getattr(spectral.verdict, "value", str(spectral.verdict))
                    cutoff_val = getattr(spectral, "cutoff_hz", None)
                    if cutoff_val:
                        extra.append(f"spectral {verdict_val} @ {cutoff_val:.0f}Hz")
                    else:
                        extra.append(f"spectral {verdict_val}")
                detail_str = f" ({', '.join(extra)})" if extra else ""
                settle_note(path, "done", f"{_timestamp()} done -> {output}{detail_str}")
                results[path] = "done"
            elif state is State.FAILED:
                error = job.error.message if getattr(job, "error", None) else "unknown"
                settle_note(path, "failed", f"{_timestamp()} failed: {error}")
                results[path] = "failed"
            elif state is State.CANCELLED:
                settle_note(path, "failed", f"{_timestamp()} cancelled")
                results[path] = "failed"
        return results


def _hub_note() -> str:
    from harvester.analysis.enhancement.presets import PRESETS as ENHANCEMENT_PRESETS
    from harvester.services.obsidian.naming import studio_note_name

    frontmatter = {
        "omnirip": OMNIRIP_NOTE_TYPE,
        "type": "hub",
        "tags": ["omnirip"],
    }
    studio_links = "".join(
        f"- [[presets/{studio_note_name(preset_id)}]]\n" for preset_id, _ in ENHANCEMENT_PRESETS.items()
    )
    body = (
        "# OmniRip — Second Brain\n\n"
        "This vault is maintained by OmniRip (`OmniRip obsidian-sync`, docs/15). It "
        "mirrors ripping activity into readable notes and doubles as the rip wishlist.\n\n"
        "## Layout\n"
        "- `Library/` — the database: one note per album, YAML frontmatter + per-track table\n"
        "- `Sessions/` — one note per batch run (stats + track log)\n"
        "- `Wants/` — your rip queue; set `status: want` to queue, OmniRip flips it to "
        "`queued`/`done`/`failed`\n"
        "- `Studio/` — enhancement & processing presets as notes\n"
        "- `Journal/` — your space; OmniRip never reads or writes it\n\n"
        "## Quick start\n"
        "1. Add a note under `Wants/` with `status: want` and a `# Artist — Title` heading.\n"
        "2. Run `OmniRip obsidian-sync`. It rips every `want` (via yt-dlp/fallback), exports "
        "`Library/`, `Sessions/` and `Studio/`, and rewrites this hub.\n"
        "3. Browse `Library/` for the database. Obsidian's native search already pivots on the "
        "frontmatter; the Dataview plugin unlocks richer queries.\n\n"
        "## Studio presets\n" + studio_links
    )
    return encode_frontmatter(frontmatter) + body


def _timestamp() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["ObsidianSync"]