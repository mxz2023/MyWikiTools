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


def describe_cursor_event(obj: dict[str, Any]) -> str | None:
    if not isinstance(obj, dict):
        return None
    etype = str(obj.get("type") or "")
    subtype = str(obj.get("subtype") or "")

    if etype == "system" and subtype == "init":
        model = obj.get("model")
        if isinstance(model, str) and model.strip():
            return f"🤖 {model.strip()}"
        return "▶️ Cursor Agent 就绪"

    if etype == "assistant":
        msg = obj.get("message")
        if isinstance(msg, dict):
            parts = msg.get("content")
            if isinstance(parts, list):
                for part in parts:
                    if not isinstance(part, dict):
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        return f"💬 {_short(text.strip(), 100)}"
        return None

    if etype == "tool_call" and subtype == "started":
        tc = obj.get("tool_call")
        if isinstance(tc, dict):
            name = _tool_name(tc)
            if name:
                return f"🔧 {name}"
        return "🔧 调用工具中…"

    if etype == "tool_call" and subtype == "completed":
        return "✅ 工具完成"

    if etype == "result":
        if subtype == "success":
            return "✅ 本轮结束"
        return "❌ 运行失败"

    return None


def _tool_name(tc: dict[str, Any]) -> str | None:
    for key in ("shellToolCall", "readToolCall", "writeToolCall", "function"):
        block = tc.get(key)
        if isinstance(block, dict):
            if key == "function":
                name = block.get("name")
                return str(name) if name else "function"
            return key.replace("ToolCall", "")
    return None


@dataclass
class CursorActivityFeed:
    max_lines: int = 12
    _lines: list[str] = field(default_factory=list)
    step_count: int = 0

    def push(self, line: str) -> None:
        text = (line or "").strip()
        if not text:
            return
        if self._lines and self._lines[-1] == text:
            return
        self._lines.append(text)
        self.step_count += 1
        if len(self._lines) > self.max_lines:
            self._lines = self._lines[-self.max_lines :]

    def consume_jsonl(self, line: str) -> str | None:
        line = line.strip()
        if not line.startswith("{"):
            return None
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None
        desc = describe_cursor_event(obj)
        if desc:
            self.push(desc)
        return desc

    def body_md(self, *, elapsed_sec: float) -> str:
        if not self._lines:
            return f"_已运行 {int(elapsed_sec)}s…_"
        return "\n".join(f"- {ln}" for ln in self._lines)