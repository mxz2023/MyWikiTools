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

## 入站监听（长连接）

封装 `lark-cli event consume`，默认只收 **Bot 私聊里你发的文字**（与 `routes.dm_self.user_id` 一致）。

```bash
# 一直挂着（无 --timeout）；落盘日志
fnotify listen --log

# 限时 + 收满 5 条就停
fnotify listen --timeout 30m --max-events 5 --log

# 文字 + 卡片按钮回调（审批确认）
fnotify listen --all --timeout 1h --log

# 看将要执行的 lark-cli 参数（不连飞书）
fnotify listen --dry-run

# 自定义 jq（覆盖默认过滤）
fnotify listen --jq 'select(.message_type=="text") | .content'
```

| 参数 | 作用 |
|------|------|
| `--timeout` / `--duration` | `0` 不限时；否则 `30m`、`2h` |
| `--max-events` | 收到 N 条业务事件后退出 |
| `--log` / `--log-file` | NDJSON 审计日志（含 `listen.start` / `listen.end`） |
| `--log-meta` | 终端 stdout 带 `ts` + `event_key` 包装 |
| `--quiet-bus` | 不刷屏 lark-cli 的 `[event]` stderr |
| `--all` | 同时监听 `im.message.receive_v1` + `card.action.trigger` |
| `--p2p-only` / `--self-only` | 默认只 Bot 私聊 + 只你自己 |
| `--include-post` / `--text-only` | 富文本 post 是否算入站 |
| `--jq` | 高级过滤（与 lark-cli 一致） |

**前提**：飞书后台 **长连接** + 已订阅对应事件；卡片回调另需 **回调配置**。

## Bridge：飞书 ↔ Codex（推荐）

默认 harness 已是 **codex**。同一 Bot 私聊的多条消息会 **续在同一个 Codex thread**（`codex exec resume <thread_id>`），在 Codex 客户端 / `codex agents` 里能看到完整对话。

```bash
fnotify bridge --workspace ~/Code/MyWikiTools --log
# 或显式
fnotify bridge --harness codex --workspace ~/Code/MyWikiTools
```

1. 飞书私聊发文字 → **M2 AI 回复卡** `agent.codex_reply`（标题 **已收到「你的原文」**；**蓝头=处理中 / 绿头=完成**；无单独 ack）  
2. 同一张卡 **patch** 更新：正文为思考/工具步骤（副标题 `Ns · M 步`；无 loading 图）  
3. 本机跑 `codex exec …`（首条新建 thread，之后 `resume`）  
4. Codex 结束后 → 结论文本写在 **同一张进度卡底部**（标题仍为 **已收到「…」**；不另发一条纯文本）。关闭实时进度时仍走 **notify.plain** / conclusion 卡

关闭实时进度： `bridge.codex.live_progress: false`；调刷新间隔 `progress_min_interval_sec`（默认 2.5s）。

**后台常驻（推荐）**：用 macOS `launchd` 托管，进程崩溃会自动拉起，且**不依赖 Cursor/终端会话**（在 Agent 里 `nohup` 起的 bridge 常会随会话结束被杀掉）：

```bash
cd tools/feishu-notify-cli
WORKSPACE=~/Code/MyWikiTools ./scripts/install-bridge-daemon.sh
tail -f ~/.config/fnotify/logs/bridge-daemon.log
# 停止：launchctl bootout gui/$(id -u)/com.fnotify.bridge
```

**改代码后自动加载最新版**：launchd **不会**在保存 `.py` 时自动重启；`KeepAlive` 只在进程崩溃时拉起。开发时可在另一个终端开着监视脚本（有防抖，约 1.5s 后执行 `kickstart -k`）：

```bash
cd tools/feishu-notify-cli
./scripts/bridge-watch-reload.sh
# 可选：仅监视 config.yaml（勿监视整个 ~/.config/fnotify，runs.json 会误触发重启）
./scripts/bridge-watch-reload.sh ~/.config/fnotify/config.yaml
```

会中断进行中的 Codex（等同手动 `kickstart -k`）；稳定环境请不用监视，改完再手动 reload 一次。

**登录后常驻监视**（不占终端，适合本机长期开发）：

```bash
cd tools/feishu-notify-cli
./scripts/install-bridge-watch.sh
tail -f ~/.config/fnotify/logs/bridge-watch.log
# 停止：launchctl bootout gui/$(id -u)/com.fnotify.bridge-watch
```

