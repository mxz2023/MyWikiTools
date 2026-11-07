# garmin-personal-cli

[简体中文](README.zh.md)

Part of the [MyWikiTools](../../README.md) monorepo (`tools/garmin-personal-cli/`).

**Repository:** [github.com/mxz2023/MyWikiTools](https://github.com/mxz2023/MyWikiTools)

CLI for [Garmin Connect Personal API](https://developer.garmin.com/gc-developer-program/personal/personal-api): **multi-profile API keys**, **China-default host** (`personal.connectapi.garmin.cn`), and **`--json-output`** for agents.

| Entry | Command |
|-------|---------|
| Short | **`gmp`** |
| Long | **`garmin-personal`** |

> **Naming**: **`gmp`** = **`gm`** (from **Garmin**) + **`p`** (from **personal**).

## Quick start

1. Install **pipx** (isolates CLI apps; [docs](https://pipx.pypa.io/)):

   ```bash
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```

   Then **open a new terminal** (or `source ~/.zshrc`) so `pipx` is on your `PATH`.

2. Install (pick one):

   **Helper script** (after pipx, prints key + `profile add` steps):

   ```bash
   git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools
   ./scripts/install.sh
   ```

   Or pipx only (**pipx does not run our onboarding**; then run):

   ```bash
   pipx install "git+https://github.com/mxz2023/MyWikiTools.git@master#subdirectory=tools/garmin-personal-cli"
   gmp setup
   ```

   From a clone:

   ```bash
   git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools
   pipx install ./tools/garmin-personal-cli
   ```

3. If you did not use `install.sh`, add your [Personal API key](https://connect.garmin.com/app/settings/personalApiToken):

   ```bash
   gmp profile add default --default "<your-api-key>"
   ```

4. Try:

   ```bash
   gmp profile-settings
   gmp --help
   ```

## Requirements

- Python **3.11+** (used by pipx’s venv for this app)
- Network access to Garmin (use `HTTPS_PROXY` / `HTTP_PROXY` behind a corporate proxy)

## Install (reference)

### pipx (recommended for daily use)

Same as [Quick start](#quick-start). Prefer **`python3 -m pip install --user pipx`** instead of plain `pip install pipx` so you don’t mix with the system interpreter.

### Editable install (development)

```bash
git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools/tools/garmin-personal-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
gmp --help
```

### Verify

```bash
which gmp garmin-personal
gmp version
```

If `command not found` after `pipx install`, ensure `pipx ensurepath` ran and your shell picked up `~/.local/bin`.

## Personal API key

Create a key in the browser: [Personal API Tokens](https://connect.garmin.com/app/settings/personalApiToken).

**Profiles** (one key per Garmin user on this machine):

```bash
gmp profile add alice --default "<alice-api-key>"
gmp profile list
```

**Or** environment variables (good for CI / one-off):

```bash
export GARMIN_API_KEY="your-key"
# Optional: only if you created a profile with this exact name
export GARMIN_PROFILE="alice"
```

If `GARMIN_PROFILE` is unset, the CLI uses `default_profile` from config (or the first profile found).

Precedence: **`--api-key` > `GARMIN_API_KEY` > profile `api_key` in `~/.config/garmin-personal/config.toml`**.

## Defaults

| Item | Default |
|------|---------|
| API base | `https://personal.connectapi.garmin.cn` |
| Token URL | `{api_base}/personalapitoken-service/personal-api/personal-api-key/token` |

**Global override:**

```bash
export GARMIN_API_BASE="https://personal.connectapi.garmin.com"
export GARMIN_TOKEN_URL="https://personal.connectapi.garmin.com/personalapitoken-service/personal-api/personal-api-key/token"
```

**Per profile** (stored in config):

```bash
gmp profile add work YOUR_KEY --api-base https://personal.connectapi.garmin.com
```

Config directory: **`~/.config/garmin-personal/`** (config + bearer token cache).

## Help language

- **`--lang both`** (default): English / 中文 where the CLI shows fixed strings.
- **`--lang en`** | **`--lang zh`**: single language.
- **`GARMIN_CLI_LANG`**: `both` | `en` | `zh`.

## Common commands

```bash
gmp steps --start-date 2026-08-20 --end-date 2026-08-24
gmp sleep --date 2026-08-24
gmp activities --start 0 --limit 20
gmp activity 123456789
gmp activity-download 123456789 -o ./run.zip
gmp request GET '/userprofile-service/userprofile/settings'
gmp request GET '/userprofile-service/userprofile/settings' --json-output
```

See also **`gmp COMMAND --help`** and [Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General / other error |
| 2 | Usage / bad arguments |
| 3 | Missing config / credentials |
| 4 | HTTP 4xx |
| 5 | HTTP 5xx |

## Agent Skill (Cursor & others)

Canonical: [`skills/garmin-personal-cli/SKILL.md`](skills/garmin-personal-cli/SKILL.md) only (one skill directory, one `SKILL.md`; symlinked under `.cursor/skills/` for Cursor).

**Open skills CLI** (needs Node):

```bash
npx skills add mxz2023/MyWikiTools@garmin-personal-cli -g -y
```

Confirm `@…` with `npx skills add --help` and [skills.sh](https://skills.sh/) after you publish.

**Other agents (Codex, Pi, Workbuddy, …):** point “knowledge” / instructions at that `SKILL.md` or the raw URL  
`https://raw.githubusercontent.com/mxz2023/MyWikiTools/master/skills/garmin-personal-cli/SKILL.md`.

## Compliance

- Personal API is **only for your own data**. One key per Garmin user; don’t aggregate others’ data.
- Keys are shown **once** in the Garmin UI — store them safely.

## Related

- [Official FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/)
- [Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)
- [connect-personal-api-python](https://github.com/garmin/connect-personal-api-python) (reference client)

## License

Apache-2.0
