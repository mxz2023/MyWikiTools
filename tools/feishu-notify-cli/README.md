# feishu-notify-cli

[简体中文](README.zh.md)

Part of [MyWikiTools](../../README.md). Harness-agnostic **Feishu outbound** for agents (FNP v1) via `lark-cli` — text and scene-based interactive cards, `bot` or `user` identity.

| Entry | Command |
|-------|---------|
| Short | **`fnotify`** |
| Long | **`feishu-notify`** |

See [README.zh.md](README.zh.md) for defaults, install, and the full scene catalog. Protocol: [docs/FNP.md](docs/FNP.md).

## Bilingual `--help`

Same convention as `gmp` ([docs/cli-help-standard.md](../../docs/cli-help-standard.md)):

- Default **`--lang both`**: `fnotify --help` and option text use **English / 中文**.
- **`--lang en`** | **`--lang zh`**
- Env: **`FNOTIFY_CLI_LANG`** = `both` | `en` | `zh`

```bash
fnotify --help
fnotify listen --help
```