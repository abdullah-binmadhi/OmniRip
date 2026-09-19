"""Log console filter tests (docs/08 §5: INFO -> DEBUG -> WARN+ERROR cycling)."""

from __future__ import annotations

from harvester.ui.logconsole import FILTER_MODES, level_passes, next_mode


def test_level_passes_debug_shows_everything() -> None:
    assert level_passes("DEBUG", "DEBUG")
    assert level_passes("DEBUG", "INFO")
    assert level_passes("DEBUG", "WARNING")
    assert level_passes("DEBUG", "ERROR")


def test_level_passes_info_hides_debug() -> None:
    assert level_passes("INFO", "INFO")
    assert level_passes("INFO", "WARNING")
    assert level_passes("INFO", "ERROR")
    assert not level_passes("INFO", "DEBUG")


def test_level_passes_warn_error_hides_info() -> None:
    assert level_passes("WARN+ERROR", "WARNING")
    assert level_passes("WARN+ERROR", "ERROR")
    assert not level_passes("WARN+ERROR", "INFO")
    assert not level_passes("WARN+ERROR", "DEBUG")


def test_next_mode_cycles_in_documented_order() -> None:
    assert next_mode("INFO") == "WARN+ERROR"
    assert next_mode("WARN+ERROR") == "DEBUG"
    assert next_mode("DEBUG") == "INFO"


def test_filter_modes_are_three_and_ordered() -> None:
    assert FILTER_MODES == ("DEBUG", "INFO", "WARN+ERROR")
