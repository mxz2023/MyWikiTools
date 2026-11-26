"""Bilingual CLI help strings (EN / 中文). See repo docs/cli-help-standard.md."""

ROOT_HELP = """
Feishu agent notify CLI (FNP v1) via lark-cli. / Agent 飞书通知 CLI（FNP v1），经 lark-cli 投递。

Commands: fnotify | feishu-notify

Workflow / 流程:
  1. fnotify install                    # lark-cli + Bot DM recipient / 绑定应用与私聊收件人
  2. fnotify doctor                     # verify auth and open_id / 自检
  3. fnotify scenes list                # builtin scenes / 内置场景
  4. echo '<FNP JSON>' | fnotify send --stdin --json-output

Outbound / 出站:
  FNP JSON → scene template → Bot P2P card or text (default route dm_self)
  agent.progress + context.run_id → M2: first send, then patch same card
  FNP 信封 → 场景模板 → Bot 私聊卡片或文本；进展场景同 run_id 单卡 M2 更新

Inbound / 入站（辅助）:
  fnotify bridge --harness cursor --log     # listen + dispatch to Agent CLI / 监听并派发 Agent
  fnotify listen --dispatch --harness codex # same / 同上
  fnotify listen --log                    # lark-cli event consume wrapper / 长连接监听
  Requires Feishu console: long connection + im.message.receive_v1
  需飞书后台长连接并订阅 im.message.receive_v1

Defaults / 默认:
  Route dm_self (Bot private chat) / 路由 Bot 私聊
  Identity bot for send (callback buttons require bot) / 发送默认 bot 身份
  Config ~/.config/fnotify/config.yaml; runs ~/.config/fnotify/runs.json
  Builtin scenes only (no custom card.json) / 仅内置场景

Exit codes / 退出码:
  0 ok; 2 validation (FNP/scene); 3 config/credentials; 5 delivery/listen; 10 render

Agent output: add --json-output on send, doctor, scenes, listen (summary).
""".strip()

EPILOG = (
    "After `pipx install` only: run `fnotify install` then `fnotify doctor`. / "
    "仅 pipx 安装后请先执行 `fnotify install`，再 `fnotify doctor`。"
)

# --- Global options ---
OPT_LANG = "Help text language: both | en | zh / help 文案语言."
OPT_JSON_OUTPUT = (
    'Emit {"status","headers","body"} JSON / 输出含 status、headers、body 的 JSON（便于 Agent 解析）'
)
OPT_QUIET = "Less stderr / 减少 stderr 输出"

# --- Shared options ---
OPT_STDIN = "Read JSON from stdin / 从 stdin 读取 JSON"
OPT_FILE = "JSON file path / JSON 文件路径"
OPT_DRY_RUN = "Do not call Feishu APIs / 不调用飞书发送或长连接"
OPT_CONFIG = "Config YAML (default ~/.config/fnotify/config.yaml) / 配置文件路径"
OPT_RUNS_STORE = "M2 bindings JSON (default ~/.config/fnotify/runs.json) / run_id 绑定存储"

# --- install / uninstall ---
OPT_INSTALL_YES = "Non-interactive; auto-send test message / 非交互并自动发测试消息"
OPT_INSTALL_SKIP_TEST = "Skip post-setup test message / 跳过后续测试消息"
OPT_UNINSTALL_YES = "Only step 1 (drop fnotify config); skip lark prompts / 仅删 fnotify 配置"

# --- send / patch / render ---
OPT_SEND_STDIN = "Read FNP envelope JSON from stdin / 从 stdin 读取 FNP 信封"
OPT_SCENE = "Scene id, e.g. agent.conclusion / 场景 id"
OPT_FORMAT = "auto | text | card / 输出格式"
OPT_PATCH_MSG_ID = "Target message id om_… for patch / patch 目标消息 id"

# --- scenes ---
OPT_DEMO_SCENE = "Only this scene id / 仅该场景"
OPT_DEMO_INTERVAL = "Seconds between live demo sends / 真发演示间隔秒"
OPT_SCENE_ID = "Builtin scene id / 内置场景 id"

# --- listen ---
OPT_LISTEN_TIMEOUT = (
    "Run limit: 0 unlimited, or 30m, 2h (lark-cli --timeout) / "
    "运行时长：0 不限，或 30m、2h"
)
OPT_LISTEN_MAX_EVENTS = "Exit after N events (0 = no limit) / 收到 N 条后退出"
OPT_LISTEN_LOG = "Append NDJSON to ~/.config/fnotify/logs/ / 写入默认日志目录"
OPT_LISTEN_LOG_FILE = "Custom NDJSON log path / 自定义日志路径"
OPT_LISTEN_LOG_META = (
    "Stdout: {ts, event_key, event} wrapper / 终端输出带时间戳包装"
)
OPT_LISTEN_QUIET_BUS = "Hide lark-cli [event] lines on stderr / 隐藏 lark-cli 诊断"
OPT_LISTEN_ALL = (
    "im.message.receive_v1 + card.action.trigger / 私聊文字 + 卡片按钮"
)
OPT_LISTEN_EVENT = "EventKey (repeatable) / 事件键（可重复）"
OPT_LISTEN_JQ = "Override default jq filter / 覆盖默认 jq 过滤"
OPT_LISTEN_AS = "bot | user for lark-cli --as / lark-cli 身份"
OPT_LISTEN_DRY_RUN = "Print consume plan only / 只打印将执行的 consume 命令"
OPT_DISPATCH = "On each message, invoke Agent CLI / 每条消息派发到 Agent"
OPT_HARNESS = "cursor | codex | shell | config harnesses.<name> / Agent 后端"
OPT_WORKSPACE = "Agent working directory (--workspace / codex --cd) / 工作区根目录"
OPT_AGENT_TIMEOUT = "Max seconds per Agent run / 单次 Agent 超时秒数"
OPT_NO_NOTIFY = "Do not send ack/conclusion cards / 不回发飞书 ack 与结论卡"
OPT_DISPATCH_DRY_RUN = "Print Agent cmd only (no run, no Feishu) / 只打印 Agent 命令"

