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
    _CODEX_REPLY_SCENES = frozenset({"agent.codex_reply"})
    if not title:
        # notify.plain 常仅 summary；勿把 summary 当 title，否则正文模板会重复一遍
        if scene == "notify.plain":
            title = ""
        else:
            title = summary[:48] or "通知"
    elif title == summary:
        title = ""
    fields = payload["fields"]
    body_md = (payload.get("body_md") or "").strip()
    card_parts: list[str] = []
    if summary and scene not in _CODEX_REPLY_SCENES and scene != "agent.progress":
        card_parts.append(f"**{summary}**")
    if fields:
        card_parts.extend(f"- **{f.get('label', '')}**：{f.get('value', '')}" for f in fields)
    if body_md:
        if len(body_md) <= 2000:
            card_parts.append(body_md)
        else:
            card_parts.append("（完整正文将以附件发送。）")
    card_markdown = "\n\n".join(card_parts)
    status_val = str(payload.get("status") or "info").lower()
    header_tpl = str(payload.get("header_template") or "").strip()
    if scene in _CODEX_REPLY_SCENES:
        if not header_tpl:
            if status_val == "success":
                header_tpl = "green"
            elif status_val in ("failed", "error"):
                header_tpl = "red"
            else:
                header_tpl = "blue"
        if not body_md:
            body_md = "_等待 Codex…_"
    else:
        header_tpl = header_tpl or str(manifest.get("header_template", "blue"))
    return {
        "title": title,
        "summary": summary,
        "status": payload.get("status") or "info",
        "body_md": body_md,
        "fields": fields,
        "actions": payload["actions"],
        "artifacts": payload["artifacts"],
        "card_markdown": card_markdown,
        "payload": payload,
        "context": ctx,
        "scene": envelope.get("scene"),
        "locale": envelope.get("locale", "zh_cn"),
        "header_template": header_tpl,
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