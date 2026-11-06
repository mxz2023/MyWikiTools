"""Personal API Key -> bearer JWT; per-profile cache."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from garmin_personal.constants import TOKEN_CACHE_DIR


def _b64url_decode(segment: str) -> bytes:
    padding = 4 - len(segment) % 4
    if padding != 4:
        segment += "=" * padding
    return base64.urlsafe_b64decode(segment.encode("ascii"))


def jwt_expiry_seconds(token: str) -> int | None:
    """Return JWT exp (unix seconds) or None if not a JWT."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
        exp = payload.get("exp")
        if isinstance(exp, (int, float)):
            return int(exp)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        return None
    return None


@dataclass
class TokenData:
    access_token: str
    expires_at: int  # unix seconds

    def is_valid(self, *, skew_seconds: int = 3600) -> bool:
        now = int(time.time())
        return now + skew_seconds < self.expires_at


def cache_path(profile: str) -> Path:
    return TOKEN_CACHE_DIR / f"{profile}.json"


def load_token_cache(profile: str, api_key_fingerprint: str) -> TokenData | None:
    path = cache_path(profile)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if raw.get("api_key_fingerprint") != api_key_fingerprint:
        return None
    token = raw.get("access_token")
    exp = raw.get("expires_at")
    if not isinstance(token, str) or not isinstance(exp, int):
        return None
    return TokenData(access_token=token, expires_at=exp)


def save_token_cache(profile: str, api_key_fingerprint: str, data: TokenData) -> None:
    TOKEN_CACHE_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
    payload: dict[str, Any] = {
        "access_token": data.access_token,
        "expires_at": data.expires_at,
        "api_key_fingerprint": api_key_fingerprint,
    }
    path = cache_path(profile)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def api_key_fingerprint(api_key: str) -> str:
    import hashlib

    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


def fetch_token(client: httpx.Client, token_url: str, api_key: str) -> TokenData:
    """POST is default; Garmin FAQ shows POST with ApiKey header."""
    r = client.post(
        token_url,
        headers={"Authorization": f"ApiKey {api_key}"},
    )
    r.raise_for_status()
    body = (r.text or "").strip()
    if not body:
        raise ValueError("Empty token response")
    exp = jwt_expiry_seconds(body)
    if exp is None:
        # Fallback: 24h from now per FAQ
        exp = int(time.time()) + 24 * 3600
    return TokenData(access_token=body, expires_at=exp)


def get_valid_token(
    client: httpx.Client,
    profile: str,
    api_key: str,
    token_url: str,
    *,
    force_refresh: bool = False,
) -> TokenData:
    fp = api_key_fingerprint(api_key)
    if not force_refresh:
        cached = load_token_cache(profile, fp)
        if cached and cached.is_valid():
            return cached
    data = fetch_token(client, token_url, api_key)
    save_token_cache(profile, fp, data)
    return data
