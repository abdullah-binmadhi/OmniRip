"""Management and auto-generation of local slskd configuration and credentials."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_API_KEY_PLACEHOLDER = "CHANGE_ME_TO_A_RANDOM_32_BYTE_SECRET"
_DEFAULT_USER_PLACEHOLDER = "YOUR_SOULSEEK_USERNAME"


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the OmniRip repository root directory."""
    curr = (start or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "pyproject.toml").is_file() and (parent / "tools" / "slskd").is_dir():
            return parent
    return curr


def get_slskd_config_path(repo_root: Path | None = None) -> Path:
    """Return path to tools/slskd/slskd.local.yml."""
    root = repo_root or find_repo_root()
    return root / "tools" / "slskd" / "slskd.local.yml"


def get_slskd_template_path(repo_root: Path | None = None) -> Path:
    """Return path to tools/slskd/slskd.yml template."""
    root = repo_root or find_repo_root()
    return root / "tools" / "slskd" / "slskd.yml"


def generate_api_key() -> str:
    """Generate a cryptographically secure 32-byte hex secret (64 characters)."""
    return secrets.token_hex(32)


def read_slskd_credentials(repo_root: Path | None = None) -> dict[str, Any]:
    """Read credentials and API key from slskd.local.yml if present."""
    config_path = get_slskd_config_path(repo_root)
    result = {
        "username": "",
        "password": "",
        "api_key": "",
        "configured": False,
        "has_key": False,
        "exists": config_path.is_file(),
    }
    if not config_path.is_file():
        return result

    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to read %s: %s", config_path, exc)
        return result

    # Extract username
    m_user = re.search(r"^\s*username:\s*(.+)$", content, re.MULTILINE)
    if m_user:
        raw_user = m_user.group(1).strip().strip("\"'")
        if raw_user != _DEFAULT_USER_PLACEHOLDER:
            result["username"] = raw_user

    # Extract password
    m_pass = re.search(r"^\s*password:\s*(.+)$", content, re.MULTILINE)
    if m_pass:
        raw_pass = m_pass.group(1).strip().strip("\"'")
        if raw_pass != "CHANGE_ME":
            result["password"] = raw_pass

    # Extract api_key
    m_key = re.search(r"^\s*api_key:\s*(.+)$", content, re.MULTILINE)
    if m_key:
        raw_key = m_key.group(1).strip().strip("\"'")
        if raw_key and raw_key != _DEFAULT_API_KEY_PLACEHOLDER:
            result["api_key"] = raw_key

    result["configured"] = bool(result["username"])
    result["has_key"] = bool(result["api_key"])
    return result


