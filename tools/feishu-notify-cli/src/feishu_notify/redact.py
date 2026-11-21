from __future__ import annotations

import re
from typing import Any


def apply_redactions(text: str, patterns: list[str]) -> str:
    out = text
    for pat in patterns:
        if not pat:
            continue
        try:
            out = re.sub(pat, "[REDACTED]", out)
        except re.error:
            continue
    return out


def redact_payload(payload: dict[str, Any], patterns: list[str]) -> dict[str, Any]:
    if not patterns:
        return payload
    cloned = dict(payload)
    for key in ("title", "summary", "body_md"):
        val = cloned.get(key)
        if isinstance(val, str):
            cloned[key] = apply_redactions(val, patterns)
    fields = cloned.get("fields")
    if isinstance(fields, list):
        new_fields = []
        for row in fields:
            if not isinstance(row, dict):
                new_fields.append(row)
                continue
            nr = dict(row)
            for k in ("label", "value"):
                if isinstance(nr.get(k), str):
                    nr[k] = apply_redactions(nr[k], patterns)
            new_fields.append(nr)
        cloned["fields"] = new_fields
    return cloned