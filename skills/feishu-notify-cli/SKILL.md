---
name: feishu-notify-cli
version: 0.1.0
description: "Agent 飞书出站（FNP v1）：通过 fnotify 发送通知、进展与结论，支持文本与场景卡片、bot/user 双身份。适用于 Cursor、Codex、Claude、Pi、DeepSeek、脚本与 CI。当用户要求飞书通知、发进展、发结论、或任务结束推送时使用。"
metadata:
  requires:
    bins: ["fnotify", "lark-cli"]
---

# feishu-notify-cli (fnotify)

Harness 无关：只构造 **FNP JSON**，调用 `fnotify send --stdin`。不手写飞书卡片 JSON；场景模板在 `feishu-notify-cli` 包内维护。

## 产品默认

- 路由：`dm_self`（**Bot 私聊**）
- 进展场景：`agent.progress` → **卡片**
- 身份：`auto`（有 callback 按钮 → bot；否则见场景 manifest）

## 前置

用户本机：`pipx install` 后只跑 `fnotify install`（内含 lark-cli 应用绑定与用户扫码 + fnotify 配置 + doctor）。重配先 `fnotify uninstall`。

## M2 进展（默认）

`agent.progress` 必须带 **`context.run_id`**。同一 `run_id`：**第一条 send 建卡，其后 patch 同一条消息**。终态 `conclusion`/`failure` 等会清除绑定。

```json
"context": {"run_id": "my-task-20251121-1"}
```

强制新发一条进展（不 patch）：`"delivery": {"mode": "send"}`。

## 何时发送

| 用户意图 | scene |
|----------|-------|
| 一句话通知 | `notify.plain` |
| 收到指令 / 已开始 | `agent.ack` |
| 长跑进展 | `agent.progress` |
| 成功结束 | `agent.conclusion` |
| 部分完成 | `agent.partial` |
| 失败 | `agent.failure` |
| 紧急 | `agent.alert` |
| 要人点按钮确认 | `agent.approval`（`actions` 含 `callback`） |
| 日报 / 汇报 | `agent.report` |
| 链接汇总 | `agent.link_digest` |
| 文件就绪 | `agent.artifact_ready` |

## 调用

```bash
fnotify send --stdin --json-output
```

最小 payload 字段见 `fnotify scenes describe <scene>`。协议：[tools/feishu-notify-cli/docs/FNP.md](../../tools/feishu-notify-cli/docs/FNP.md)（仓库相对路径）。

## payload 约定

- `title` + `summary`：首屏信息
- `fields`：`{label, value}[]`
- 长文放 `body_md`；超过配置长度会自动 **另发文件消息**
- `actions`：`kind: url|callback`；callback 的 `value` 为 JSON 对象（供日后入站 Bridge 解析）

## 禁止

- 不要使用未列出的 `scene` 或外挂 `card.json`
- 勿向群发送未脱敏密钥；必要时只发 `summary`
- 真发前若收件人非默认 Bot 私聊，须向用户确认

## 调试

```bash
fnotify render --scene agent.conclusion --file payload.json
fnotify send --stdin --dry-run
```