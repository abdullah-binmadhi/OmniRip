# 15 — Obsidian Second-Brain Integration

Status: **merged** — two-way bridge between OmniRip and a local Obsidian vault
(live-verified against a real vault, §11).

## 1. Goal

Give the user their own knowledge graph around the workbench: Obsidian becomes the
database and second brain for everything OmniRip produces, and the vault doubles as
an inbound rip wishlist. All integration is **opt-in** (config) and **manual** (a single
CLI command); the pipeline itself never writes to the vault without being asked.

Two-way contract:

- **Outbound (OmniRip → vault):** batch-history exports as readable notes — album
  notes (`Library/`), per-run session notes (`Sessions/`), and preset inventories
  (`Studio/`).
- **Inbound (vault → OmniRip):** `Wants/` notes are turned into rip jobs; their
  `status` is reconciled to `queued` / `done` / `failed` as jobs run.

## 2. Design rules

1. **Plain vault on disk.** No plugin, no server, no network. Obsidian indexes the
   folder itself; OmniRip just reads/writes `.md` files and YAML frontmatter.
2. **No new dependencies.** Frontmatter is handled by a small stdlib-only codec
   (`frontmatter.py`); atomic writes reuse the existing `util.fsatomic`.
3. **Ownership is strict.** `Library/`, `Sessions/`, `Studio/` are OmniRip-owned and
   fully regenerated. `Wants/` is user-owned: OmniRip edits only the `status`
   frontmatter key and appends to the `## OmniRip` section. Everything else in the
   vault (e.g. `Journal/`) is never read or written.
4. **Never blocks ripping.** Every path is best-effort: the CLI wraps the run, and a
   broken vault can only fail the sync, never the pipeline.
5. **Path safety.** All note paths are resolved against the vault root
   (`naming.resolve_within`) — hostile metadata cannot escape the vault.

## 3. Vault layout

```
<vault_dir>                      # config [obsidian] vault_dir
├── OmniRip.md                   # hub / map of content
├── Library/<artist>/
│   └── <Artist> — <Album>.md    # the database: frontmatter + per-track table
├── Sessions/<root>-<utctime>.md # one note per Mode B report
├── Wants/**/*.md                # inbound rip queue (user-owned)
├── Studio/presets/<id>.md       # preset snapshots (enhancement + processing)
│   └── README.md                # preset inventory index
└── Journal/                     # user space — untouched
```

All notes carry `omnirip: omnirip` frontmatter plus a `type` (`album`, `session`,
`preset`, `hub`) and `tags: [omnirip, …]` so Obsidian's search (and optionally the
Dataview plugin) can pivot on them.

### 3.1 Album note

Built per `(artist, album)` from upgraded batch-report rows. Frontmatter includes
`title`, `artist`, `year`, `tracks`, plus per-track facts in the body table (status,
source kind, spectral verdict, cutoff, output path).

### 3.2 Session note

One per report file `reports/<root>-<utctime>.jsonl`. Frontmatter carries the
`statuses` and `verdicts` rollups as inline maps; the body has the rollup table and a
full track log.

### 3.3 Wants note (inbound)

User creates any `.md` under `Wants/` — optionally with frontmatter `title`/`artist`,
and a `status` value, plus a body heading or filename `Artist — Title`. OmniRip derives
a search query from (in order of priority): frontmatter `query` / `artist`+`title`, the
first `# Heading`, or the note filename. Statuses: `want` (default when missing) →
queued by `import_wants`, then `done` / `failed` on settle. `--retry-failed`
re-queues `failed` notes.

## 4. Config

```toml
[obsidian]
enabled = false                # opt-in
vault_dir = "~/OmniRip-Vault"
# library  = "Library"          # folder names are configurable
# sessions = "Sessions"
# studio   = "Studio"
# wants    = "Wants"
```

Defaults live in `_DEFAULTS`; `AppConfig.obsidian` exposes an `ObsidianConfig`
frozen dataclass. `config.example.toml` documents the section.

## 5. CLI

```
OmniRip obsidian-sync [--no-import] [--no-library] [--no-sessions]
                      [--no-studio] [--no-hub] [--retry-failed] [--timeout S] [--dry-run]
```

1. (import) `Queueable wants → submit_url("ytsearch1:<query>")` via the real
   `PipelineOrchestrator`; notes go to `queued`; after `wait_for_idle` (or timeout)
   terminal jobs settle notes to `done`/`failed`.
2. (export) `Library/` from report rows (`status == "upgraded"`), `Sessions/` per
   report, `Studio/` from both preset registries, then rewrite `OmniRip.md`.
3. `--dry-run` prints the planned import/export without writing; `--timeout` bounds
   how long the import lane is allowed to run before settling what finished.

## 6. Module surface

