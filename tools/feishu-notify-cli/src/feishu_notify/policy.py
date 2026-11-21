from __future__ import annotations

from typing import Any, Literal


def has_callback_actions(payload: dict[str, Any]) -> bool:
    for action in payload.get("actions") or []:
        if isinstance(action, dict) and action.get("kind") == "callback":
            return True
    return False


def resolve_identity(
    envelope: dict[str, Any],
    manifest: dict[str, Any],
    cfg: dict[str, Any],
) -> Literal["bot", "user"]:
    if envelope.get("identity") in ("bot", "user"):
        return envelope["identity"]

    if has_callback_actions(envelope.get("payload") or {}):
        return "bot"

    manifest_id = manifest.get("default_identity")
    if manifest_id in ("bot", "user"):
        return manifest_id

    default = cfg.get("default_identity", "bot")
    return "bot" if default not in ("bot", "user") else default


def resolve_format(
    envelope: dict[str, Any],
    manifest: dict[str, Any],
) -> Literal["text", "card"]:
    fmt = envelope.get("format", "auto")
    payload = envelope.get("payload") or {}

    if fmt == "text":
        return "text"
    if fmt == "card":
        return "card"

    if has_callback_actions(payload):
        return "card"

    scene_default = manifest.get("default_format", "auto")
    if scene_default in ("text", "card"):
        return scene_default

    scene_id = envelope.get("scene", "")
    status = payload.get("status")
    if scene_id in ("agent.failure", "agent.alert", "agent.approval") or status == "failed":
        return "card"

    return "card"