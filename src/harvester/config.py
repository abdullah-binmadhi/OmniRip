"""Validated TOML configuration with file, environment, and CLI precedence."""

from __future__ import annotations

import copy
import os
import re
import tomllib
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from harvester.appdirs import AppPaths
from harvester.processing import DEFAULT_PRESET, TAG_THRESHOLD
from harvester.processing import PRESETS as PROCESSING_PRESETS
from harvester.util.errors import ConfigError

_SECRET_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
_TRANSCODE_MODES = {
    "mp3-128",
    "mp3-192",
    "mp3-256",
    "mp3-320",
    "mp3-v0",
    "keep-opus",
}


@dataclass(frozen=True, slots=True)
class GeneralConfig:
    output_dir: Path
    log_level_file: str = "DEBUG"
    log_level_ui: str = "INFO"
    first_run_notice_accepted: bool = False


@dataclass(frozen=True, slots=True)
class SlskdConfig:
    enabled: bool = True
    url: str = "http://localhost:5000"
    api_key_env: str = "SLSKD_API_KEY"
    download_dir: Path = Path("~/Music/slskd")
    search_timeout_s: float = 25.0
    poll_interval_s: float = 1.5
    max_concurrent_downloads: int = 2
    verify_openapi: bool = True
    stall_timeout_s: float = 120.0
    acquisition_mode: str = "best_available"
    max_queue_length: int = 5
    p2p_timeout_s: float = 30.0


@dataclass(frozen=True, slots=True)
class AcoustidConfig:
    api_key_env: str = "ACOUSTID_API_KEY"
    rate_limit_per_s: float = 3.0
    cache_ttl_days: int = 90


@dataclass(frozen=True, slots=True)
class RestorationSettings:
    enabled: bool = False
    mode: str = "conservative"
    preserve_original: bool = True


@dataclass(frozen=True, slots=True)
class YtdlpConfig:
    binary: str = "yt-dlp"
    format: str = "bestaudio[acodec^=opus]/bestaudio/best"
    cookies_from_browser: str = ""
    stall_timeout_s: float = 90.0
    total_timeout_s: float = 900.0


@dataclass(frozen=True, slots=True)
class FfmpegConfig:
    binary: str = "ffmpeg"
    probe_binary: str = "ffprobe"
    transcode: str = "mp3-320"


@dataclass(frozen=True, slots=True)
class SpectralConfig:
    enabled: bool = True
    excerpt_s: float = 60.0
    strict: bool = False


@dataclass(frozen=True, slots=True)
class BatchConfig:
    skip_bitrate_kbps: int = 256
    playlist_cap: int = 50
    rename_to_canonical: bool = False
    trash_retention_days: int = 7
    auto_purge_trash: bool = False


@dataclass(frozen=True, slots=True)
class TimeoutConfig:
    probe_s: float = 30.0
    fpcalc_s: float = 60.0
    acoustid_s: float = 15.0
    coverart_s: float = 15.0
    transcode_s: float = 300.0
    ffprobe_s: float = 15.0
    spectral_s: float = 30.0
    health_s: float = 5.0
    kill_grace_s: float = 5.0


@dataclass(frozen=True, slots=True)
class ProcessingSettings:
    """Which pipeline stages run (docs/13): fetch_only | standard | neural_full."""

    preset: str = DEFAULT_PRESET
    use_credits: bool = True
    tag_threshold: float = TAG_THRESHOLD


@dataclass(frozen=True, slots=True)
class UiConfig:
    refresh_hz: int = 8
    max_log_lines: int = 2000
    status_interval_s: float = 10.0


