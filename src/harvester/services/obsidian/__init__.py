"""Obsidian vault bridge: read/write a local vault as OmniRip's second brain (docs/15).

The package keeps the contact surface tiny and stdlib-only:

- :mod:`frontmatter` — a small, deterministic YAML frontmatter codec (no PyYAML).
- :mod:`naming` — traversal-safe, human-readable note paths and slugs.
- :mod:`vault` — vault layout, atomic writes, and owned-namespace helpers.
- :mod:`library` / :mod:`sessions` / :mod:`studio` — outbound exports.
- :mod:`wants` — the inbound rip queue living in the vault.
- :mod:`sync` — the CLI-facing orchestration entry points.
"""

from harvester.services.obsidian.sync import ObsidianSync

__all__ = ["ObsidianSync"]