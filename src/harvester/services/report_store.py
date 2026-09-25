"""
Persistent Report Store and Preset Recipe Engine for OmniRip.

Saves, indexes, renames, and retrieves mastering and stem reports,
enabling 1-click re-application of past acoustic triage recipes.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import platformdirs

logger = logging.getLogger(__name__)


@dataclass
class MasteringReport:
    """Complete serialized mastering report and remediation recipe."""

    id: str
    name: str
    created_at: str
    track_name: str
    track_path: str
    workflow: str  # "enhance_only" or "stems_only"
    genre: str = "Pop"
    genre_intensity: str = "balanced"
    triage_answers: dict[str, bool] = field(default_factory=dict)
    eq_bands: dict[str, float] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MasteringReport:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "Untitled Report")),
            created_at=str(data.get("created_at", "")),
            track_name=str(data.get("track_name", "Unknown Track")),
            track_path=str(data.get("track_path", "")),
            workflow=str(data.get("workflow", "enhance_only")),
            genre=str(data.get("genre", "Pop")),
            genre_intensity=str(data.get("genre_intensity", "balanced")),
            triage_answers=dict(data.get("triage_answers", {})),
            eq_bands={str(k): float(v) for k, v in data.get("eq_bands", {}).items()},
            metrics=dict(data.get("metrics", {})),
        )


@dataclass(frozen=True)
class ReportSummary:
    """Lightweight summary of a stored report for fast list display."""

    id: str
    name: str
    created_at: str
    track_name: str
    genre: str
    workflow: str
    num_remediations: int


class ReportStore:
    """Filesystem-backed persistent repository for mastering reports."""

    def __init__(self, reports_dir: Path | None = None) -> None:
        if reports_dir is not None:
            self.reports_dir = Path(reports_dir)
        else:
            self.reports_dir = Path(platformdirs.user_data_dir("harvester")) / "reports"
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("Could not create reports directory %s: %s", self.reports_dir, e)

    def save_report(
        self,
        track_name: str,
        track_path: str,
        workflow: str = "enhance_only",
        genre: str = "Pop",
        genre_intensity: str = "balanced",
        triage_answers: dict[str, bool] | None = None,
        eq_bands: dict[str, float] | None = None,
        metrics: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> MasteringReport:
        """Create and persist a new mastering report."""
        now = datetime.now(UTC)
        ts_slug = now.strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:6]
        report_id = f"rep_{ts_slug}_{short_id}"

        display_name = name or f"{track_name} ({genre})"
        report = MasteringReport(
            id=report_id,
            name=display_name,
            created_at=now.isoformat(),
            track_name=track_name,
            track_path=str(track_path),
            workflow=workflow,
            genre=genre,
            genre_intensity=genre_intensity,
            triage_answers=dict(triage_answers or {}),
            eq_bands={str(k): float(v) for k, v in (eq_bands or {}).items()},
            metrics=dict(metrics or {}),
        )

        file_path = self.reports_dir / f"{report_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
        except Exception as e:
            logger.error("Failed to write report %s: %s", file_path, e)

        return report

    def list_reports(self) -> list[ReportSummary]:
        """List all available reports, sorted newest first."""
        summaries: list[ReportSummary] = []
        if not self.reports_dir.exists():
            return summaries

        for file_path in self.reports_dir.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                num_fixes = sum(1 for v in data.get("triage_answers", {}).values() if v is True)
                summaries.append(
                    ReportSummary(
                        id=str(data.get("id", file_path.stem)),
                        name=str(data.get("name", file_path.stem)),
                        created_at=str(data.get("created_at", "")),
                        track_name=str(data.get("track_name", "Unknown Track")),
                        genre=str(data.get("genre", "Pop")),
                        workflow=str(data.get("workflow", "enhance_only")),
                        num_remediations=num_fixes,
                    )
                )
            except Exception as e:
                logger.warning("Could not read report file %s: %s", file_path, e)

        # Sort newest first by created_at
        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries

    def get_report(self, report_id: str) -> MasteringReport | None:
        """Fetch a complete report by its ID."""
        file_path = self.reports_dir / f"{report_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return MasteringReport.from_dict(data)
        except Exception as e:
            logger.error("Failed to load report %s: %s", file_path, e)
            return None

    def rename_report(self, report_id: str, new_name: str) -> bool:
        """Rename an existing report's display label."""
        report = self.get_report(report_id)
        if report is None:
            return False
        report.name = new_name.strip()
        file_path = self.reports_dir / f"{report_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error("Failed to update report %s: %s", file_path, e)
            return False

    def delete_report(self, report_id: str) -> bool:
        """Delete a report file from disk."""
        file_path = self.reports_dir / f"{report_id}.json"
        if not file_path.exists():
            return False
        try:
            file_path.unlink()
            return True
        except Exception as e:
            logger.error("Failed to delete report %s: %s", file_path, e)
            return False
