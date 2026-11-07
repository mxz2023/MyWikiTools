"""Unit tests for auth token and 401 retry."""

from __future__ import annotations

import base64
import json
import time

import httpx
import pytest
import respx

from garmin_personal.auth import (
    TokenData,
    api_key_fingerprint,
    fetch_token,
    get_valid_token,
    jwt_expiry_seconds,
    save_token_cache,
)
from garmin_personal.client import GarminClient


def _jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"


def test_jwt_exp():
    exp = int(time.time()) + 3600
    tok = _jwt({"exp": exp})
    assert jwt_expiry_seconds(tok) == exp


@respx.mock
def test_fetch_token():
    jwt = _jwt({"exp": int(time.time()) + 7200})
    route = respx.post("https://example.com/token").mock(return_value=httpx.Response(200, text=jwt))
    r = httpx.Client()
    td = fetch_token(r, "https://example.com/token", "secret-key")
    assert td.access_token == jwt
    assert route.called


@respx.mock
def test_client_retries_401():
    """401 triggers token refresh and second GET succeeds."""
    expires = int(time.time()) + 7200
    jwt1 = _jwt({"exp": expires})
    jwt2 = _jwt({"exp": expires + 100})
    respx.post("https://api.example.com/personalapitoken-service/personal-api/personal-api-key/token").mock(
        side_effect=[
            httpx.Response(200, text=jwt1),
            httpx.Response(200, text=jwt2),
        ]
    )
    gw = respx.get("https://api.example.com/protected").mock(
        side_effect=[
            httpx.Response(401, text="unauthorized"),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    c = GarminClient(
        api_base="https://api.example.com",
        token_url="https://api.example.com/personalapitoken-service/personal-api/personal-api-key/token",
        api_key="k",
        profile="p",
    )
    try:
        r = c.request("GET", "/protected")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        assert gw.call_count == 2
    finally:
        c.close()


def test_cache_reuse(tmp_path, monkeypatch):
    monkeypatch.setattr("garmin_personal.auth.TOKEN_CACHE_DIR", tmp_path)
    fp = api_key_fingerprint("key")
    exp = int(time.time()) + 10_000
    jwt = _jwt({"exp": exp})
    save_token_cache("u1", fp, TokenData(access_token=jwt, expires_at=exp))
    client = httpx.Client()
    td = get_valid_token(
        client,
        "u1",
        "key",
        "https://invalid.example/no-network",
        force_refresh=False,
    )
    assert td.access_token == jwt
    client.close()
