"""Command-line entry point for the OmniRip TUI."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from harvester import __version__
from harvester.config import load_config, load_env_file
from harvester.ui.app import HarvesterApp
from harvester.util.errors import ConfigError

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="OmniRip",
        description="OmniRip: P2P-first music acquisition and curation TUI",
    )
    parser.add_argument("--config", help="path to a TOML configuration file")
    parser.add_argument(
        "--data-dir",
        help="override the platform data directory (useful for isolated profiles)",
    )
    parser.add_argument(
        "--enhance",
        help="enhance audio file directly via CLI without TUI",
        metavar="FILE",
    )
    parser.add_argument(
        "--preset",
        default="conservative",
        help="enhancement preset (default: conservative)",
    )
    parser.add_argument("--bitrate", default="320k", help="output MP3 bitrate (default: 320k)")
    parser.add_argument(
        "--download-models",
        action="store_true",
        help="download and verify default AI model weights (Demucs, FlashSR) and exit",
    )
    parser.add_argument("--version", action="version", version=f"OmniRip {__version__}")

    sync = parser.add_subparsers(dest="command")
    obsidian = sync.add_parser(
        "obsidian-sync",
        help="sync the local Obsidian vault (docs/15)",
        description=(
            "Two-way sync with the Obsidian vault configured in [obsidian]. Imports Wants/ "
            "notes into the rip queue and exports Library/, Sessions/, Studio/ and the hub."
        ),
    )
    obsidian.add_argument("--no-import", action="store_true", help="do not rip Wants/ notes")
    obsidian.add_argument("--no-library", action="store_true", help="do not export album notes")
    obsidian.add_argument("--no-sessions", action="store_true", help="do not export session notes")
    obsidian.add_argument("--no-studio", action="store_true", help="do not export preset notes")
    obsidian.add_argument("--no-hub", action="store_true", help="do not rewrite the hub note")
    obsidian.add_argument(
        "--retry-failed", action="store_true", help="re-queue Wants/ notes marked failed"
    )
    obsidian.add_argument(
        "--timeout",
        type=float,
        default=3600.0,
        help="seconds to keep running the imported rip queue before giving up (default: 3600)",
    )
    obsidian.add_argument(
        "--dry-run",
        action="store_true",
        help="list what would be imported/exported without writing anything",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.enhance:
        from pathlib import Path

        from harvester.analysis.enhancement.presets import PRESETS
        from harvester.services.enhancement.exporter import EnhancementExporter

        target_file = Path(args.enhance)
        if not target_file.exists():
            print(f"OmniRip: file not found: {target_file}", file=sys.stderr)
            return 1

        preset = PRESETS.get(args.preset)
        if not preset:
            print(
                f"OmniRip: unknown preset '{args.preset}'. Available: {list(PRESETS.keys())}",
                file=sys.stderr,
            )
            return 1

        print(f"OmniRip: Enhancing '{target_file.name}' with preset '{preset.name}'...")
        try:
            exporter = EnhancementExporter()
            out_file = exporter.export_enhanced_derivative(
                input_path=target_file,
                preset=preset,
                bitrate=args.bitrate,
            )
            print(f"OmniRip: Exported enhanced MP3: {out_file}")
            return 0
        except Exception as err:
            print(f"OmniRip: enhancement failed: {err}", file=sys.stderr)
            return 1

    if args.download_models:
        from harvester.services.model_manager import ModelManager

        print("OmniRip: Verifying and downloading default AI model weights...")
        mm = ModelManager()
        models_to_download = ["hdemucs", "flashsr", "flashsr_ldm", "flashsr_vae"]
        for name in models_to_download:
            if mm.is_cached(name):
                print(f"  ✓ {name}: cached locally")
            else:
                print(f"  ↓ {name}: downloading...", end="", flush=True)
                try:
                    mm.download_model(
                        name,
                        progress_callback=lambda p, n=name: print(
                            f"\r  ↓ {n}: {int(p * 100)}%", end="", flush=True
                        ),
                    )
                    print(f"\r  ✓ {name}: downloaded and verified")
                except Exception as err:
                    print(f"\r  ✗ {name}: download skipped or failed ({err})")
        print("OmniRip: Model provisioning check complete.")
        return 0

    environment = dict(os.environ)
    if args.data_dir:
        environment["HARVESTER_DATA_DIR"] = args.data_dir
    # NFR-6: API keys come from the environment. A local gitignored .env (next
    # to the config or in the project root) is read here so GUI launches — which
    # do not inherit shell exports — still find ACOUSTID_API_KEY et al.
    loaded = load_env_file(config_path=args.config, environ=environment)
    if loaded:
        logger.debug("Loaded %d key(s) from a local .env file", len(loaded))
    try:
        config = load_config(args.config, environ=environment)
    except ConfigError as exc:
        print(f"OmniRip: configuration error: {exc}", file=sys.stderr)
        if exc.user_hint:
            print(f"hint: {exc.user_hint}", file=sys.stderr)
        return 2

    if args.command == "obsidian-sync":
        return _run_obsidian_sync(config, args)

    HarvesterApp(config).run()
    return 0


def _run_obsidian_sync(config, args) -> int:
    """``OmniRip obsidian-sync``: two-way sync with the Obsidian vault (docs/15)."""
    import asyncio

    from harvester.batch.report import BatchReport
    from harvester.services.obsidian.sync import ObsidianSync

    if not config.obsidian.enabled:
        print(
            "OmniRip: the Obsidian bridge is disabled. Set [obsidian] enabled = true "
            "with a vault_dir in config.toml (docs/15).",
            file=sys.stderr,
        )
        return 3

    sync = ObsidianSync(config.obsidian)
    sync.ensure()
    queueable_wants = [
        note
        for note in sync.wants()
        if note.status == "want" or (note.status == "failed" and args.retry_failed)
    ]
    reports = (
        sorted(config.paths.reports.glob("*.jsonl")) if config.paths.reports.exists() else []
    )

    if args.dry_run:
        print(f"OmniRip: dry run against vault {sync.vault.root}")
        for note in queueable_wants:
            rel = note.path.relative_to(sync.vault.root)
            print(f"  import: {rel} -> query '{note.query}'")
        print(f"  export: {len(reports)} session report(s), Library, Studio presets, hub")
        return 0

    if not args.no_import and queueable_wants:
        asyncio.run(_run_wants(sync, config, args, [note.query for note in queueable_wants]))

    exported: list[str] = []
    if not args.no_library:
        rows = [
            row
            for report in reports
            for row in BatchReport(report).rows()
            if row.get("status") == "upgraded"
        ]
        exported.extend(str(path) for path in sync.export_library(rows))
    if not args.no_sessions:
        exported.extend(str(path) for path in sync.export_sessions(reports))
    if not args.no_studio:
        exported.extend(str(path) for path in sync.export_studio())
    if not args.no_hub:
        exported.append(str(sync.write_hub()))
    print(f"OmniRip: obsidian-sync exported {len(exported)} note(s) to {sync.vault.root}")
    return 0


async def _run_wants(sync, config, args, queries) -> None:
    """Rip queued Wants notes through the real pipeline, then reconcile statuses."""

    from harvester.pipeline.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(config)

    async def submit(query: str):
        return await orchestrator.submit_url(f"ytsearch1:{query}")

    try:
        pending = await sync.import_wants(submit, retry_failed=args.retry_failed)
    except Exception as exc:
        print(f"OmniRip: queueing Wants notes failed: {exc}", file=sys.stderr)
        await orchestrator.shutdown()
        return
    if not pending:
        await orchestrator.shutdown()
        return
    print(f"OmniRip: importing {len(pending)} want note(s); running until idle…")
    try:
        await orchestrator.wait_for_idle(timeout_s=args.timeout)
    except TimeoutError:
        print("OmniRip: import exceeded the timeout; settling whatever finished", file=sys.stderr)
    finally:
        results = sync.settle_wants(pending)
        await orchestrator.shutdown()
    done = [note for note, status in results.items() if status == "done"]
    failed = [note for note, status in results.items() if status == "failed"]
    print(f"OmniRip: wants settled — {len(done)} ready, {len(failed)} failed.")


if __name__ == "__main__":  # pragma: no cover - exercised through the console script
    raise SystemExit(main())
