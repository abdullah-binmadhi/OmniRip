from harvester.services.environment import DependencyStatus, EnvironmentStatus


def test_required_dependency_controls_ready_state() -> None:
    status = EnvironmentStatus(
        {
            "ffmpeg": DependencyStatus("ffmpeg", True, True),
            "yt-dlp": DependencyStatus("yt-dlp", False, True, detail="missing"),
            "slskd": DependencyStatus("slskd", False, False, detail="offline"),
        }
    )

    assert not status.ready
    assert [item.name for item in status.missing_required] == ["yt-dlp"]
    assert status.get("slskd").severity == "warning"


def test_all_required_dependencies_ready_when_optional_services_are_down() -> None:
    status = EnvironmentStatus(
        {
            "ffmpeg": DependencyStatus("ffmpeg", True, True),
            "yt-dlp": DependencyStatus("yt-dlp", True, True),
            "slskd": DependencyStatus("slskd", False, False),
            "acoustid": DependencyStatus("acoustid", False, False),
        }
    )

    assert status.ready
    assert status.get("slskd").icon == "▲"
