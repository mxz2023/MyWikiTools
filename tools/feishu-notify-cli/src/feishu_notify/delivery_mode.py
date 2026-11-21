from __future__ import annotations

from typing import Any, Literal

from feishu_notify.runs import get_binding

DeliveryOp = Literal["send", "patch"]

TERMINAL_SCENES = frozenset(
    {
        "agent.conclusion",
        "agent.partial",
        "agent.failure",
        "agent.cancelled",
    }
)


def progress_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = cfg.get("progress")
    return raw if isinstance(raw, dict) else {}


def hold_scene(cfg: dict[str, Any]) -> str:
    return str(progress_cfg(cfg).get("hold_scene") or "agent.progress")


def m2_enabled(cfg: dict[str, Any]) -> bool:
    return str(progress_cfg(cfg).get("mode") or "").lower() == "m2"


def resolve_delivery_op(
    envelope: dict[str, Any],
    cfg: dict[str, Any],
    *,
    store_path=None,
) -> tuple[DeliveryOp, str | None, str | None]:
    """
    Returns (op, message_id, reason).
    message_id set when op is patch.
    """
    delivery = envelope.get("delivery")
    if not isinstance(delivery, dict):
        delivery = {}

    explicit = delivery.get("mode", "auto")
    run_id = (envelope.get("context") or {}).get("run_id")
    run_id = run_id.strip() if isinstance(run_id, str) else None

    message_id = delivery.get("message_id")
    if isinstance(message_id, str):
        message_id = message_id.strip() or None
    else:
        message_id = None

    if explicit == "send":
        return "send", None, "delivery.mode=send"

    if explicit == "patch":
        if message_id:
            return "patch", message_id, "delivery.message_id"
        if run_id:
            binding = get_binding(run_id, store_path=store_path)
            if binding:
                return "patch", binding.message_id, "run_id binding"
        raise ValueError(
            "patch requires delivery.message_id or a stored binding for context.run_id"
        )

    scene = envelope.get("scene", "")
    if m2_enabled(cfg) and scene == hold_scene(cfg) and run_id:
        binding = get_binding(run_id, store_path=store_path)
        if binding:
            return "patch", binding.message_id, "m2 auto patch"
        return "send", None, "m2 auto first send"

    return "send", None, "default send"