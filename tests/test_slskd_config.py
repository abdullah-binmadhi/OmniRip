"""Unit and integration tests for Soulseek configuration and in-app credential manager."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import respx
from httpx import Response
from textual.app import App, ComposeResult
from textual.widgets import Input

from harvester.services.slskd_config import (
    check_soulseek_status,
    generate_api_key,
    read_slskd_credentials,
    save_slskd_credentials,
)
from harvester.ui.screens.soulseek_login import SoulseekLoginModal


def test_generate_api_key() -> None:
    key1 = generate_api_key()
    key2 = generate_api_key()
    assert len(key1) == 64
    assert len(key2) == 64
    assert key1 != key2
    int(key1, 16)  # Valid hex


def test_read_nonexistent_config(tmp_path: Path) -> None:
    res = read_slskd_credentials(repo_root=tmp_path)
    assert not res["configured"]
    assert not res["has_key"]
    assert res["username"] == ""
    assert res["password"] == ""


def test_save_and_read_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure environment doesn't interfere
    monkeypatch.delenv("SLSKD_API_KEY", raising=False)

    saved_key = save_slskd_credentials(
        username="audiophile_99",
        password="supersecretpassword",
        repo_root=tmp_path,
    )

    assert len(saved_key) == 64
    assert os.environ.get("SLSKD_API_KEY") == saved_key

    config_file = tmp_path / "tools" / "slskd" / "slskd.local.yml"
    assert config_file.is_file()

    read_back = read_slskd_credentials(repo_root=tmp_path)
    assert read_back["configured"]
    assert read_back["has_key"]
    assert read_back["username"] == "audiophile_99"
    assert read_back["password"] == "supersecretpassword"
    assert read_back["api_key"] == saved_key


def test_save_preserves_existing_custom_api_key(tmp_path: Path) -> None:
    custom_key = "my_custom_secret_key_1234567890"
    saved_key = save_slskd_credentials(
        username="user1",
        password="pass1",
        api_key=custom_key,
        repo_root=tmp_path,
    )
    assert saved_key == custom_key

    # Update username only without specifying key
    saved_key_2 = save_slskd_credentials(
        username="user2",
        password="pass2",
        repo_root=tmp_path,
    )
    assert saved_key_2 == custom_key

    creds = read_slskd_credentials(repo_root=tmp_path)
    assert creds["username"] == "user2"
    assert creds["password"] == "pass2"
    assert creds["api_key"] == custom_key


@pytest.mark.asyncio
@respx.mock
async def test_check_soulseek_status_connected() -> None:
    base_url = "http://127.0.0.1:5030"
    respx.get(f"{base_url}/api/v0/session").mock(return_value=Response(200, json={"user": "admin"}))
    respx.get(f"{base_url}/api/v0/server").mock(
        return_value=Response(
            200,
            json={"state": "Connected, LoggedIn", "isConnected": True, "isLoggedIn": True},
        )
    )

    status = await check_soulseek_status(base_url=base_url, api_key="valid_test_key")
    assert status["daemon_running"] is True
    assert status["api_authorized"] is True
    assert status["connected"] is True
    assert status["logged_in"] is True
    assert "Connected" in status["detail"]


@pytest.mark.asyncio
@respx.mock
async def test_check_soulseek_status_unauthorized() -> None:
    base_url = "http://127.0.0.1:5030"
    respx.get(f"{base_url}/api/v0/session").mock(return_value=Response(401))

    status = await check_soulseek_status(base_url=base_url, api_key="bad_key")
    assert status["daemon_running"] is True
    assert status["api_authorized"] is False
    assert "rejected" in status["detail"]


class DummyModalApp(App[None]):
    def __init__(self, modal: SoulseekLoginModal) -> None:
        super().__init__()
        self.modal = modal

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(self.modal)


@pytest.mark.asyncio
async def test_soulseek_login_modal_compose(tmp_path: Path) -> None:
    save_slskd_credentials("modal_user", "modal_pass", repo_root=tmp_path)
    modal = SoulseekLoginModal(repo_root=tmp_path)
    app = DummyModalApp(modal)

    async with app.run_test() as pilot:
        user_input = modal.query_one("#slsk-username", Input)
        pass_input = modal.query_one("#slsk-password", Input)
        assert user_input.value == "modal_user"
        assert pass_input.value == "modal_pass"

        # Press cancel button to dismiss
        await pilot.click("#btn-slsk-cancel")