# --- Top-level & group command one-liners (Typer Commands list) ---
CMD_VERSION = "Print package version / 打印版本号"
CMD_INSTALL = "Guide lark-cli + fnotify setup (start here) / 引导安装（推荐首选）"
CMD_UNINSTALL = "Remove fnotify config; optional lark-cli cleanup / 卸载配置"
CMD_DOCTOR = "Check lark-cli, auth, dm_self recipient / 自检依赖与收件人"
CMD_SEND = (
    "Send FNP envelope; M2 auto-patch agent.progress / 发送 FNP（进展自动 M2 patch）"
)
CMD_PATCH = "Patch interactive card (delivery.mode=patch) / 更新已有互动卡片"
CMD_RENDER = "Render template only, no send / 仅渲染模板不发飞书"
CMD_LISTEN = "Feishu long connection via lark-cli event consume / 长连接入站监听"
CMD_BRIDGE = (
    "Listen on Bot DM and run Agent CLI (cursor, codex, …) / 监听私聊并调用 Agent CLI"
)
CMD_SCENES = "Builtin scene catalog (templates in package) / 内置场景目录"
CMD_CONFIG = "Local ~/.config/fnotify/ settings / 本地配置"
CMD_RUN = "M2 run_id ↔ message_id bindings / M2 进展卡绑定"

GRP_SCENES_LIST = "List scene ids and versions / 列出场景"
GRP_SCENES_DESCRIBE = "Show manifest fields and templates / 查看场景详情"
GRP_SCENES_DEMO = "Send style-preview sample cards to Bot DM / 样式预览真发"

GRP_CONFIG_INIT = "Create default config.yaml / 初始化配置文件"
GRP_CONFIG_SHOW = "Print merged config / 显示当前配置"

GRP_RUN_LIST = "List active run_id bindings / 列出 run 绑定"
GRP_RUN_SHOW = "Show binding for one run_id / 查看单个 run"
GRP_RUN_CLEAR = "Remove run_id binding / 清除 run 绑定"

# Longer docs for `fnotify COMMAND --help` (command docstrings)
DOC_SEND = """
Validate FNP v1, render scene template, deliver via lark-cli.

校验 FNP v1 信封，渲染场景模板，经 lark-cli 发送。

Example / 示例:
  echo '{"fnp_version":1,"scene":"notify.plain","payload":{"summary":"hi"}}' \\
    | fnotify send --stdin --json-output

M2: agent.progress needs context.run_id; later sends patch the same card.
M2：agent.progress 需 context.run_id；后续同 run_id 会 patch 同一张卡。
""".strip()

DOC_PATCH = """
Force delivery.mode=patch on the envelope (optional --message-id).

强制 patch 模式更新卡片（可用 --message-id 指定 om_…）。
""".strip()

DOC_LISTEN = """
Wrap `lark-cli event consume` with dm_self-friendly defaults (p2p, self sender).

封装 lark-cli 长连接；默认仅 Bot 私聊、仅配置中的 user open_id。

Example / 示例:
  fnotify listen --timeout 30m --log
  fnotify listen --all --timeout 1h --log    # + card buttons / 含卡片按钮

Console: long connection mode + subscribe im.message.receive_v1.
飞书后台须使用长连接并订阅事件（非 Webhook URL）。

Dispatch / 派发 Agent:
  fnotify bridge --harness cursor --workspace ~/Code/MyWikiTools
  fnotify listen --dispatch --harness codex --log --notify

Built-in harnesses / 内置后端:
  cursor → cursor agent --print --force --workspace …
  codex  → codex exec -C …
  shell  → bridge.shell_cmd (default echo)
  deepseek, pi, … → config bridge.harnesses.<name>.argv
""".strip()

DOC_BRIDGE = """
Long-poll Feishu, run one Agent job per message (serial), reply via FNP cards.

长连接收消息，串行执行 Agent，用 ack / conclusion / failure 卡片回飞书。

Example / 示例:
  fnotify bridge --harness cursor --workspace ~/Code/MyWikiTools --log
  fnotify bridge --harness codex --agent-timeout 1800

Config ~/.config/fnotify/config.yaml → bridge.default_harness, bridge.workspace.
自定义 CLI：bridge.harnesses.deepseek.argv: ["your-cli", "{prompt}"]
""".strip()

DOC_SCENES_DEMO = """
Send one sample card per builtin scene (summary contains 样式预览).

每个内置场景发一条示例卡到 Bot 私聊（摘要含「样式预览」）。
""".strip()