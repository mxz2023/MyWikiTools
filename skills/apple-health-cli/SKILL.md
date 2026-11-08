---
name: apple-health-cli
description: >-
  Sync and query the user's own Apple Watch / Health data via `ahp` / `apple-health`
  on macOS (--json-output). Use for 苹果手表, Apple Watch, 健康, 步数, 睡眠, 心率,
  运动, 锻炼, workouts — iPhone AHPSync pushes to Mac; not for other users' data.
---

# Apple Health CLI (Agent Skill)

## What this is

- **CLI**: `ahp` — SQLite cache on Mac after **AHPSync** (iOS) POSTs to `ahp serve`.
- **No Mac HealthKit** — do not use removed `sync` / `authorize` commands.

## Hard rules

1. **Own data only** on the user's Mac.
2. **Do not** invent sample values — ensure `ahp serve` ran and phone synced, or `ahp import`.
3. **Data commands**: use **`--json-output`** unless the user wants human-only output.
4. Path: Watch → iPhone **AHPSync** → `http://<mac>:8765/api/ingest` → query `ahp steps` etc.

## Install

```bash
pipx install ./tools/apple-health-cli
ahp serve --host 0.0.0.0
```

## Typical agent flow

```bash
ahp doctor --json-output
ahp status --json-output
ahp steps --days 7 --json-output
ahp sleep --days 7 --json-output
ahp workouts --days 30 --json-output
```

## Commands

| Command | Purpose |
|---------|---------|
| `setup` | Onboarding |
| `doctor` | Supported commands |
| `serve` | HTTP ingest (`--host 0.0.0.0`, token) |
| `watch` | Auto-import folder |
| `import PATH` | `export.xml` bulk |
| `status` | DB stats |
| `steps` / `heart-rate` / `sleep` / `workouts` | Query cache |

## JSON success shape (`--json-output`)

```json
{ "status": 200, "body": { } }
```

## Paths

- DB: `~/.local/share/apple-health/health.db`
- iOS app: `tools/apple-health-cli/ios/AHPSync.xcodeproj`
