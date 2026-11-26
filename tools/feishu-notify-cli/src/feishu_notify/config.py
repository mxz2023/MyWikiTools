from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from feishu_notify.constants import CONFIG_DIR, CONFIG_FILE

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "default_route": "dm_self",
    "default_identity": "bot",
    "max_body_chars": 12000,
    "progress": {
        "mode": "m2",
        "hold_scene": "agent.codex_reply",
        "require_run_id": True,
    },
    "routes": {
        "dm_self": {
            "type": "bot_p2p",
            "user_id": "",
        },
    },
    "redact_patterns": [],
    "bridge": {
        "default_harness": "codex",
        "workspace": "",
        "agent_timeout_sec": 3600,
        "notify": True,
        "shell_cmd": 'echo "fnotify bridge (shell): {prompt}"',
        "harnesses": {},
        "codex": {
            "executable": "",
            "skip_git_repo_check": True,
            "approve_for_me": True,
            "json_events": True,
            "thread_name": "Feishu Bot",
            "model": "",
            "profile": "",
            "config_overrides": [],
            "live_progress": True,
            "progress_min_interval_sec": 2.5,
            "progress_max_lines": 12,
        },
    },
}


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or CONFIG_FILE
    if not cfg_path.is_file():
        merged = dict(DEFAULT_CONFIG)
        merged["routes"] = {k: dict(v) for k, v in DEFAULT_CONFIG["routes"].items()}
        return merged
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(
        {k: v for k, v in data.items() if k not in ("routes", "progress", "bridge")}
    )
    progress = dict(DEFAULT_CONFIG.get("progress") or {})
    if isinstance(data.get("progress"), dict):
        progress.update(data["progress"])
    merged["progress"] = progress
    bridge = dict(DEFAULT_CONFIG.get("bridge") or {})
    if isinstance(data.get("bridge"), dict):
        bridge.update({k: v for k, v in data["bridge"].items() if k not in ("harnesses", "codex")})
        harnesses = dict(bridge.get("harnesses") or {})
        if isinstance(data["bridge"].get("harnesses"), dict):
            harnesses.update(data["bridge"]["harnesses"])
        bridge["harnesses"] = harnesses
        codex = dict(bridge.get("codex") or {})
        if isinstance(data["bridge"].get("codex"), dict):
            codex.update(data["bridge"]["codex"])
        overrides = codex.get("config_overrides")
        if not isinstance(overrides, list):
            codex["config_overrides"] = list(
                DEFAULT_CONFIG["bridge"]["codex"].get("config_overrides") or []
            )
        bridge["codex"] = codex
    merged["bridge"] = bridge
    routes = dict(DEFAULT_CONFIG["routes"])
    if isinstance(data.get("routes"), dict):
        for name, route in data["routes"].items():
            if isinstance(route, dict):
                base = dict(routes.get(name, {}))
                base.update(route)
                routes[name] = base
    merged["routes"] = routes
    return merged


def init_config() -> Path:
    ensure_config_dir()
    if CONFIG_FILE.is_file():
        return CONFIG_FILE
    text = yaml.safe_dump(DEFAULT_CONFIG, allow_unicode=True, sort_keys=False)
    CONFIG_FILE.write_text(text, encoding="utf-8")
    return CONFIG_FILE


def save_dm_self_user_id(user_id: str, *, path: Path | None = None) -> Path:
    """Write routes.dm_self.user_id and merge with defaults."""
    cfg_path = path or CONFIG_FILE
    ensure_config_dir()
    cfg = load_config(cfg_path)
    routes = dict(cfg.get("routes") or {})
    dm = dict(routes.get("dm_self") or DEFAULT_CONFIG["routes"]["dm_self"])
    dm["user_id"] = user_id.strip()
    routes["dm_self"] = dm
    cfg["routes"] = routes
    text = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)
    cfg_path.write_text(text, encoding="utf-8")
    return cfg_path


def resolve_route(cfg: dict[str, Any], route_name: str) -> dict[str, Any]:
    routes = cfg.get("routes") or {}
    route = routes.get(route_name)
    if not isinstance(route, dict):
        raise ValueError(f"unknown route alias: {route_name}")
    return route