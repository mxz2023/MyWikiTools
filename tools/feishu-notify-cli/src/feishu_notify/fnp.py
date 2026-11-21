from __future__ import annotations

from typing import Any

from feishu_notify.constants import FNP_VERSION, VALID_FORMATS, VALID_IDENTITIES, VALID_STATUSES


class FnpValidationError(ValueError):
    pass


def _require_str(obj: dict[str, Any], key: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str) or not val.strip():
        raise FnpValidationError(f"payload.{key} must be a non-empty string")
    return val.strip()


def validate_envelope(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise FnpValidationError("envelope must be a JSON object")
    version = raw.get("fnp_version")
    if version != FNP_VERSION:
        raise FnpValidationError(f"fnp_version must be {FNP_VERSION}")

    scene = raw.get("scene")
    if not isinstance(scene, str) or not scene.strip():
        raise FnpValidationError("scene is required")

    fmt = raw.get("format", "auto")
    if fmt not in VALID_FORMATS:
        raise FnpValidationError(f"invalid format: {fmt}")

    identity = raw.get("identity", "auto")
    if identity not in VALID_IDENTITIES:
        raise FnpValidationError(f"invalid identity: {identity}")

    route = raw.get("route", "dm_self")
    if not isinstance(route, str) or not route.strip():
        raise FnpValidationError("route must be a string")

    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise FnpValidationError("payload must be an object")

    status = payload.get("status")
    if status is not None and status not in VALID_STATUSES:
        raise FnpValidationError(f"invalid payload.status: {status}")

    for action in payload.get("actions") or []:
        if not isinstance(action, dict):
            raise FnpValidationError("actions[] must be objects")
        kind = action.get("kind")
        if kind not in ("url", "callback"):
            raise FnpValidationError("action.kind must be url or callback")

    delivery = raw.get("delivery")
    if delivery is not None and not isinstance(delivery, dict):
        raise FnpValidationError("delivery must be an object")
    if isinstance(delivery, dict):
        mode = delivery.get("mode", "auto")
        if mode not in ("auto", "send", "patch"):
            raise FnpValidationError("delivery.mode must be auto|send|patch")

    return {
        "fnp_version": FNP_VERSION,
        "scene": scene.strip(),
        "scene_version": str(raw.get("scene_version") or "1.0"),
        "format": fmt,
        "identity": identity,
        "route": route.strip(),
        "locale": str(raw.get("locale") or "zh_cn"),
        "payload": payload,
        "context": raw.get("context") if isinstance(raw.get("context"), dict) else {},
        "delivery": delivery if isinstance(delivery, dict) else {},
    }


def validate_payload_for_scene(manifest: dict[str, Any], payload: dict[str, Any]) -> None:
    required = manifest.get("required_fields") or []
    for field in required:
        val = payload.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise FnpValidationError(f"payload.{field} is required for scene {manifest.get('id')}")