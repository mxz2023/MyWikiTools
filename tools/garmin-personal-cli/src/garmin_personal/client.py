"""HTTP client with bearer auth and 401 -> refresh token."""

from __future__ import annotations

import json
from typing import Any

import httpx

from garmin_personal.auth import TokenData, get_valid_token


class GarminClient:
    def __init__(
        self,
        *,
        api_base: str,
        token_url: str,
        api_key: str,
        profile: str,
        timeout: float = 30.0,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.token_url = token_url
        self.api_key = api_key
        self.profile = profile
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._token: TokenData | None = None

    def access_token(self, *, refresh: bool = False) -> str:
        return self._bearer(refresh=refresh)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GarminClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _bearer(self, *, refresh: bool = False) -> str:
        self._token = get_valid_token(
            self._client, self.profile, self.api_key, self.token_url, force_refresh=refresh
        )
        return self._token.access_token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        allow_retry: bool = True,
    ) -> httpx.Response:
        if not path.startswith("/"):
            path = "/" + path
        url = self.api_base + path
        hdrs = {"Authorization": f"Bearer {self._bearer()}"}

        # Optional gzip for activity download per some docs — accept */* works

        if headers:
            hdrs.update(headers)
        r = self._client.request(method.upper(), url, params=params, headers=hdrs, content=content)
        if r.status_code == 401 and allow_retry:
            hdrs["Authorization"] = f"Bearer {self._bearer(refresh=True)}"
            r = self._client.request(method.upper(), url, params=params, headers=hdrs, content=content)
        return r


def http_exit_code(status: int) -> int:
    from garmin_personal.constants import EXIT_HTTP_4XX, EXIT_HTTP_5XX

    if 400 <= status < 500:
        return EXIT_HTTP_4XX
    if 500 <= status < 600:
        return EXIT_HTTP_5XX
    return 1


def decode_body(resp: httpx.Response) -> Any:
    if resp.status_code == 204 or not (resp.content or b""):
        return None
    ct = resp.headers.get("content-type", "")
    if "application/json" in ct or resp.text.strip().startswith(("{", "[")):
        try:
            return resp.json()
        except json.JSONDecodeError:
            pass
    return resp.text
