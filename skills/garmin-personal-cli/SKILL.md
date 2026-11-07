---
name: garmin-personal-cli
description: >-
  Guides agents to query Garmin Connect Personal API via the `gmp` / `garmin-personal`
  CLI (multi-profile API keys, China-default host). Use when the user mentions Garmin,
  佳明, Connect Personal, steps, sleep, activity, HRV, body battery, or exporting watch
  data programmatically.
---

# Garmin Personal API CLI (Skill)

## What this is

- **CLI**: `gmp` or `garmin-personal` — calls Garmin Personal API with per-user API keys.
- **`gmp`** = **`gm`** (from **Garmin**) + **`p`** (from **personal**).

## Hard rules

1. **Personal API = own data only.** Each Garmin user must use **their own** [Personal API key](https://connect.garmin.com/app/settings/personalApiToken).
2. **Do not** use one key to aggregate multiple people’s data.
3. Default API host: **`https://personal.connectapi.garmin.cn`**. Override with `GARMIN_API_BASE` / profile if needed.
4. Prefer **`--profile`** when multiple keys exist on one machine.

## Install (user machine)

1. **Python CLI** (required):

   ```bash
   git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools
   ./scripts/install.sh
   ```

   After `pipx install` alone, users must run **`gmp setup`** (same text as `install.sh` prints). Then `gmp profile add default --default "<key>"`.

2. **Skill / knowledge** (optional): import this file or the whole repo’s `skills/garmin-personal-cli/`.

3. **Open skills ecosystem** (Node):

   ```bash
   npx skills add mxz2023/MyWikiTools@garmin-personal-cli -g -y
   ```

   Confirm the exact `@subpath` with `npx skills add --help` and [skills.sh](https://skills.sh/).

## Configure keys

```bash
gmp profile add alice --default "<personal-api-key>"
export GARMIN_API_KEY="<key>"        # alternative
# Optional: only if a profile named alice exists
export GARMIN_PROFILE="alice"
```

Precedence: `--api-key` > `GARMIN_API_KEY` > profile file (`~/.config/garmin-personal/config.toml`). If `GARMIN_PROFILE` is unset, default profile from config is used.

## Patterns for agents

- **Structured stdout** for parsing:

  ```bash
  gmp request GET '/userprofile-service/userprofile/settings' --json-output
  ```

- **Exit codes**: `0` ok; `3` missing credentials; `4` HTTP 4xx; `5` HTTP 5xx (see `gmp --help`).
- **Help language**: `--lang both|en|zh`, or `GARMIN_CLI_LANG`.

## Examples

Replace dates and IDs. Use `--profile` when multiple keys exist.

```bash
gmp --profile alice steps --start-date 2026-08-20 --end-date 2026-08-24 --json-output
gmp sleep --date 2026-08-24
gmp activities --start 0 --limit 20 --start-date 2026-08-01
gmp activity 123456789
gmp activity-download 123456789 -o ./activity-123456789.zip
gmp request GET '/userprofile-service/userprofile/settings'
```

## References

- [Official FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/)
- [Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)
