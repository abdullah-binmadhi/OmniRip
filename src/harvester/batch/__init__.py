"""Mode B batch audit: scanner, trash lifecycle, incremental report, and auto-restoration."""

from harvester.batch.report import BatchReport, batch_report_name, job_row, skipped_row
from harvester.batch.restoration import (
    BatchRestoreSummary,
    BatchRestoreTrackResult,
    restore_directory,
    restore_file,
    safe_swap,
    should_restore_entry,
)
from harvester.batch.scanner import AUDIO_EXTENSIONS, scan_directory
from harvester.batch.trash import move_to_trash, purge, rollback, trash_root_for

__all__ = [
    "AUDIO_EXTENSIONS",
    "BatchReport",
    "BatchRestoreSummary",
    "BatchRestoreTrackResult",
    "batch_report_name",
    "job_row",
    "move_to_trash",
    "purge",
    "restore_directory",
    "restore_file",
    "rollback",
    "safe_swap",
    "scan_directory",
    "should_restore_entry",
    "skipped_row",
    "trash_root_for",
]
