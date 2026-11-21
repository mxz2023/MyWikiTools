# fnotify 操作说明

把 Agent 的运行结果发到 **飞书 Bot 私聊**。默认 **M2**：进展只用 **一张卡片**，后续更新同一条消息。

---

## 一、准备（一次性）

### 推荐：两条命令（pipx + install）

```bash
pipx install /path/to/MyWikiTools/tools/feishu-notify-cli --force
fnotify install
```

**只需 `fnotify install` 即可**（交互终端）：按需自动引导

1. `lark-cli config init --new`（若尚未绑定应用）  
2. `lark-cli auth login --domain im`（若用户未登录）  
3. 写入 `~/.config/fnotify`、`doctor`、可选测试消息  

无需再手工拼 `auth login` 后重跑 install。

前置：**本机已安装 `lark-cli` 命令**（install 只负责配置，不安装 lark-cli 包）。

非交互 / CI 请用 `--json-output`，失败时按返回的 `error` 手工执行 lark-cli。

### 卸载 / 重配

```bash
fnotify uninstall       # 交互：①删配置 ②可选清 lark-cli ③可选 pipx 卸 fnotify
fnotify uninstall --yes # 仅删 ~/.config/fnotify，不询问 ②③
```

见 [RESET.zh.md](RESET.zh.md)。

### 手动检查

```bash
fnotify doctor    # 分条列出哪一步未就绪
```

---

## 二、最常用：发一条通知

```bash
echo '{"fnp_version":1,"scene":"notify.plain","payload":{"summary":"你好，这是一条测试"}}' \
  | fnotify send --stdin
```

---

## 三、跑任务：进展 + 结论（M2）

同一任务用 **同一个 `run_id`**。

### 1. 进展（第一张卡 + 后续改同一条）

```bash
RID="my-task-001"

# 第一次：新建进展卡
echo "{\"fnp_version\":1,\"scene\":\"agent.progress\",\"context\":{\"run_id\":\"$RID\"},\"payload\":{\"title\":\"任务名\",\"summary\":\"0/10 开始\",\"status\":\"running\"}}" \
  | fnotify send --stdin

# 第二次起：自动 patch 同一张卡
echo "{\"fnp_version\":1,\"scene\":\"agent.progress\",\"context\":{\"run_id\":\"$RID\"},\"payload\":{\"title\":\"任务名\",\"summary\":\"5/10 进行中\",\"status\":\"running\"}}" \
  | fnotify send --stdin
```

飞书里应看到 **一条进展卡在变**，而不是多条新卡。

### 2. 结束（新发一条结论，并清除 run 绑定）

```bash
echo "{\"fnp_version\":1,\"scene\":\"agent.conclusion\",\"context\":{\"run_id\":\"$RID\"},\"payload\":{\"title\":\"完成\",\"summary\":\"10/10 成功\",\"status\":\"success\"}}" \
  | fnotify send --stdin
```

### 3. 失败时

```bash
echo "{\"fnp_version\":1,\"scene\":\"agent.failure\",\"context\":{\"run_id\":\"$RID\"},\"payload\":{\"title\":\"失败\",\"summary\":\"原因简述\",\"status\":\"failed\"}}" \
  | fnotify send --stdin
```

---

## 四、调试（不真发飞书）

```bash
fnotify send --stdin --dry-run --json-output < payload.json
```

看 `delivery_op`：`send` = 新建，`patch` = 更新旧卡。

只看渲染效果：

```bash
fnotify render --scene agent.conclusion --stdin <<'JSON'
{"payload":{"title":"演示","summary":"结论一句"}}
JSON
```

---

## 五、场景怎么选（简表）

| 你想说 | scene |
|--------|--------|
| 随便一句 | `notify.plain` |
| 已开始 / 进度 | `agent.progress`（要 `run_id`） |
| 成功结束 | `agent.conclusion` |
| 部分完成 | `agent.partial` |
| 失败 | `agent.failure` |
| 取消了 | `agent.cancelled` |
| 很急 | `agent.alert` |
| 要按钮确认 | `agent.approval`（须 bot + 卡片按钮） |
| 日报汇总 | `agent.report` |
| 链为主 | `agent.link_digest` |
| 文件好了 | `agent.artifact_ready` |

详细协议：[FNP.md](FNP.md)

```bash
fnotify scenes describe agent.progress

# 12 个场景样式预览（真发到 Bot 私聊，约 12 条消息）
fnotify scenes demo
fnotify scenes demo --scene agent.failure
fnotify scenes demo --dry-run
```

---

## 六、维护命令

```bash
fnotify run list              # 哪些 run_id 还绑着 message_id
fnotify run show my-task-001
fnotify run clear my-task-001 # 手动解绑
fnotify patch --stdin         # 强制 patch（一般不用，send 会自动）
```

---

## 七、给 Agent 用（Skill）

任意 Harness 在任务结束或阶段节点组 JSON，统一：

```bash
fnotify send --stdin --json-output
```

Skill 路径（仓库内）：`skills/feishu-notify-cli/SKILL.md`

---

## 八、自测清单（本机）

```bash
cd tools/feishu-notify-cli && python3 -m pytest -q   # 应为 8 passed
fnotify doctor --json-output                        # ok 为 true
# M2 干跑：两条 progress 第二条 delivery_op 应为 patch（见 README.zh.md 示例）
```

---

## 常见问题

| 现象 | 处理 |
|------|------|
| `user_id is empty` | 配置 `routes.dm_self.user_id` |
| `lark-cli auth` 失败 | 重新 `auth login --domain im` |
| 每条进展都是新气泡 | 检查是否同一 `run_id`；`config` 里 `progress.mode: m2` |
| `context.run_id is required` | `agent.progress` 必须带 `run_id` |
| 要强制每条新发 | JSON 加 `"delivery": {"mode": "send"}` |