与 `com.fnotify.bridge` 独立：watch 只负责检测文件变更并 `kickstart -k` bridge。仓库路径若搬家，需重新执行本安装脚本更新 plist。

**补跑**：飞书长连接**不补发**离线期间的消息。`fnotify bridge` 启动时默认 `--catch-up`：读 Bot 私聊最近记录，对「只有你发的文字、Bot 只有已收到、没有结论文本」的消息依次走 Codex。

临时前台调试：`fnotify bridge --workspace ~/Code/MyWikiTools --log`。

**Codex 进度里 `Reconnecting… request timed out`**：来自 **Codex CLI ↔ OpenAI**，不是飞书。常见原因：① **launchd 未带 HTTP(S)_PROXY**（终端里走 `127.0.0.1:7890`，daemon 默认没有）；② WebSocket 在代理/VPN 下易超时，Codex 会 **重试 5 次再降级 HTTPS**（你看到的 2/5…5/5）；③ `exec resume` 长会话 + MCP 启动也会拖长时间。处理：编辑 `~/.config/fnotify/bridge.env` 写入与终端一致的代理，再 `launchctl kickstart -k gui/$(id -u)/com.fnotify.bridge`；或前台用同一终端跑 bridge 以继承代理。

`~/.config/fnotify/config.yaml` 可调 Codex：

```yaml
bridge:
  default_harness: codex
  workspace: /Users/you/Code/MyWikiTools
  agent_timeout_sec: 3600
  codex:
    skip_git_repo_check: true
    approve_for_me: true
    thread_name: "Feishu Bot"
    # 用 Codex 桌面同款 CLI（~/.codex/config.toml 里的 gpt-6-sol 等），不要用 PATH 里过旧的 codex：
    executable: "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
    model: ""   # 空 = 读 ~/.codex/config.toml；仅 API Key 登录时才常需 -m 覆盖
```

若 `codex exec` 报 **model not supported when using Codex with a ChatGPT account**，多半是 **Homebrew/npm 的 codex 过旧**，走了 ChatGPT 订阅模型表；与你在 Codex App 里选的 **Codex 模型** 不是同一条路。解决：**升级** `npm i -g @openai/codex@latest`，或在上面配置 **executable** 指向 ChatGPT.app 内置 CLI。

若要用 **OpenAI API Key** 走 API 模型表（与 ChatGPT 订阅不同），在本机执行 `printenv OPENAI_API_KEY | codex login --with-api-key`，再在 `model` 里填 API 侧可用模型名。
```

绑定文件：`~/.config/fnotify/codex_sessions.json`（`chat_id` → `thread_id`）。

```bash
fnotify codex sessions          # 查看绑定
fnotify codex reset             # 下一条飞书消息将开新 Codex 对话
fnotify codex reset --chat-id oc_xxx
```

本机需已 `codex login`；工作区建议为 git 仓库，或保持 `skip_git_repo_check: true`。

## Bridge：飞书 → 其它 Agent CLI（cursor / 自定义）

一条命令 = 长连接 + 把私聊文字派发给本机 Agent，并用 **ack / conclusion / failure** 卡片回飞书。

```bash
# 推荐：默认 cursor，工作区当前目录，写日志
fnotify bridge --workspace ~/Code/MyWikiTools --log

# 用 Codex，单次任务最长 30 分钟
fnotify bridge --harness codex --workspace ~/Code/MyWikiTools --agent-timeout 1800

# 等价于 listen --dispatch
fnotify listen --dispatch --harness cursor --workspace ~/Code/MyWikiTools --log

# 只打印将要执行的 Agent 命令（不真跑、不发卡片）
fnotify bridge --dispatch-dry-run
```

`~/.config/fnotify/config.yaml` 可增加：

```yaml
bridge:
  default_harness: cursor
  workspace: /Users/you/Code/MyWikiTools
  agent_timeout_sec: 3600
  notify: true
  harnesses:
    deepseek:
      argv: ["your-deepseek-cli", "chat", "{prompt}"]
```

内置 **cursor**、**codex**、**shell**（`shell_cmd`）；其它 CLI 用 `harnesses.<名字>.argv`，占位符 `{prompt}` `{workspace}` `{run_id}` `{message_id}`。

**注意**：同一时刻只跑一个 Agent（串行）；飞书里连续发两条时，第二条若上一条未结束会跳过（日志 `bridge.skipped`）。长任务请等结论卡再发下一条。
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