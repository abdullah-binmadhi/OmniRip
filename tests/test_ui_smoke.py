import pytest

textual = pytest.importorskip("textual")


from harvester.config import load_config  # noqa: E402
from harvester.ui.app import HarvesterApp  # noqa: E402


@pytest.mark.asyncio
async def test_m0_shell_mounts_without_startup_checks(tmp_path):
    config = load_config(environ={"HARVESTER_DATA_DIR": str(tmp_path / "data")})
    app = HarvesterApp(config, auto_startup=False)

    async with app.run_test() as pilot:
        assert app.query_one("#jobs")
        assert app.query_one("#statusbar")
        assert app.query_one("#logs")
        await pilot.press("?")
        assert app.screen.__class__.__name__ == "HelpScreen"
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.__class__.__name__ != "HelpScreen"
