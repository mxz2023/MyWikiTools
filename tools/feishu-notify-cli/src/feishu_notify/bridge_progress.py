from __future__ import annotations

import sys
import time
from typing import Any

from feishu_notify.card_safe import card_safe_md, card_safe_summary
from feishu_notify.codex_stream import CodexActivityFeed
from feishu_notify.config import load_config
from feishu_notify.pipeline import process_send


def _truncate_title(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def codex_progress_opts(cfg: dict[str, Any]) -> dict[str, Any]:
    block = cfg.get("bridge") or {}
    if not isinstance(block, dict):
        return {}
    raw = block.get("codex")
    return raw if isinstance(raw, dict) else {}


def codex_live_progress_enabled(cfg: dict[str, Any]) -> bool:
    opts = codex_progress_opts(cfg)
    if "live_progress" in opts:
        return bool(opts.get("live_progress"))
    return True


def _progress_interval(cfg: dict[str, Any]) -> float:
    opts = codex_progress_opts(cfg)
    try:
        return max(1.0, float(opts.get("progress_min_interval_sec") or 2.5))
    except (TypeError, ValueError):
        return 2.5


def _progress_max_lines(cfg: dict[str, Any]) -> int:
    opts = codex_progress_opts(cfg)
    try:
        return max(4, int(opts.get("progress_max_lines") or 12))
    except (TypeError, ValueError):
        return 12


class FeishuCodexProgress:
    """M2 agent.codex_reply card while Codex exec runs (patch in place)."""

    def __init__(
        self,
        *,
        run_id: str,
        harness: str,
        prompt: str,
        cfg: dict[str, Any] | None = None,
    ) -> None:
        self.run_id = run_id
        self.harness = harness
        self.cfg = cfg or load_config()
        self.feed = CodexActivityFeed(max_lines=_progress_max_lines(self.cfg))
        self._started = time.monotonic()
        self._last_patch = 0.0
        self._interval = _progress_interval(self.cfg)
        self._prompt_text = prompt.strip()
        self._footer_md = ""

    def _header_template(self, status: str) -> str:
        if status == "success":
            return "green"
        if status == "failed":
            return "red"
        return "blue"

    def _ack_title(self) -> str:
        body = card_safe_summary(self._prompt_text)
        if not body:
            return "已收到"
        short = card_safe_summary(_truncate_title(body, 52))
        return f"已收到「{short}」"

    def _summary(self) -> str:
        elapsed = int(time.monotonic() - self._started)
        steps = self.feed.step_count
        if steps:
            return f"{elapsed}s · {steps} 步"
        return f"{elapsed}s"

    def _patch(self, *, title: str, status: str = "running", force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self._last_patch) < self._interval:
            return
        self._last_patch = now
        elapsed = now - self._started
        body = card_safe_md(self.feed.body_md(elapsed_sec=elapsed))
        if self._footer_md:
            sep = "\n\n---\n\n" if body else ""
            body = f"{body}{sep}{self._footer_md}" if body or self._footer_md else body
        envelope = {
            "fnp_version": 1,
            "scene": "agent.codex_reply",
            "route": "dm_self",
            "context": {"harness": self.harness, "run_id": self.run_id},
            "payload": {
                "title": card_safe_summary(title),
                "summary": card_safe_summary(self._summary()),
                "status": status,
                "body_md": body,
                "header_template": self._header_template(status),
            },
        }
        try:
            body = process_send(envelope, dry_run=False)
            op = body.get("delivery_op")
            mid = body.get("message_id")
            print(
                f"[bridge] progress {op} scene=agent.codex_reply message_id={mid}",
                file=sys.stderr,
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[bridge] progress patch failed: {exc}", file=sys.stderr, flush=True)

    def start(self) -> None:
        self.feed.push("📥 已交给 Codex")
        self._patch(title=self._ack_title(), force=True)

    def on_jsonl_line(self, line: str) -> None:
        desc = self.feed.consume_jsonl(line)
        if desc:
            self._patch(title=self._ack_title())

    def heartbeat(self) -> None:
        """Refresh card while waiting (long gaps between events)."""
        if self.feed.step_count == 0:
            self.feed.push("⌛ 等待模型响应…")
        self._patch(title=self._ack_title())

    def finish(self, *, ok: bool, reply: str | None = None) -> None:
        text = (reply or "").strip()
        if text:
            self._footer_md = card_safe_md(text)
        elif not ok:
            self._footer_md = "（未得到有效回复）"
        status = "success" if ok else "failed"
        self._patch(title=self._ack_title(), status=status, force=True)