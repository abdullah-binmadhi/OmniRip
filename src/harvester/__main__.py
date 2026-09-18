"""Command-line entry point for the OmniRip TUI."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from harvester import __version__
from harvester.config import load_config
from harvester.ui.app import HarvesterApp
from harvester.util.errors import ConfigError


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
    parser.add_argument("--enhance", help="enhance audio file directly via CLI without TUI", metavar="FILE")
    parser.add_argument("--preset", default="conservative", help="enhancement preset (default: conservative)")
    parser.add_argument("--bitrate", default="320k", help="output MP3 bitrate (default: 320k)")
    parser.add_argument("--version", action="version", version=f"OmniRip {__version__}")
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

    environment = dict(os.environ)
    if args.data_dir:
        environment["HARVESTER_DATA_DIR"] = args.data_dir
    try:
        config = load_config(args.config, environ=environment)
    except ConfigError as exc:
        print(f"OmniRip: configuration error: {exc}", file=sys.stderr)
        if exc.user_hint:
            print(f"hint: {exc.user_hint}", file=sys.stderr)
        return 2

    HarvesterApp(config).run()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the console script
    raise SystemExit(main())
