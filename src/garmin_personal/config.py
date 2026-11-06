"""TOML config: profiles and default_profile under ~/.config/garmin-personal/."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import tomllib
import tomli_w

from garmin_personal.constants import CONFIG_DIR, CONFIG_FILE, DEFAULT_API_BASE, DEFAULT_TOKEN_PATH

_DEFAULT_PROFILE = "default"


def _secure_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=0o700, exist_ok=True)


def _chmod_config_file(path: Path) -> None:
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def config_path() -> Path:
    return CONFIG_FILE


def load_raw_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {"default_profile": _DEFAULT_PROFILE, "profiles": {}}
    data = CONFIG_FILE.read_bytes()
    return tomllib.loads(data.decode("utf-8"))


def save_raw_config(cfg: dict[str, Any]) -> None:
    _secure_dir(CONFIG_DIR)
    with CONFIG_FILE.open("wb") as f:
        tomli_w.dump(cfg, f)
    _chmod_config_file(CONFIG_FILE)


def get_profile_names() -> list[str]:
    cfg = load_raw_config()
    return sorted(cfg.get("profiles", {}).keys())


def get_default_profile_name() -> str:
    cfg = load_raw_config()
    names = list(cfg.get("profiles", {}).keys())
    env = os.environ.get("GARMIN_PROFILE")
    if env and env in names:
        return env
    if env:
        return env
    chosen = cfg.get("default_profile")
    if isinstance(chosen, str) and chosen in names:
        return chosen
    if names:
        return names[0]
    return str(chosen or _DEFAULT_PROFILE)


def resolve_profile(profile: str | None) -> str:
    if profile:
        return profile
    return get_default_profile_name()


def get_profile_config(name: str) -> dict[str, Any]:
    cfg = load_raw_config()
    prof = cfg.get("profiles", {}).get(name)
    if not isinstance(prof, dict):
        return {}
    return prof


def set_profile(
    name: str,
    api_key: str,
    *,
    api_base: str | None = None,
    token_url: str | None = None,
) -> None:
    cfg = load_raw_config()
    cfg.setdefault("profiles", {})
    entry: dict[str, Any] = {"api_key": api_key}
    if api_base is not None:
        entry["api_base"] = api_base
    if token_url is not None:
        entry["token_url"] = token_url
    cfg["profiles"][name] = entry
    save_raw_config(cfg)


def remove_profile(name: str) -> None:
    cfg = load_raw_config()
    profiles = cfg.get("profiles", {})
    if name in profiles:
        del profiles[name]
    if cfg.get("default_profile") == name:
        remaining = sorted(profiles.keys())
        cfg["default_profile"] = remaining[0] if remaining else _DEFAULT_PROFILE
    save_raw_config(cfg)


def set_default_profile(name: str) -> None:
    cfg = load_raw_config()
    if name not in cfg.get("profiles", {}):
        raise KeyError(f"Unknown profile: {name}")
    cfg["default_profile"] = name
    save_raw_config(cfg)


def api_base_for_profile(name: str) -> str:
    prof = get_profile_config(name)
    return str(prof.get("api_base") or os.environ.get("GARMIN_API_BASE") or DEFAULT_API_BASE).rstrip(
        "/"
    )


def token_url_for_profile(name: str) -> str:
    prof = get_profile_config(name)
    if prof.get("token_url"):
        return str(prof["token_url"])
    base = api_base_for_profile(name)
    env = os.environ.get("GARMIN_TOKEN_URL")
    if env:
        return env
    return base + DEFAULT_TOKEN_PATH
