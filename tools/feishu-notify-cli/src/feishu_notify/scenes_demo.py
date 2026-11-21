from __future__ import annotations

import time
from typing import Any

from feishu_notify.pipeline import process_send
from feishu_notify.scenes import list_scenes

# 各 scene 示例 payload（字段满足 manifest required_fields）
DEMO_PAYLOADS: dict[str, dict[str, Any]] = {
    "notify.plain": {
        "summary": "【样式预览】通用纯通知 notify.plain",
    },
    "agent.ack": {
        "title": "已接单",
        "summary": "【样式预览】agent.ack — 任务已开始",
        "status": "running",
        "fields": [{"label": "工作区", "value": "MyWikiTools"}],
    },
    "agent.progress": {
        "title": "同步中",
        "summary": "【样式预览】agent.progress — 5/10",
        "status": "running",
        "fields": [{"label": "阶段", "value": "写入数据库"}],
    },
    "agent.conclusion": {
        "title": "完成",
        "summary": "【样式预览】agent.conclusion — 全部成功",
        "status": "success",
        "fields": [{"label": "耗时", "value": "3m"}],
    },
    "agent.partial": {
        "title": "部分完成",
        "summary": "【样式预览】agent.partial — 8/10",
        "status": "partial",
    },
    "agent.failure": {
        "title": "失败",
        "summary": "【样式预览】agent.failure — 示例错误",
        "status": "failed",
    },
    "agent.cancelled": {
        "title": "已取消",
        "summary": "【样式预览】agent.cancelled",
        "status": "cancelled",
    },
    "agent.alert": {
        "title": "注意",
        "summary": "【样式预览】agent.alert — 需尽快查看",
        "status": "info",
    },
    "agent.approval": {
        "title": "待确认",
        "summary": "【样式预览】agent.approval — 点按钮示意",
        "actions": [
            {"id": "ok", "label": "确认", "kind": "callback", "value": {"op": "approve", "demo": True}},
            {"id": "no", "label": "取消", "kind": "callback", "value": {"op": "deny", "demo": True}},
        ],
    },
    "agent.report": {
        "title": "今日汇报",
        "summary": "【样式预览】agent.report",
        "fields": [
            {"label": "完成", "value": "5 项"},
            {"label": "进行中", "value": "2 项"},
        ],
    },
    "agent.link_digest": {
        "title": "链接摘要",
        "summary": "【样式预览】agent.link_digest",
        "actions": [
            {"id": "doc", "label": "打开文档", "kind": "url", "href": "https://open.feishu.cn/"},
        ],
    },
    "agent.artifact_ready": {
        "title": "产出就绪",
        "summary": "【样式预览】agent.artifact_ready — report.md",
        "status": "success",
    },
}


def demo_envelope(scene_id: str, *, run_id: str) -> dict[str, Any]:
    payload = dict(DEMO_PAYLOADS.get(scene_id) or {"title": scene_id, "summary": f"【样式预览】{scene_id}"})
    env: dict[str, Any] = {
        "fnp_version": 1,
        "scene": scene_id,
        "format": "auto",
        "route": "dm_self",
        "payload": payload,
        "context": {"harness": "fnotify-demo", "run_id": run_id},
    }
    if scene_id == "agent.progress":
        env["delivery"] = {"mode": "send"}
    return env


def run_scenes_demo(
    *,
    dry_run: bool = False,
    only: str | None = None,
    interval_sec: float = 0.8,
) -> list[dict[str, Any]]:
    scenes = list_scenes()
    if only:
        scenes = [s for s in scenes if s["id"] == only]
        if not scenes:
            raise ValueError(f"unknown scene: {only}")

    batch = f"style-preview-{int(time.time())}"
    results: list[dict[str, Any]] = []

    for idx, scene in enumerate(scenes):
        sid = scene["id"]
        run_id = f"{batch}-{sid}"
        env = demo_envelope(sid, run_id=run_id)
        body = process_send(env, dry_run=dry_run)
        results.append({"scene": sid, "header": scene.get("description"), **body})
        if not dry_run and idx < len(scenes) - 1 and interval_sec > 0:
            time.sleep(interval_sec)

    return results