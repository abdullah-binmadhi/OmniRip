# Project Agent Instructions

## graphify knowledge graph — mandatory workflow

This project maintains a graphify knowledge graph at `graphify-out/graph.json`, built from
all documentation (`README.md`, `docs/*.md`) and any future code. The graph is the
persistent, low-token source of truth — keep it current and query it instead of re-reading
files.

### 1. When answering any question about this project

- **If `graphify-out/graph.json` exists:** run `graphify query "<question>"` from the
  project root FIRST and answer from the graph context. Open source files only for details
  the graph does not cover. Do not re-read whole documents to re-orient yourself.
- **If it does not exist:** run the full graphify pipeline first (see §3), then answer.

### 2. After EVERY turn that creates, modifies, or deletes project files

Before ending your response, update the graph so it never goes stale:

- Graph exists → run the graphify skill in update mode: `/graphify . --update`
  (incremental: code-only changes need no LLM; doc changes re-extract only changed files).
- No graph yet → run the full pipeline: `/graphify .`

This is required, not optional. A turn that edited files without updating the graph is
incomplete.

### 3. If the graphify CLI is not installed

Install/upgrade it first, then run the pipeline:

```
uv tool install --upgrade graphifyy     # preferred
pip install graphifyy                   # fallback
```

### 4. Notes

- All pipeline outputs live in `graphify-out/` (graph.json, graph.html, GRAPH_REPORT.md).
  Never hand-edit them; they are regenerated.
- Semantic extraction for docs uses subagents or the configured LLM backend per the
  graphify skill; follow the skill's steps exactly.
- Optional hardening (only if the project becomes a git repo): `graphify hook install`
  adds a post-commit auto-rebuild for code changes. Doc changes still need §2 above.

## Minimal implementation ladder

Adapted from [ponytail](https://github.com/DietrichGebert/ponytail) (MIT). Before writing
new code, stop at the first rung that holds:

1. Does this need to exist? — no: skip it (YAGNI)
2. Already in this codebase? — reuse it, don't rewrite
3. Python stdlib does it? — use it
4. Native/platform feature does it? — use it (OS APIs, ffmpeg, shell tools)
5. Installed dependency does it? — use it (textual, httpx, mutagen, yt-dlp, numpy)
6. One line? — one line
7. Only then: the minimum that works

Mandatory guards (never on the chopping block):

- **Lazy about the solution, never about reading.** Read the code you touch and trace the
  real flow before picking a rung.
- **Spec-mandated bodies are requirements, not YAGNI candidates.** `docs/01–09` fix the
  spectral algorithm, verdict thresholds, atomic-swap steps, scoring weights, fixtures,
  and acceptance criteria; implement them in full with tests. The ladder applies only to
  scaffolding and unspec'd extras.
- Never skip validation, error handling, cancellation, timeouts, or tests to save lines.
- At the end of each milestone, run ponytail's review question over the diff: "What did
  we build that the docs did not ask for?" Delete it, or justify it in `docs/01` §5.
