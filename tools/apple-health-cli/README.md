# Apple Health CLI (`ahp`)

Receive **Apple Watch / iPhone Health** data on your Mac via the free **AHPSync** iOS app, store in SQLite, query with CLI.

Commands: **`ahp`** or **`apple-health`**.

## Data flow

Apple Watch → iPhone Health → **AHPSync** → Wi‑Fi → **`ahp serve`** → `~/.local/share/apple-health/health.db`

macOS does **not** expose HealthKit to third-party apps; sync always goes through the iPhone app.

## Install CLI

```bash
pipx install ./tools/apple-health-cli
# or: ./tools/apple-health-cli/scripts/install.sh
ahp setup
```

## Mac: receive sync

```bash
export AHP_INGEST_TOKEN='your-secret'
ahp serve --host 0.0.0.0 --port 8765
```

## iPhone: AHPSync

See [ios/README.zh.md](ios/README.zh.md) — open `ios/AHPSync.xcodeproj` in Xcode, install on device.

## Query cache

```bash
ahp status --json-output
ahp steps --days 7 --json-output
ahp sleep --days 14 --json-output
ahp workouts --days 30 --json-output
```

## Optional

- **Bulk import:** `ahp import path/to/export.xml`
- **Folder watch:** `ahp watch` (iCloud `AHP/` drops)

## Paths

| Path | Purpose |
|------|---------|
| `~/.local/share/apple-health/health.db` | SQLite cache |

## Agent usage

Use `--json-output`. Ensure `ahp serve` is running before expecting new data from the phone.