def save_slskd_credentials(
    username: str,
    password: str,
    api_key: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """Save Soulseek credentials and ensure a valid local API key exists.

    Returns the effective slskd API key.
    """
    config_path = get_slskd_config_path(repo_root)
    template_path = get_slskd_template_path(repo_root)

    # Determine existing key if not provided
    effective_key = (api_key or "").strip()
    if not effective_key:
        existing = read_slskd_credentials(repo_root)
        env_key = os.environ.get("SLSKD_API_KEY")
        if existing.get("has_key"):
            effective_key = existing["api_key"]
        elif env_key and env_key != _DEFAULT_API_KEY_PLACEHOLDER:
            effective_key = env_key
        else:
            effective_key = generate_api_key()

    # Read base template or existing file
    base_content = ""
    if config_path.is_file():
        try:
            base_content = config_path.read_text(encoding="utf-8")
        except OSError:
            base_content = ""

    if not base_content and template_path.is_file():
        try:
            base_content = template_path.read_text(encoding="utf-8")
        except OSError:
            base_content = ""

    clean_user = username.strip()
    clean_pass = password.strip()

    if base_content:
        # Replace username
        if re.search(r"^\s*username:.*$", base_content, re.MULTILINE):
            new_content = re.sub(
                r"^(\s*username:).*$",
                rf"\1 {clean_user}",
                base_content,
                flags=re.MULTILINE,
            )
        else:
            new_content = base_content + f"\nsoulseek:\n  username: {clean_user}\n"

        # Replace password
        if re.search(r"^\s*password:.*$", new_content, re.MULTILINE):
            new_content = re.sub(
                r"^(\s*password:).*$",
                rf"\1 {clean_pass}",
                new_content,
                flags=re.MULTILINE,
            )
        else:
            new_content += f"  password: {clean_pass}\n"

        # Replace api_key
        if re.search(r"^\s*api_key:.*$", new_content, re.MULTILINE):
            new_content = re.sub(
                r"^(\s*api_key:).*$",
                rf"\1 {effective_key}",
                new_content,
                flags=re.MULTILINE,
            )
        else:
            new_content += f"\nweb:\n  authentication:\n    api_key: {effective_key}\n"
    else:
        # Build standard minimal config
        new_content = (
            "soulseek:\n"
            f"  username: {clean_user}\n"
            f"  password: {clean_pass}\n"
            "  listen_port: 50300\n"
            "web:\n"
            "  listen:\n"
            "    ip: 127.0.0.1\n"
            "    ports:\n"
            "      - 5030\n"
            "  authentication:\n"
            f"    api_key: {effective_key}\n"
            "  url_base: /\n"
            "remote_configuration: true\n"
            "feature:\n"
            "  swagger: true\n"
        )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(new_content, encoding="utf-8")
    try:
        config_path.chmod(0o600)
    except OSError:
        pass

    # Synchronize environment
    os.environ["SLSKD_API_KEY"] = effective_key
    return effective_key


async def check_soulseek_status(
    base_url: str = "http://127.0.0.1:5030",
    api_key: str | None = None,
    timeout_s: float = 4.0,
) -> dict[str, Any]:
    """Query local slskd daemon session and Soulseek network connection status."""
    secret = (api_key or os.environ.get("SLSKD_API_KEY") or "").strip()
    headers = {"X-API-Key": secret} if secret else {}
    timeout = httpx.Timeout(timeout_s)

    status: dict[str, Any] = {
        "daemon_running": False,
        "api_authorized": False,
        "connected": False,
        "logged_in": False,
        "state": "offline",
        "detail": "Daemon not reachable",
    }

    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            session_resp = await client.get("/api/v0/session")
            if session_resp.status_code in {401, 403}:
                status["daemon_running"] = True
                status["api_authorized"] = False
                status["detail"] = "Local API key rejected (401/403)"
                return status

            session_resp.raise_for_status()
            status["daemon_running"] = True
            status["api_authorized"] = True

            # Query Soulseek server connection state
            try:
                server_resp = await client.get("/api/v0/server")
                if server_resp.is_success:
                    server_data = server_resp.json()
                    status["connected"] = bool(server_data.get("isConnected"))
                    status["logged_in"] = bool(server_data.get("isLoggedIn"))
                    state_str = server_data.get("state", "")
                    status["state"] = state_str
                    if status["logged_in"]:
                        status["detail"] = "Connected & Logged In"
                    elif state_str:
                        status["detail"] = f"Soulseek state: {state_str}"
                    else:
                        status["detail"] = "Connected to daemon; Soulseek logging in..."
                else:
                    status["detail"] = (
                        f"Daemon connected (server status HTTP {server_resp.status_code})"
                    )
            except Exception as err:
                status["detail"] = f"Daemon connected; error querying server status: {err}"
    except httpx.HTTPError as exc:
        status["detail"] = f"Connection failed: {exc}"

    return status


async def restart_slskd_daemon(repo_root: Path | None = None) -> bool:
    """Attempt to start or restart the local slskd daemon process."""
    root = repo_root or find_repo_root()
    daemon_bin = root / "tools" / "slskd" / "slskd"

    if not daemon_bin.is_file():
        logger.warning("slskd binary not found at %s", daemon_bin)
        return False

    # Check if executable
    if not os.access(daemon_bin, os.X_OK):
        try:
            daemon_bin.chmod(0o755)
        except OSError:
            pass

    # Kill any existing slskd process started by this user
    try:
        pkill = await asyncio.create_subprocess_exec(
            "pkill",
            "-f",
            "slskd.*slskd.local.yml",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(pkill.wait(), timeout=3.0)
    except Exception:
        pass

    # Start new daemon process in background
    try:
        log_file = root / "tools" / "slskd" / "slskd.log"
        with log_file.open("ab") as out:
            await asyncio.create_subprocess_exec(
                str(daemon_bin),
                "--config",
                "slskd.local.yml",
                cwd=str(root / "tools" / "slskd"),
                stdout=out,
                stderr=out,
                start_new_session=True,
            )
        # Give daemon a moment to bind port
        await asyncio.sleep(1.0)
        return True
    except Exception as exc:
        logger.error("Failed to start slskd daemon: %s", exc)
        return False
