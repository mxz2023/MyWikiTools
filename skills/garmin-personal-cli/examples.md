# Examples

Replace dates and IDs with real values. Use `--profile` if you have multiple keys.

## Steps (range)

```bash
gmp --profile alice steps --start-date 2026-08-20 --end-date 2026-08-24 --json-output
```

## Sleep (one night)

```bash
gmp sleep --date 2026-08-24
```

## List activities

```bash
gmp activities --start 0 --limit 20 --start-date 2026-08-01
```

## Activity detail + ZIP download

```bash
gmp activity 123456789
gmp activity-download 123456789 -o ./activity-123456789.zip
```

## Arbitrary GET

```bash
gmp request GET '/userprofile-service/userprofile/settings'
```
