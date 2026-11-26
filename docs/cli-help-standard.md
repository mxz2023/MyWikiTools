# MyWikiTools CLI `--help` 标准

Monorepo 内基于 Typer 的 CLI（`gmp`、`fnotify`、`mfp` 等）在 `--help` 上遵循同一约定，便于用户与 Agent 一致理解。

## 双语

- 默认 **`--lang both`**：固定文案使用 **`English / 中文`** 同一行（与 `gmp --help` 一致）。
- **`--lang en`** | **`--lang zh`**：仅一种语言。
- 环境变量：各工具 `*_CLI_LANG`（如 `GARMIN_CLI_LANG`、`FNOTIFY_CLI_LANG`），取值 `both|en|zh`。

实现：

1. `src/<pkg>/i18n.py` — 从 `argv` / env 解析 `LANG`；可选 `T(en, zh)`。
2. `src/<pkg>/help_text.py` — `ROOT_HELP`、`EPILOG`、`OPT_*`、`CMD_*` 常量，不写在 `cli.py` 里堆长字符串。
3. 根 `Typer(help=ROOT_HELP, epilog=EPILOG)` + `@app.callback()` 声明 `--lang`。

## 根 help 必含块

与 Garmin `gmp` 对齐，根 `ROOT_HELP` 至少包括：

| 块 | 内容 |
|----|------|
| 标题 | 英文一句 + `/` + 中文一句 |
| 命令名 | 短名、长名（若有） |
| Workflow / 流程 | 3–5 步典型路径 |
| Defaults / 默认 | 配置路径、重要默认行为 |
| Exit codes / 退出码 | 非 0 含义 |
| Agent | 何时加 `--json-output` |

## 选项与子命令

- 每个 `typer.Option(..., help=...)` 使用 `help_text.OPT_*` 双语串。
- 子命令：`@app.command(help=help_text.CMD_*)`；需要多行说明时用双语 **docstring**（`fnotify send --help` 展开）。
- Typer 组：`Typer(help=...)` 同样双语。

## 不要求

- 运行时错误、API 原始响应不必双语（可逐步加 `i18n.T()`）。
- 第三方工具（`lark-cli`）转发的 stderr 不翻译。

## 参考实现

- **完整**：`tools/garmin-personal-cli/`（`help_text.py`、`i18n.py`、`cli.py`）
- **FNP**：`tools/feishu-notify-cli/`

新工具从第一天起拷贝上述两文件结构，再填 `ROOT_HELP` 与 `OPT_*`。