- `src/harvester/services/obsidian/`
  - `frontmatter.py` — encode/parse a YAML subset (scalars, quoted strings, inline
    lists and maps), `set_status`.
  - `naming.py` — `slugify`, `sanitize_part`, `album_note_name`, `resolve_within`.
  - `vault.py` — `VaultPaths.from_config`, `ensure`, atomic `write_note`.
  - `library.py` — `album_identity`, `group_by_album`, `build_album_note`, `export_library`.
  - `sessions.py` — `session_identity`, `build_session_note`, `export_sessions`.
  - `studio.py` — `build_preset_note`, `export_studio`.
  - `wants.py` — `read_want`, `list_wants`, `queueable`, `settle_note`, `append_omnirip_log`.
  - `sync.py` — `ObsidianSync` facade + `import_wants`/`settle_wants`.
- `harvester/__main__.py` — `obsidian-sync` subcommand and `_run_wants`.
- `harvester/config.py` — `ObsidianConfig`.

No orchestrator changes were required: the bridge is driven by the CLI, not by hooks,
per the "manual only" decision.

## 7. Tests

`tests/test_obsidian_{frontmatter,vault,library,sessions,wants,sync}.py` plus two
`tests/test_config.py` cases. Coverage: codec round-trips and tolerant parsing;
traversal guards; album grouping and note shape; session rollups; status flow incl.
`--retry-failed`; settlement to `done`/`failed`; config defaults and overrides.
`test_obsidian_sync.py::test_studio_index_and_hub_links_resolve_to_written_notes`
(added after the live run, §11) asserts every `[[wikilink]]` in `Studio/README.md`
and the hub resolves to a note that exists.
Baseline full suite before this doc: 483 passed, 1 skipped; ruff clean.

## 8. Acceptance criteria

- [x] `obsidian-sync` runs with `enabled = false` → tells the user how to enable, exit 3.
- [x] A report written by a Mode B run exports library + session notes on next sync.
- [x] Upgraded report rows group into one album note per `(artist, album)`.
- [x] Every note round-trips through the frontmatter codec (idempotent resync).
- [x] Wants note `want → queued → done|failed` transitions edit only `status` + the
      `## OmniRip` log, never the body.
- [x] Hidden files, `queued` notes, and terminal notes are never re-queued; `failed`
      notes re-queue only under `--retry-failed`.
- [x] No path escapes the vault (`resolve_within` + unit test).
- [x] No new dependencies; pipeline untouched; full suite still green.

## 9. Ponytail review — "what did we build the docs did not ask for?"

Nothing extra was shipped: the only unspec'd item considered (a TUI "Sync Obsidian"
button) was deliberately left out (docs/15 §1, manual-only decision). `--dry-run` and
`--timeout` were added to the spec here, not beyond it.

## 10. Follow-ups (not in scope)

- Auto-export a library note on job terminal state (needs a persisted single-URL
  ledger first — today only Mode B reports are durable).
- Status/state ledger so `queued` orphaned notes from a killed sync auto-recover.
- Dataview query examples page in the hub.

## 11. Live verification (2026-09-21, this machine)

Exercised against a real vault (`vault_dir = ~/Desktop/Ideas`) with the real services
(slskd 0.26.0.0, yt-dlp, fpcalc/AcoustID, ffmpeg), not test doubles:

1. **Real Mode B report.** A sandbox directory (`Imogen Heap/Speak for Yourself/`) holding
   one 128 kbps transcode (queued) and one 320 kbps file (skipped) was audited through
   `PipelineOrchestrator.submit_batch` — the same entry point the TUI uses. Report
   `omnirip-batch-20260921-211018.jsonl`: 1 `skipped` (reason `bitrate`) + 1 `upgraded`
   (`STREAM_OPUS`, real replacement, original moved into `.trash/`).
2. **Outbound.** `OmniRip --config config.toml obsidian-sync` wrote 12 notes: the album note
   `Library/imogen-heap/Imogen Heap — Speak for Yourself.md` (from the upgraded row), the
   session note carrying both rows, 8 preset notes plus the inventory index, and the hub.
3. **Inbound.** `Wants/Imogen Heap — Hide and Seek.md` (`status: want`) was queued through
   `ytsearch1:` and settled to `done` after a real rip: `status` flipped, the body was left
   untouched, and the `## OmniRip` log gained the job id, timestamps and output path.
4. **Ownership + idempotency.** `Journal/` was byte-identical before/after (sha256
   unchanged); a second `--no-import` sync rewrote all 14 notes byte-identically.

**Found and fixed during the run:** the preset wikilinks in `Studio/README.md` and the hub
used the raw preset id (`[[presets/fast_balanced]]`) while the notes on disk are slugified
(`presets/fast-balanced.md`) — 7 of the 8 links were dead in Obsidian. Both call sites now
use `naming.studio_note_name` and a regression test asserts every wikilink resolves;
re-running the sync on the real vault resolves 13/13 links.

**Operational note:** the CLI's default config file is the platform one
(`~/Library/Application Support/harvester/config.toml`, or `HARVESTER_DATA_DIR/config.toml`);
the project's `config.toml` is only read with `--config config.toml` or `HARVESTER_CONFIG`.
Both files now carry the `[obsidian]` section, so `OmniRip obsidian-sync` works without a flag.