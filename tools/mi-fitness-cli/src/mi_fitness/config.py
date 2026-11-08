"""Session paths and secure dirs."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from mi_fitness.constants import CONFIG_DIR, DATA_DIR, SESSION_FILE

from mifit.auth.session import Session, load_session, save_session


def ensure_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
    return CONFIG_DIR


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
    return DATA_DIR


def load_local_session() -> Session | None:
    ensure_config_dir()
    return load_session(SESSION_FILE)


def save_local_session(session: Session) -> Path:
    ensure_config_dir()
    return save_session(session, SESSION_FILE)


def import_session_file(source: Path) -> Session:
    raw = source.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("session file must be a JSON object")
    required = ("user_id", "c_user_id", "service_token", "ssecurity", "region", "created_at")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    session = Session(
        user_id=str(data["user_id"]),
        c_user_id=str(data["c_user_id"]),
        service_token=str(data["service_token"]),
        ssecurity=str(data["ssecurity"]),
        region=str(data.get("region") or "cn"),
        created_at=str(data["created_at"]),
        extra_cookies=dict(data.get("extra_cookies") or {}),
        pass_token=str(data.get("pass_token") or ""),
        device_id=str(data.get("device_id") or ""),
        renewed_at=data.get("renewed_at"),
    )
    if not session.is_valid():
        raise ValueError("session is missing service_token or user_id")
    save_local_session(session)
    return session


def logout_local() -> bool:
    if not SESSION_FILE.exists():
        return False
    try:
        SESSION_FILE.unlink()
    except OSError:
        return False
    return True


def env_pass_token_login() -> tuple[str, str] | None:
    uid = os.environ.get("MI_FITNESS_USER_ID", "").strip()
    pt = os.environ.get("MI_FITNESS_PASS_TOKEN", "").strip()
    if uid and pt:
        return uid, pt
    return None
