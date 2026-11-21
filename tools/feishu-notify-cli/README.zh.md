# feishu-notify-cli

**操作说明（推荐先看）：** [docs/OPERATIONS.zh.md](docs/OPERATIONS.zh.md)

[English](README.md)

MyWikiTools monorepo：`tools/feishu-notify-cli/`。**Harness 无关**的飞书出站 CLI（FNP v1），经 `lark-cli` 发送；支持 **文本 + 场景卡片**、**bot / user** 身份。

| 入口 | 命令 |
|------|------|
| 短名 | **`fnotify`** |
| 长名 | **`feishu-notify`** |

## 产品默认（已锁定）

| 项 | 值 |
|----|-----|
| 默认会话 | `dm_self` — **Bot 私聊** |
| `agent.progress` | **卡片** + **M2 单卡 patch** |
| 场景扩展 | 仅仓库内 **builtin_scenes**（不支持外挂 `card.json`） |
| CLI 短名 | **fnotify** |

## 快速开始

```bash
pipx install ./tools/feishu-notify-cli   # 或 pipx install . --force
fnotify install                          # 引导配置 lark-cli + 写入收件人
fnotify uninstall --yes                  # 清除本机 fnotify 配置
```

`install` 在交互终端内按需引导 `lark-cli config init --new` 与 `auth login --domain im`，无需另开终端手工配 lark-cli。

## 命令

```bash
fnotify scenes list
fnotify scenes describe agent.progress
fnotify render --scene agent.conclusion --file payload.json
fnotify send --stdin --dry-run    # 调试，不真发
fnotify send --stdin              # 发送
fnotify patch --stdin             # 显式 patch
fnotify run list                  # 查看 run_id 绑定
```

### M2 进展示例

```bash
RID="sync-$(date +%s)"
for n in 3 7 10; do
  echo "{\"fnp_version\":1,\"scene\":\"agent.progress\",\"context\":{\"run_id\":\"$RID\"},\"payload\":{\"title\":\"同步\",\"summary\":\"${n}/10\",\"status\":\"running\"}}" \
    | fnotify send --stdin --json-output
  sleep 1
done
echo "{\"fnp_version\":1,\"scene\":\"agent.conclusion\",\"context\":{\"run_id\":\"$RID\"},\"payload\":{\"title\":\"完成\",\"summary\":\"10/10\",\"status\":\"success\"}}" \
  | fnotify send --stdin
```

飞书里应只见 **一条进展卡不断变化**，再加一条结论。

## FNP 示例

```json
{
  "fnp_version": 1,
  "scene": "agent.progress",
  "format": "auto",
  "identity": "auto",
  "route": "dm_self",
  "payload": {
    "title": "同步任务",
    "summary": "已处理 3/10 个文件",
    "status": "running",
    "fields": [
      { "label": "工作区", "value": "MyWikiTools" }
    ]
  },
  "context": {
    "harness": "cursor",
    "run_id": "abc"
  }
}
```

```bash
echo '<上面 JSON>' | fnotify send --stdin --json-output
```

协议全文：[docs/FNP.md](docs/FNP.md)

## 内置场景（v0.1 投产集）

| Scene | 用途 |
|-------|------|
| `notify.plain` | 通用通知 |
| `agent.ack` | 已收到指令 |
| `agent.progress` | 进展（默认卡片） |
| `agent.conclusion` | 成功结束 |
| `agent.partial` | 部分完成 |
| `agent.failure` | 失败 |
| `agent.cancelled` | 取消 |
| `agent.alert` | 紧急提醒 |
| `agent.approval` | 人工确认（按钮） |
| `agent.report` | 汇报 |
| `agent.link_digest` | 链接摘要 |
| `agent.artifact_ready` | 产出物就绪 |

模板目录：`src/feishu_notify/builtin_scenes/`（含 `shared/` 公共 Jinja 模板）。

## 各 Harness 集成（同一命令）

任意 Agent 结束时组 FNP JSON，调用：

```bash
fnotify send --stdin --json-output
```

| Harness | 挂载点 |
|---------|--------|
| Cursor / Codex / Claude | 个人 Skill `skills/feishu-notify-cli` |
| Pi / DeepSeek / 脚本 | `post_command` / cron / CI |

**不要**在核心库里依赖某家 SDK。

## 与双向遥控的关系

- **出站（本工具）**：Agent → 飞书
- **入站（规划中）**：`im.message.receive_v1` + Cursor SDK 等 → 另一条 `fnotify bridge` 命令

出站卡片上的 `callback` 按钮需 **bot** 身份；入站消费 `card.action.trigger` 与出站 `agent.approval` 共用 `run_id` / `trace_id` 约定见 FNP。