@dataclass(frozen=True, slots=True)
class AppConfig:
    general: GeneralConfig
    slskd: SlskdConfig
    acoustid: AcoustidConfig
    restoration: RestorationSettings
    ytdlp: YtdlpConfig
    ffmpeg: FfmpegConfig
    spectral: SpectralConfig
    batch: BatchConfig
    processing: ProcessingSettings
    timeouts: TimeoutConfig
    ui: UiConfig
    paths: AppPaths

    def validate(self) -> AppConfig:
        """Validate cross-field invariants and return this config for fluent use."""

        if self.general.log_level_file not in _LOG_LEVELS:
            raise ConfigError(f"Unsupported file log level: {self.general.log_level_file}")
        if self.general.log_level_ui not in _LOG_LEVELS:
            raise ConfigError(f"Unsupported UI log level: {self.general.log_level_ui}")
        if urlparse(self.slskd.url).scheme not in {"http", "https"}:
            raise ConfigError("slskd.url must use http:// or https://")
        for label, value in (
            ("slskd.search_timeout_s", self.slskd.search_timeout_s),
            ("slskd.poll_interval_s", self.slskd.poll_interval_s),
            ("slskd.stall_timeout_s", self.slskd.stall_timeout_s),
            ("ytdlp.stall_timeout_s", self.ytdlp.stall_timeout_s),
            ("ytdlp.total_timeout_s", self.ytdlp.total_timeout_s),
            ("acoustid.rate_limit_per_s", self.acoustid.rate_limit_per_s),
            ("spectral.excerpt_s", self.spectral.excerpt_s),
            ("ui.status_interval_s", self.ui.status_interval_s),
        ):
            if value <= 0:
                raise ConfigError(f"{label} must be greater than zero")
        if self.slskd.max_concurrent_downloads < 1:
            raise ConfigError("slskd.max_concurrent_downloads must be at least 1")
        if self.restoration.mode not in {"conservative"}:
            raise ConfigError("restoration.mode must be conservative")
        if self.restoration.enabled and not self.restoration.preserve_original:
            raise ConfigError("restoration.preserve_original must remain true")
        if self.slskd.acquisition_mode not in {
            "best_available",
            "lossless_preferred",
            "fast_fallback",
            "highest_quality_mp3",
        }:
            raise ConfigError(
                "slskd.acquisition_mode must be best_available, lossless_preferred, "
                "fast_fallback, or highest_quality_mp3"
            )
        if self.slskd.max_queue_length < 0:
            raise ConfigError("slskd.max_queue_length must be zero or greater")
        if self.processing.preset not in PROCESSING_PRESETS:
            raise ConfigError(
                "processing.preset must be one of " + ", ".join(sorted(PROCESSING_PRESETS))
            )
        if not 0.0 < self.processing.tag_threshold <= 1.0:
            raise ConfigError("processing.tag_threshold must be greater than 0 and at most 1")
        if self.batch.skip_bitrate_kbps < 1:
            raise ConfigError("batch.skip_bitrate_kbps must be at least 1")
        if self.batch.playlist_cap < 1:
            raise ConfigError("batch.playlist_cap must be at least 1")
        if self.batch.trash_retention_days < 0:
            raise ConfigError("batch.trash_retention_days cannot be negative")
        if self.ui.refresh_hz < 1 or self.ui.refresh_hz > 60:
            raise ConfigError("ui.refresh_hz must be between 1 and 60")
        if self.ui.max_log_lines < 100:
            raise ConfigError("ui.max_log_lines must be at least 100")
        if self.ffmpeg.transcode not in _TRANSCODE_MODES:
            raise ConfigError(f"ffmpeg.transcode must be one of {sorted(_TRANSCODE_MODES)}")
        for label, value in (
            ("slskd.api_key_env", self.slskd.api_key_env),
            ("acoustid.api_key_env", self.acoustid.api_key_env),
        ):
            if not _SECRET_NAME.fullmatch(value):
                raise ConfigError(f"{label} must be an uppercase environment variable name")
        return self

    def public_dict(self) -> dict[str, Any]:
        """Return diagnostic configuration without exposing secret values."""

        return {
            "general": {
                "output_dir": str(self.general.output_dir),
                "log_level_file": self.general.log_level_file,
                "log_level_ui": self.general.log_level_ui,
                "first_run_notice_accepted": self.general.first_run_notice_accepted,
            },
            "slskd": {
                "enabled": self.slskd.enabled,
                "url": self.slskd.url,
                "api_key_env": self.slskd.api_key_env,
                "download_dir": str(self.slskd.download_dir),
                "search_timeout_s": self.slskd.search_timeout_s,
                "poll_interval_s": self.slskd.poll_interval_s,
                "max_concurrent_downloads": self.slskd.max_concurrent_downloads,
                "verify_openapi": self.slskd.verify_openapi,
                "stall_timeout_s": self.slskd.stall_timeout_s,
                "acquisition_mode": self.slskd.acquisition_mode,
                "max_queue_length": self.slskd.max_queue_length,
                "p2p_timeout_s": self.slskd.p2p_timeout_s,
            },
            "acoustid": {
                "api_key_env": self.acoustid.api_key_env,
                "rate_limit_per_s": self.acoustid.rate_limit_per_s,
                "cache_ttl_days": self.acoustid.cache_ttl_days,
            },
            "restoration": {
                "enabled": self.restoration.enabled,
                "mode": self.restoration.mode,
                "preserve_original": self.restoration.preserve_original,
            },
            "ytdlp": {
                "binary": self.ytdlp.binary,
                "format": self.ytdlp.format,
                "cookies_from_browser": bool(self.ytdlp.cookies_from_browser),
                "stall_timeout_s": self.ytdlp.stall_timeout_s,
                "total_timeout_s": self.ytdlp.total_timeout_s,
            },
            "ffmpeg": {
                "binary": self.ffmpeg.binary,
                "probe_binary": self.ffmpeg.probe_binary,
                "transcode": self.ffmpeg.transcode,
            },
            "spectral": {
                "enabled": self.spectral.enabled,
                "excerpt_s": self.spectral.excerpt_s,
                "strict": self.spectral.strict,
            },
            "batch": {
                "skip_bitrate_kbps": self.batch.skip_bitrate_kbps,
                "playlist_cap": self.batch.playlist_cap,
                "rename_to_canonical": self.batch.rename_to_canonical,
                "trash_retention_days": self.batch.trash_retention_days,
                "auto_purge_trash": self.batch.auto_purge_trash,
            },
            "paths": {
                "data_dir": str(self.paths.data_dir),
                "config_file": str(self.paths.config_file),
            },
        }


