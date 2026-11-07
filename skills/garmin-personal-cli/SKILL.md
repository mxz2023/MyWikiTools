---
name: garmin-personal-cli
description: >-
  Query the user's own Garmin Connect data only via `gmp` / `garmin-personal` CLI
  (--json-output envelope). Use for 佳明/Garmin, steps, sleep, 睡眠, activities,
  运动/跑步/跑步机, HRV, body battery, stress, hydration, weight, food, SpO2,
  menstrual cycle, fitness age — never fetch Garmin developer Swagger/FAQ to guess APIs.
---

# Garmin Personal API CLI (Agent Skill)

## What this is

- **CLI**: `gmp` or `garmin-personal` — Personal API with per-user keys.
- **`gmp`** = **`gm`** (Garmin) + **`p`** (personal).
- **Command catalog**: [reference.md](reference.md) in this directory (all data commands + HTTP paths). Read it when picking a subcommand.

## Hard rules

1. **Own data only** — one [Personal API key](https://connect.garmin.com/app/settings/personalApiToken) per Garmin user; never aggregate others with one key.
2. **Do not** use WebFetch/WebSearch to read `developer.garmin.com` Swagger, FAQ, or API docs to guess endpoints. This CLI already wraps Personal API GETs — use `gmp <command>` from [reference.md](reference.md) or `gmp request GET '…'`.
3. **Exception**: guiding the user to **create/rotate API key** in the browser (same URL as `gmp setup`) is allowed; that is not “looking up API shape”.
4. Default API host: **`https://personal.connectapi.garmin.cn`** (`GARMIN_API_BASE` / profile `--api-base` to override).
5. Multiple keys on one machine: **`gmp -p PROFILE`** before data commands.
6. **Data queries**: always **`--json-output --json-errors`** unless the user explicitly wants human-only output.
7. **Never invent** JSON field names inside `body` before running a command; parse the real response after exit 0.

## Install (user machine)

```bash
git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools
./scripts/install.sh
```

```bash
pipx install "git+https://github.com/mxz2023/MyWikiTools.git@master#subdirectory=tools/garmin-personal-cli"
gmp setup
gmp profile add default --default "<personal-api-key>"
```

Open skills: `npx skills add mxz2023/MyWikiTools@garmin-personal-cli -g -y`

## Credentials

Precedence: `--api-key` > `GARMIN_API_KEY` > `~/.config/garmin-personal/config.toml`.

```bash
gmp profile add alice --default "<key>"
gmp -p alice profile-settings --json-output
```

## Agent I/O contract

### Global options (before subcommand)

| Option | Meaning |
|--------|---------|
| `-p, --profile` | Profile name (default from config) |
| `--api-key` | Override profile key |
| `-t, --timeout` | HTTP timeout seconds (default 30) |
| `-q, --quiet` | Less stderr |
| `--lang` | CLI help language only (`both`/`en`/`zh`); does not change API data |

### Recommended on every data command

| Option | Meaning |
|--------|---------|
| `--json-output` | Single JSON object on stdout (envelope below) |
| `--json-errors` | On failure, stderr JSON `{"error","text"}` |

### `--json-output` stdout (success)

```json
{
  "status": 200,
  "headers": { "content-type": "application/json" },
  "body": null
}
```

| Field | Meaning |
|-------|---------|
| `status` | HTTP status code |
| `headers` | Response headers |
| `body` | **Garmin payload** — object, array, string, or **`null`** (e.g. HTTP 204 / no rows for date range). Not always an auth error; check exit code and `status`. |

Without `--json-output`, stdout is raw `body` only — **agents should not rely on that**.

### Exit codes

| Code | Meaning | Agent action |
|------|---------|----------------|
| 0 | Success | Parse stdout JSON |
| 3 | Missing credentials | Ask user to `gmp profile add` or set `GARMIN_API_KEY` |
| 4 | HTTP 4xx | Read `--json-errors`; do not guess URLs |
| 5 | HTTP 5xx | Retry lightly or ask user to retry later |

### Special I/O

- **`activity-download`**: binary ZIP at `-o`; use `activities` / `activity` for Q&A.
- **`auth print-token`**: debug only; do not echo token to user.

## Intent → command (routing)

Use [reference.md](reference.md) for full args and examples.

| User intent (examples) | Subcommand |
|------------------------|------------|
| Verify key / profile | `profile-settings` |
| Steps in date range | `steps` |
| Stress / hydration | `stress`, `hydration` |
| Weight goals / weigh-ins | `effective-weight-goals`, `weight-measurements` |
| Food one day | `food-logs` |
| Sleep one day / range | `sleep`, `sleep-summaries` |
| Body Battery | `body-battery` |
| Daily wellness rollup | `daily-summaries` |
| Heart rate / HRV | `heart-rate`, `hrv`, `hrv-summaries` |
| HR zones config | `heart-rate-zones` |
| SpO2 | `spo2` |
| Fitness age | `fitness-age` |
| Menstrual cycle | `menstrual-cycle-summary`, `menstrual-cycle-day-view` |
| **Workouts list / yesterday’s run / treadmill** | `activities` → then `activity <id>` |
| Activity laps / segments | `activity-workouts <id>` |
| Download activity file | `activity-download <id> -o path` |
| **Daily activity stats (not each workout)** | `wellness-activity-summaries` |
| Nothing in reference | `request GET '/path'` |

**Prefer convenience commands** over `request`.

### Worked example: yesterday’s treadmill run

User: “昨天跑步机上跑了多久？”

1. Resolve yesterday from **the user’s current calendar** (`date` / context) as `YYYY-MM-DD` — never copy example years from docs (e.g. 2025) as “yesterday”.
2. `gmp activities --start 0 --limit 50 --start-date DATE --end-date DATE --json-output --json-errors`
3. From `body`, find indoor/treadmill run; note `activityId`.
4. If user wants detail: `gmp activity ACTIVITY_ID --json-output --json-errors`
5. Answer in natural language from parsed `body` (duration, distance if present, calories, HR). Do not quote full JSON unless asked.

**`wellness-activity-summaries`** is for per-day activity *summaries*, not the list of individual treadmill sessions.

## Standard workflow

```bash
gmp profile-settings --json-output --json-errors
gmp -p PROFILE steps --start-date YYYY-MM-DD --end-date YYYY-MM-DD --json-output --json-errors
```

Dates: **YYYY-MM-DD**, inclusive endpoints on range commands.

## Output fields: who documents what

| Layer | Documented here | Notes |
|-------|-----------------|-------|
| Envelope + CLI flags + exit codes | This SKILL + [reference.md](reference.md) | Source of truth: CLI code |
| Garmin `body` shape | `reference.md` **「响应（实测 API）」** | From real `gmp ... --json-output` on cn host; re-verify when APIs change |
| Every nested Garmin field | Not a full Swagger dump | Parse actual JSON after run |

**Maintainership**: before changing response docs, run the command locally and update `RESP_VERIFIED` in [generate_skill_reference.py](../../tools/garmin-personal-cli/scripts/generate_skill_reference.py), then regenerate reference.

### Verified facts (sample — see reference for per-command)

- `activities`: `body` is a **JSON array**; treadmill runs use `activityType.typeKey` = `treadmill_running`; duration/distances on each item are enough for many questions.
- `activity`: detail metrics often live under **`body.summaryDTO`**, not only top-level keys.
- `steps`: `body` is an array of `{calendarDate, totalSteps, totalDistance, stepGoal}`.

## Canonical reference

All subcommands, HTTP templates, CLI parameters, and examples: **[reference.md](reference.md)**.

Do not link agents to Garmin Swagger/FAQ for API discovery.
