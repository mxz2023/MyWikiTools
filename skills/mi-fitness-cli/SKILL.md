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

## Morning weight sync for MyWiki

When the user explicitly says they have just woken up, the MyWiki health workflow may sync their Xiaomi scale data:

1. Determine the target wake-up date in `Asia/Shanghai` (use the user's specified date when given). Compute the inclusive three-calendar-day window as target date minus two days through target date.
2. Sync only body measurements for that explicit window:

   ```bash
   mfp sync --start-date YYYY-MM-DD --end-date YYYY-MM-DD --type body_measurements --json-output --json-errors
   ```

3. Check process exit status and the JSON envelope. If sync succeeds, query the same inclusive window:

   ```bash
   mfp weight --start YYYY-MM-DD --end YYYY-MM-DD --full --json-output
   ```

4. Inspect the returned `items`; choose the newest item with a non-null numeric `weight_kg` and a parseable `measured_at` inside the window. Do not infer a measurement date from sync time or assume a scale reading happened on the wake-up date. The MyWiki health agent records that value on its actual measurement date and sets the source to `小米运动健康`; only the weight and source may be replaced on that date.
5. If there is no valid measurement in the three-day window, leave any existing record values untouched, keep a missing weight blank, and prompt the user to enter today's morning weight. If synchronization or query fails, credentials are unavailable, or the returned date/value cannot be verified, do not write a weight and report the specific gap.

This workflow reads the local cache after syncing; the scale measurement must have reached Xiaomi's cloud to be available. Do not print, copy, or log session credentials.

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