_DEFAULTS: dict[str, dict[str, Any]] = {
    "general": {
        "output_dir": "~/Music/Harvested",
        "log_level_file": "DEBUG",
        "log_level_ui": "INFO",
        "first_run_notice_accepted": False,
    },
    "slskd": {
        "enabled": True,
        "url": "http://localhost:5000",
        "api_key_env": "SLSKD_API_KEY",
        "download_dir": "~/Music/slskd",
        "search_timeout_s": 25.0,
        "poll_interval_s": 1.5,
        "max_concurrent_downloads": 2,
        "verify_openapi": True,
        "stall_timeout_s": 120.0,
        "acquisition_mode": "best_available",
        "max_queue_length": 5,
        "p2p_timeout_s": 30.0,
    },
    "acoustid": {"api_key_env": "ACOUSTID_API_KEY", "rate_limit_per_s": 3.0, "cache_ttl_days": 90},
    "restoration": {"enabled": False, "mode": "conservative", "preserve_original": True},
    "ytdlp": {
        "binary": "yt-dlp",
        "format": "bestaudio[acodec^=opus]/bestaudio/best",
        "cookies_from_browser": "",
        "stall_timeout_s": 90.0,
        "total_timeout_s": 900.0,
    },
    "ffmpeg": {"binary": "ffmpeg", "probe_binary": "ffprobe", "transcode": "mp3-320"},
    "spectral": {"enabled": True, "excerpt_s": 60.0, "strict": False},
    "batch": {
        "skip_bitrate_kbps": 256,
        "playlist_cap": 50,
        "rename_to_canonical": False,
        "trash_retention_days": 7,
        "auto_purge_trash": False,
    },
    "processing": {"preset": DEFAULT_PRESET, "use_credits": True, "tag_threshold": TAG_THRESHOLD},
    "timeouts": {
        "probe_s": 30.0,
        "fpcalc_s": 60.0,
        "acoustid_s": 15.0,
        "coverart_s": 15.0,
        "transcode_s": 300.0,
        "ffprobe_s": 15.0,
        "spectral_s": 30.0,
        "health_s": 5.0,
        "kill_grace_s": 5.0,
    },
    "ui": {"refresh_hz": 8, "max_log_lines": 2000, "status_interval_s": 10.0},
}


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _set_dotted(mapping: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cursor = mapping
    for part in parts[:-1]:
        child = cursor.setdefault(part, {})
        if not isinstance(child, dict):
            raise ConfigError(f"Cannot override nested configuration key: {dotted_key}")
        cursor = child
    cursor[parts[-1]] = value


def _bool(value: Any, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigError(f"{name} must be a boolean")


def _int(value: Any, *, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer") from exc


def _float(value: Any, *, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number") from exc


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            loaded = tomllib.load(handle)
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration file {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"Configuration file {path} must contain a TOML table")
    return loaded


def _apply_environment(config: dict[str, Any], environ: Mapping[str, str]) -> None:
    converters: dict[str, tuple[str, Any]] = {
        "HARVESTER_OUTPUT_DIR": ("general.output_dir", str),
        "HARVESTER_LOG_LEVEL_FILE": ("general.log_level_file", str),
        "HARVESTER_LOG_LEVEL_UI": ("general.log_level_ui", str),
        "HARVESTER_SLSKD_ENABLED": (
            "slskd.enabled",
            lambda value: _bool(value, name="slskd.enabled"),
        ),
        "HARVESTER_SLSKD_URL": ("slskd.url", str),
        "HARVESTER_SLSKD_SEARCH_TIMEOUT_S": (
            "slskd.search_timeout_s",
            lambda value: _float(value, name="slskd.search_timeout_s"),
        ),
        "HARVESTER_YTDLP_BINARY": ("ytdlp.binary", str),
        "HARVESTER_FFMPEG_BINARY": ("ffmpeg.binary", str),
        "HARVESTER_FFPROBE_BINARY": ("ffmpeg.probe_binary", str),
        "HARVESTER_TRANSCODE": ("ffmpeg.transcode", str),
        "HARVESTER_SPECTRAL_ENABLED": (
            "spectral.enabled",
            lambda value: _bool(value, name="spectral.enabled"),
        ),
        "HARVESTER_BATCH_SKIP_BITRATE_KBPS": (
            "batch.skip_bitrate_kbps",
            lambda value: _int(value, name="batch.skip_bitrate_kbps"),
        ),
        "HARVESTER_FIRST_RUN_NOTICE_ACCEPTED": (
            "general.first_run_notice_accepted",
            lambda value: _bool(value, name="general.first_run_notice_accepted"),
        ),
    }
    for env_name, (key, converter) in converters.items():
        if env_name in environ:
            _set_dotted(config, key, converter(environ[env_name]))


def _build_config(
    raw: Mapping[str, Any],
    *,
    paths: AppPaths,
    config_file: Path,
) -> AppConfig:
    def section(name: str) -> Mapping[str, Any]:
        value = raw.get(name, {})
        if not isinstance(value, Mapping):
            raise ConfigError(f"Configuration section [{name}] must be a table")
        return value

    general = section("general")
    slskd = section("slskd")
    acoustid = section("acoustid")
    restoration = section("restoration")
    ytdlp = section("ytdlp")
    ffmpeg = section("ffmpeg")
    spectral = section("spectral")
    batch = section("batch")
    processing = section("processing")
    timeouts = section("timeouts")
    ui = section("ui")

    config = AppConfig(
        general=GeneralConfig(
            output_dir=Path(str(general.get("output_dir", "~/Music/Harvested"))).expanduser(),
            log_level_file=str(general.get("log_level_file", "DEBUG")).upper(),
            log_level_ui=str(general.get("log_level_ui", "INFO")).upper(),
            first_run_notice_accepted=_bool(
                general.get("first_run_notice_accepted", False),
                name="general.first_run_notice_accepted",
            ),
        ),
        slskd=SlskdConfig(
            enabled=_bool(slskd.get("enabled", True), name="slskd.enabled"),
            url=str(slskd.get("url", "http://localhost:5000")).rstrip("/"),
            api_key_env=str(slskd.get("api_key_env", "SLSKD_API_KEY")),
            download_dir=Path(str(slskd.get("download_dir", "~/Music/slskd"))).expanduser(),
            search_timeout_s=_float(
                slskd.get("search_timeout_s", 25.0), name="slskd.search_timeout_s"
            ),
            poll_interval_s=_float(slskd.get("poll_interval_s", 1.5), name="slskd.poll_interval_s"),
            max_concurrent_downloads=_int(
                slskd.get("max_concurrent_downloads", 2), name="slskd.max_concurrent_downloads"
            ),
            verify_openapi=_bool(slskd.get("verify_openapi", True), name="slskd.verify_openapi"),
            stall_timeout_s=_float(
                slskd.get("stall_timeout_s", 120.0), name="slskd.stall_timeout_s"
            ),
            acquisition_mode=str(slskd.get("acquisition_mode", "best_available")),
            max_queue_length=_int(slskd.get("max_queue_length", 5), name="slskd.max_queue_length"),
            p2p_timeout_s=_float(slskd.get("p2p_timeout_s", 30.0), name="slskd.p2p_timeout_s"),
        ),
        acoustid=AcoustidConfig(
            api_key_env=str(acoustid.get("api_key_env", "ACOUSTID_API_KEY")),
            rate_limit_per_s=_float(
                acoustid.get("rate_limit_per_s", 3.0), name="acoustid.rate_limit_per_s"
            ),
            cache_ttl_days=_int(acoustid.get("cache_ttl_days", 90), name="acoustid.cache_ttl_days"),
        ),
        restoration=RestorationSettings(
            enabled=_bool(restoration.get("enabled", False), name="restoration.enabled"),
            mode=str(restoration.get("mode", "conservative")),
            preserve_original=_bool(
                restoration.get("preserve_original", True), name="restoration.preserve_original"
            ),
        ),
        ytdlp=YtdlpConfig(
            binary=str(ytdlp.get("binary", "yt-dlp")),
            format=str(ytdlp.get("format", "bestaudio[acodec^=opus]/bestaudio/best")),
            cookies_from_browser=str(ytdlp.get("cookies_from_browser", "")),
            stall_timeout_s=_float(
                ytdlp.get("stall_timeout_s", 90.0), name="ytdlp.stall_timeout_s"
            ),
            total_timeout_s=_float(
                ytdlp.get("total_timeout_s", 900.0), name="ytdlp.total_timeout_s"
            ),
        ),
        ffmpeg=FfmpegConfig(
            binary=str(ffmpeg.get("binary", "ffmpeg")),
            probe_binary=str(ffmpeg.get("probe_binary", "ffprobe")),
            transcode=str(ffmpeg.get("transcode", "mp3-320")),
        ),
        spectral=SpectralConfig(
            enabled=_bool(spectral.get("enabled", True), name="spectral.enabled"),
            excerpt_s=_float(spectral.get("excerpt_s", 60.0), name="spectral.excerpt_s"),
            strict=_bool(spectral.get("strict", False), name="spectral.strict"),
        ),
        batch=BatchConfig(
            skip_bitrate_kbps=_int(
                batch.get("skip_bitrate_kbps", 256), name="batch.skip_bitrate_kbps"
            ),
            playlist_cap=_int(batch.get("playlist_cap", 50), name="batch.playlist_cap"),
            rename_to_canonical=_bool(
                batch.get("rename_to_canonical", False), name="batch.rename_to_canonical"
            ),
            trash_retention_days=_int(
                batch.get("trash_retention_days", 7), name="batch.trash_retention_days"
            ),
            auto_purge_trash=_bool(
                batch.get("auto_purge_trash", False), name="batch.auto_purge_trash"
            ),
        ),
        processing=ProcessingSettings(
            preset=str(processing.get("preset", DEFAULT_PRESET)),
            use_credits=_bool(processing.get("use_credits", True), name="processing.use_credits"),
            tag_threshold=_float(
                processing.get("tag_threshold", TAG_THRESHOLD), name="processing.tag_threshold"
            ),
        ),
        timeouts=TimeoutConfig(
            probe_s=_float(timeouts.get("probe_s", 30.0), name="timeouts.probe_s"),
            fpcalc_s=_float(timeouts.get("fpcalc_s", 60.0), name="timeouts.fpcalc_s"),
            acoustid_s=_float(timeouts.get("acoustid_s", 15.0), name="timeouts.acoustid_s"),
            coverart_s=_float(timeouts.get("coverart_s", 15.0), name="timeouts.coverart_s"),
            transcode_s=_float(timeouts.get("transcode_s", 300.0), name="timeouts.transcode_s"),
            ffprobe_s=_float(timeouts.get("ffprobe_s", 15.0), name="timeouts.ffprobe_s"),
            spectral_s=_float(timeouts.get("spectral_s", 30.0), name="timeouts.spectral_s"),
            health_s=_float(timeouts.get("health_s", 5.0), name="timeouts.health_s"),
            kill_grace_s=_float(timeouts.get("kill_grace_s", 5.0), name="timeouts.kill_grace_s"),
        ),
        ui=UiConfig(
            refresh_hz=_int(ui.get("refresh_hz", 8), name="ui.refresh_hz"),
            max_log_lines=_int(ui.get("max_log_lines", 2000), name="ui.max_log_lines"),
            status_interval_s=_float(
                ui.get("status_interval_s", 10.0), name="ui.status_interval_s"
            ),
        ),
        paths=AppPaths.from_base(paths.data_dir, config_file=config_file),
    )
    return config.validate()


def load_config(
    path: Path | str | None = None,
    *,
    cli_overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load config with precedence CLI > environment > TOML > defaults."""

    env = dict(os.environ if environ is None else environ)
    default_paths = AppPaths.default()
    data_dir = (
        Path(env["HARVESTER_DATA_DIR"]).expanduser()
        if env.get("HARVESTER_DATA_DIR")
        else default_paths.data_dir
    )
    config_file = Path(path or env.get("HARVESTER_CONFIG", data_dir / "config.toml")).expanduser()

    raw = _deep_merge(_DEFAULTS, {})
    if config_file.exists():
        raw = _deep_merge(raw, _load_toml(config_file))
    _apply_environment(raw, env)
    for key, value in (cli_overrides or {}).items():
        _set_dotted(raw, key, value)
    paths = AppPaths.from_base(data_dir, config_file=config_file)
    return _build_config(raw, paths=paths, config_file=config_file)


_FIRST_RUN_KEY = "first_run_notice_accepted"

ENV_FILE_NAME = ".env"
ENV_FILE_VAR = "OMNIRIP_ENV_FILE"


def _parse_env_file(text: str) -> dict[str, str]:
    """Parse a dotenv-style file into KEY=VALUE pairs (stdlib only)."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def env_file_candidates(config_path: Path | str | None = None) -> list[Path]:
    """Where a local ``.env`` may live, most specific first."""
    candidates: list[Path] = []
    explicit = os.environ.get(ENV_FILE_VAR, "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if config_path:
        candidates.append(Path(config_path).expanduser().parent / ENV_FILE_NAME)
    candidates.append(Path.cwd() / ENV_FILE_NAME)
    # Same data-dir resolution as `load_config` (HARVESTER_DATA_DIR override first).
    override = os.environ.get("HARVESTER_DATA_DIR", "").strip()
    data_dir = Path(override).expanduser() if override else AppPaths.default().data_dir
    candidates.append(data_dir / ENV_FILE_NAME)
    return candidates


def load_env_file(
    path: Path | str | None = None,
    *,
    config_path: Path | str | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> list[str]:
    """Load secrets from a local ``.env`` into the process environment.

    API keys come from environment variables only (NFR-6) — but a GUI launch
    (Terminal.app, double-click) does not inherit the shell's exports, so a
    gitignored ``.env`` file next to the config is read at startup. Real
    environment variables always win; nothing is ever written back to the file.

    Returns the names of the keys that were loaded (never their values).
    """
    target = environ if environ is not None else os.environ
    files = [Path(path).expanduser()] if path else env_file_candidates(config_path)
    loaded: list[str] = []
    for candidate in files:
        try:
            if not candidate.is_file():
                continue
            values = _parse_env_file(candidate.read_text(encoding="utf-8"))
        except OSError:
            continue
        # Most specific file first; whatever it lacks may come from the next one,
        # and an already-set (real) environment variable is never overwritten.
        for key, value in values.items():
            if value and not target.get(key):
                target[key] = value
                loaded.append(key)
    return loaded


def persist_first_run_acceptance(config: AppConfig) -> None:
    """Persist ``general.first_run_notice_accepted = true`` to the config file.

    A targeted write preserves the user's other settings and comments: the value is
    replaced in place when present, otherwise inserted under the ``[general]`` table
    (creating that table if the file does not exist or lacks it).
    """

    path = config.paths.config_file
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(rf"(?m)^(\s*{_FIRST_RUN_KEY}\s*=\s*)\S+")
        updated, count = pattern.subn(r"\g<1>true", text)
        if count:
            path.write_text(updated, encoding="utf-8")
            return
        updated = _insert_general_key(text, _FIRST_RUN_KEY, "true")
        path.write_text(updated, encoding="utf-8")
        return
    path.write_text(f"[general]\n{_FIRST_RUN_KEY} = true\n", encoding="utf-8")


def _insert_general_key(text: str, key: str, value: str) -> str:
    match = re.search(r"(?m)^\s*\[general\]\s*$", text)
    if match:
        insert_at = match.end()
        return text[:insert_at] + f"\n{key} = {value}\n" + text[insert_at:]
    if text and not text.endswith("\n"):
        text += "\n"
    return text + f"\n[general]\n{key} = {value}\n"


__all__ = [
    "AcoustidConfig",
    "AppConfig",
    "RestorationSettings",
    "BatchConfig",
    "FfmpegConfig",
    "GeneralConfig",
    "SlskdConfig",
    "SpectralConfig",
    "TimeoutConfig",
    "UiConfig",
    "YtdlpConfig",
    "load_config",
    "persist_first_run_acceptance",
]
