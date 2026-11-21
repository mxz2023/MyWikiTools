from __future__ import annotations

import json
from typing import Any, Literal

from jinja2 import Environment, StrictUndefined

from feishu_notify.scenes import load_manifest, manifest_template_path


def _jinja_env() -> Environment:
    return Environment(undefined=StrictUndefined, autoescape=False)


def _render_context(envelope: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    payload = dict(envelope.get("payload") or {})
    ctx = dict(envelope.get("context") or {})
    payload["fields"] = payload.get("fields") or []
    payload["actions"] = payload.get("actions") or []
    payload["artifacts"] = payload.get("artifacts") or []
    title = (payload.get("title") or "").strip()
    summary = (payload.get("summary") or "").strip()
    scene = envelope.get("scene") or ""
    if not title:
        # notify.plain 常仅 summary；勿把 summary 当 title，否则正文模板会重复一遍
        if scene == "notify.plain":
            title = ""
        else:
            title = summary[:48] or "通知"
    elif title == summary:
        title = ""
    return {
        "title": title,
        "summary": summary,
        "status": payload.get("status") or "info",
        "body_md": payload.get("body_md") or "",
        "fields": payload["fields"],
        "actions": payload["actions"],
        "artifacts": payload["artifacts"],
        "payload": payload,
        "context": ctx,
        "scene": envelope.get("scene"),
        "locale": envelope.get("locale", "zh_cn"),
        "header_template": manifest.get("header_template", "blue"),
        "scene_description": manifest.get("description", ""),
    }


def render_message(
    envelope: dict[str, Any],
    fmt: Literal["text", "card"],
) -> dict[str, Any]:
    scene_id = envelope["scene"]
    manifest = load_manifest(scene_id, envelope.get("scene_version", "1.0"))
    render_ctx = _render_context(envelope, manifest)
    env = _jinja_env()

    if fmt == "text":
        tpl_path = manifest_template_path(manifest, "text")
        text = env.from_string(tpl_path.read_text(encoding="utf-8")).render(**render_ctx)
        return {"format": "text", "markdown": text.strip()}

    card_path = manifest_template_path(manifest, "card")
    card_raw = env.from_string(card_path.read_text(encoding="utf-8")).render(**render_ctx)
    card = json.loads(card_raw)
    return {"format": "card", "card": card}