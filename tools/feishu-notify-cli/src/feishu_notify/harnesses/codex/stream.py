from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from typing import Any


def _short(text: str, width: int = 120) -> str:
    t = " ".join(str(text).split())
    if len(t) <= width:
        return t
    return textwrap.shorten(t, width=width, placeholder="…")


def describe_codex_event(obj: dict[str, Any]) -> str | None:
    """Turn one codex exec --json line into a user-facing activity line."""
    if not isinstance(obj, dict):
        return None
    etype = str(obj.get("type") or "")
    if etype == "turn.started":
        return "▶️ 开始推理"
    if etype == "turn.completed":
        return "✅ 本轮推理结束"
    if etype == "thread.started":
        return None
    if etype in ("turn.failed", "error"):
        msg = obj.get("message")
        if isinstance(msg, str):
            low = msg.lower()
            if "reconnecting" in low or "request timed out" in low:
                return f"⚠️ {_short(msg, 140)}（Codex 连模型 API 重试中）"
            return f"❌ {_short(msg, 160)}"
        err = obj.get("error")
        if isinstance(err, dict) and err.get("message"):
            return f"❌ {_short(str(err.get('message')), 160)}"
        return "❌ Codex 失败"

    if etype != "item.completed":
        return None

    item = obj.get("item")
    if not isinstance(item, dict):
        return None
    itype = str(item.get("type") or "")
    low = itype.lower()

    if low == "error":
        msg = str(item.get("message") or "")
        if "under-development" in msg.lower() or "suppress_unstable" in msg.lower():
            return None
        return f"⚠️ {_short(msg, 140)}"

    if low in ("agent_message", "message", "assistant_message", "agentmessage"):
        text = (
            item.get("text")
            or item.get("message")
            or item.get("content")
            or ""
        )
        if not isinstance(text, str):
            text = ""
        phase = str(item.get("phase") or "").lower()
        if phase == "final_answer" and text:
            return "✍️ 正在整理最终回复…"
        if phase == "commentary" and text:
            return f"💭 {_short(text, 100)}"
        if text and phase not in ("final_answer",):
            return f"💭 {_short(text, 100)}"
        if text:
            return f"💬 {_short(text, 80)}"
        return None

    if low == "reasoning":
        return "🧠 深度思考中…"

    if low == "extension":
        kind = str(item.get("kind") or "extension")
        if kind == "web.search":
            action = item.get("action") if isinstance(item.get("action"), dict) else {}
            query = str(item.get("query") or action.get("query") or "").strip()
            if query:
                return f"🔍 搜索：{_short(query, 80)}"
            return "🔍 联网搜索…"
        return f"🔌 {kind}"

    if "command" in low or low in (
        "command_execution",
        "shell_command",
        "exec_command",
        "local_shell",
    ):
        cmd = (
            item.get("command")
            or item.get("cmd")
            or item.get("text")
            or item.get("input")
            or ""
        )
        if cmd:
            return f"🛠 命令：`{_short(str(cmd), 90)}`"
        return "🛠 执行命令…"

    if "tool" in low or low.startswith("mcp") or low in ("function_call", "custom_tool"):
        name = item.get("name") or item.get("tool") or item.get("server") or itype
        return f"🔧 工具：{_short(str(name), 60)}"

    if "skill" in low:
        name = item.get("name") or item.get("skill") or "skill"
        return f"📎 技能：{_short(str(name), 60)}"

    if itype:
        return f"· {itype}"
    return None


@dataclass
class CodexActivityFeed:
    max_lines: int = 12
    lines: list[str] = field(default_factory=list)
    step_count: int = 0

    def push(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        self.step_count += 1
        if self.lines and self.lines[-1] == line:
            return
        low = line.lower()
        if "reconnecting" in low and self.lines:
            prev = self.lines[-1].lower()
            if "reconnecting" in prev or "重试中" in self.lines[-1]:
                self.lines[-1] = line
                return
        self.lines.append(line)
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines :]

    def consume_jsonl(self, raw: str) -> str | None:
        raw = raw.strip()
        if not raw.startswith("{"):
            return None
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return None
        desc = describe_codex_event(obj)
        if desc:
            self.push(desc)
        return desc

    def body_md(self, *, elapsed_sec: float | None = None) -> str:
        del elapsed_sec  # shown via card payload.summary, not body copy
        if not self.lines:
            return "等待 Codex 响应…"
        return "\n".join(f"- {ln}" for ln in self.lines)