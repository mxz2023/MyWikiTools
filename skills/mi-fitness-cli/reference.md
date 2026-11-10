# `mfp` command reference

## Global

| Option | Meaning |
|--------|---------|
| `--json-output` | Envelope: `status`, `headers`, `body` |
| `--json-errors` | `{"error": "<message>"}` on stderr |

## Commands

| Command | Purpose |
|---------|---------|
| `setup` | Onboarding |
| `doctor` | Session + cloud probe |
| `status` | Session + DB counts |
| `login` | QR login (default) |
| `login --pass-token --user-id` | Cookie login |
| `login import PATH` | Restore session file |
| `logout` | Delete session |
| `sync` | `--days`, `--start-date`, `--end-date`, `--type` (repeatable) |
| `steps` / `sleep` / `heart-rate` / `workouts` / `weight` | Query cache |
| `weight --full` | Include body composition JSON |
| `request PATH --data '{}'` | Debug signed API call |

For a date-bounded weight query, use `mfp weight --start YYYY-MM-DD --end YYYY-MM-DD --full --json-output`; `items` are ordered newest measurement first and include `measured_at` and `weight_kg`. Use explicit dates when the requested window follows a timezone other than the host's local date.

## Sync `--type` values

- `daily_activity` — steps, distance
- `sleep`
- `heart_rate` — daily summary
- `workouts`
- `body_measurements` — weight, BMI, composition (from cloud `weight` key)
