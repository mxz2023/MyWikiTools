---
name: mi-fitness-cli
description: >-
  Sync and query the user's own Xiaomi Mi Fitness (小米运动健康) data via `mfp` on macOS
  (--json-output). Use for 小米运动健康, 步数, 睡眠, 心率, 运动, 体重, 体脂秤 — cloud sync
  to SQLite; not for other users' data.
---

# Mi Fitness CLI (Agent Skill)

## What this is

- **CLI**: `mfp` / `mi-fitness` — login (QR or passToken), `sync` from `hlth.io.mi.com`, query local SQLite.
- **Catalog**: [reference.md](reference.md)

## Hard rules

1. **Own data only** — user's session on their Mac.
2. **Do not** WebFetch/WebSearch to guess Xiaomi API shapes; use `mfp` subcommands.
3. **Data commands**: `--json-output --json-errors` unless the user wants human-only output.
4. **Never invent** fields in `body` before a successful command.
5. Scale/body-fat data requires the measurement synced to Mi Fitness cloud first.

## Install

```bash
pipx install ./tools/mi-fitness-cli
mfp login
mfp sync --days 30
```

## Typical flow

```bash
mfp doctor --json-output
mfp status --json-output
mfp sync --days 7 --json-output
mfp steps --days 7 --json-output
mfp sleep --days 7 --json-output
mfp weight --full --json-output
```

## JSON success (`--json-output`)

```json
{
  "status": 200,
  "headers": {},
  "body": { }
}
```

## Paths

- Session: `~/.config/mi-fitness/session.json`
- DB: `~/.local/share/mi-fitness/health.db`
