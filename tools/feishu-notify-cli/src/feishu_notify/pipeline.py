from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_notify.config import load_config
from feishu_notify.deliver import DeliveryError, deliver, deliver_patch, extract_message_id
from feishu_notify.delivery_mode import (
    TERMINAL_SCENES,
    hold_scene,
    m2_enabled,
    resolve_delivery_op,
)
from feishu_notify.fnp import FnpValidationError, validate_envelope, validate_payload_for_scene
from feishu_notify.policy import resolve_format, resolve_identity
from feishu_notify.redact import redact_payload
from feishu_notify.render import render_message
from feishu_notify.runs import RunBinding, clear_binding, get_binding, put_binding
from feishu_notify.scenes import load_manifest


def _require_run_id_if_needed(envelope: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    from feishu_notify.delivery_mode import progress_cfg

    scene = envelope.get("scene", "")
    if not m2_enabled(cfg):
        return _run_id(envelope)
    if not progress_cfg(cfg).get("require_run_id"):
        return _run_id(envelope)
    if scene == hold_scene(cfg):
        rid = _run_id(envelope)
        if not rid:
            raise FnpValidationError(
                f"context.run_id is required for {scene} when progress.mode=m2"
            )
        return rid
    return _run_id(envelope)


def _run_id(envelope: dict[str, Any]) -> str | None:
    raw = (envelope.get("context") or {}).get("run_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def process_notify(
    raw: dict[str, Any],
    *,
    config_path: Path | None = None,
    store_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    envelope = validate_envelope(raw)
    manifest = load_manifest(envelope["scene"], envelope["scene_version"])
    validate_payload_for_scene(manifest, envelope["payload"])

    cfg = load_config(config_path)
    run_id = _require_run_id_if_needed(envelope, cfg)

    patterns = list(cfg.get("redact_patterns") or [])
    envelope = dict(envelope)
    envelope["payload"] = redact_payload(envelope["payload"], patterns)

    identity = resolve_identity(envelope, manifest, cfg)
    fmt = resolve_format(envelope, manifest)

    try:
        op, patch_message_id, op_reason = resolve_delivery_op(
            envelope, cfg, store_path=store_path
        )
    except ValueError as exc:
        raise FnpValidationError(str(exc)) from exc

    if op == "patch" and fmt != "card":
        raise FnpValidationError("patch requires card format; use format=card or scene agent.progress")

    rendered = render_message(envelope, fmt)

    if op == "patch":
        assert patch_message_id
        patch_identity = identity
        if run_id:
            binding = get_binding(run_id, store_path=store_path)
            if binding:
                patch_identity = binding.identity
        body = deliver_patch(
            message_id=patch_message_id,
            identity=patch_identity,
            rendered=rendered,
            dry_run=dry_run,
        )
        if run_id and not dry_run:
            put_binding(
                RunBinding(
                    run_id=run_id,
                    message_id=patch_message_id,
                    identity=patch_identity,
                    route=envelope.get("route", "dm_self"),
                    scene=envelope.get("scene", hold_scene(cfg)),
                    updated_at=datetime.now(timezone.utc).isoformat(),
                ),
                store_path=store_path,
            )
        out = {
            "ok": body.get("ok", True),
            "scene": envelope["scene"],
            "format_used": fmt,
            "delivery_op": "patch",
            "delivery_reason": op_reason,
            "run_id": run_id,
            **body,
        }
        return out

    body = deliver(
        cfg=cfg,
        route_name=envelope["route"],
        identity=identity,
        rendered=rendered,
        payload=envelope["payload"],
        dry_run=dry_run,
        max_body_chars=int(cfg.get("max_body_chars") or 12000),
    )

    message_id = body.get("message_id")
    if not message_id and dry_run:
        message_id = "om_dry_run"

    scene = envelope.get("scene", "")
    if run_id and message_id and scene == hold_scene(cfg) and m2_enabled(cfg):
        if not dry_run or str(message_id).startswith("om_"):
            put_binding(
                RunBinding(
                    run_id=run_id,
                    message_id=str(message_id),
                    identity=identity,
                    route=envelope.get("route", "dm_self"),
                    scene=scene,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                ),
                store_path=store_path,
            )
            body["run_bound"] = True

    if run_id and scene in TERMINAL_SCENES and not dry_run:
        body["run_cleared"] = clear_binding(run_id, store_path=store_path)

    return {
        "ok": body.get("ok", True),
        "scene": envelope["scene"],
        "format_used": fmt,
        "delivery_op": "send",
        "delivery_reason": op_reason,
        "run_id": run_id,
        **body,
    }


# Backward-compatible alias
process_send = process_notify