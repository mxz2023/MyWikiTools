# Mi Fitness CLI (`mfp`)

Sync your **Xiaomi Mi Fitness** (小米运动健康) cloud data to a local SQLite database on macOS and query it from the terminal or AI agents.

**Unofficial.** Not affiliated with Xiaomi.

## Install

```bash
./tools/mi-fitness-cli/scripts/install.sh
mfp setup
```

## Login

```bash
mfp login
# or
mfp login --pass-token "<passToken>" --user-id "<userId>"
mfp login import /path/to/session.json
```

## Sync & query

```bash
mfp sync --days 30
mfp steps --days 7 --json-output
mfp sleep --days 7 --json-output
mfp weight --full --json-output
```

Session: `~/.config/mi-fitness/session.json`  
Database: `~/.local/share/mi-fitness/health.db`

See [README.zh.md](README.zh.md).
