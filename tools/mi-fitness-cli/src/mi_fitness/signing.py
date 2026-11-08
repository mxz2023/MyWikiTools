# Portions adapted from Mi-Fitness-Sync / mifit (MIT). See THIRD_PARTY_NOTICES.md.
# Runtime signing uses the `mifit` package; this module exists for unit tests only.

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct
import time
from urllib.parse import urlparse

_RC4_DISCARD = 1024
_MINUTE_MS = 60_000


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value)


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


class _Rc4:
    def __init__(self, key: bytes) -> None:
        if not key:
            raise ValueError("RC4 key must not be empty.")
        state = list(range(256))
        j = 0
        for i in range(256):
            j = (j + state[i] + key[i % len(key)]) & 0xFF
            state[i], state[j] = state[j], state[i]
        self._state = state
        self._i = 0
        self._j = 0
        self.apply(bytes(_RC4_DISCARD))

    def apply(self, data: bytes) -> bytes:
        state = self._state
        i, j = self._i, self._j
        out = bytearray(len(data))
        for index, value in enumerate(data):
            i = (i + 1) & 0xFF
            j = (j + state[i]) & 0xFF
            state[i], state[j] = state[j], state[i]
            out[index] = value ^ state[(state[i] + state[j]) & 0xFF]
        self._i, self._j = i, j
        return bytes(out)


def rc4_crypt(key: bytes, data: bytes) -> bytes:
    return _Rc4(key).apply(data)


def generate_nonce(time_diff_ms: int = 0) -> str:
    now_ms = int(time.time() * 1000) + time_diff_ms
    payload = os.urandom(8) + struct.pack(">i", now_ms // _MINUTE_MS)
    return _b64encode(payload)


def signed_nonce(ssecurity: str, nonce: str) -> str:
    digest = hashlib.sha256(_b64decode(ssecurity) + _b64decode(nonce)).digest()
    return _b64encode(digest)


def build_signature(
    method: str, path: str, params: dict[str, str], signed_nonce_value: str
) -> str:
    parts = [method.upper(), urlparse(path).path]
    parts.extend(f"{key}={params[key]}" for key in sorted(params))
    parts.append(signed_nonce_value)
    return _b64encode(hashlib.sha1("&".join(parts).encode("utf-8")).digest())


def encrypt_query_params(
    *,
    method: str,
    path: str,
    params: dict[str, str],
    nonce: str,
    ssecurity: str,
    signature_path: str | None = None,
) -> dict[str, str]:
    signed_nonce_value = signed_nonce(ssecurity, nonce)
    sign_path = signature_path or path
    plain = {key: value for key, value in params.items() if key and value}
    plain["rc4_hash__"] = build_signature(method, sign_path, plain, signed_nonce_value)
    cipher = _Rc4(_b64decode(signed_nonce_value))
    encrypted = {
        key: _b64encode(cipher.apply(value.encode("utf-8")))
        for key, value in sorted(plain.items())
    }
    encrypted["signature"] = build_signature(method, sign_path, encrypted, signed_nonce_value)
    encrypted["_nonce"] = nonce
    return encrypted


def decrypt_response_payload(body: str, nonce: str, ssecurity: str) -> dict:
    key = _b64decode(signed_nonce(ssecurity, nonce))
    payload = json.loads(rc4_crypt(key, _b64decode(body)).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Mi Fitness response payload was not a JSON object.")
    return payload
