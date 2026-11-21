# FNP — Feishu Notify Protocol (v1)

Harness-agnostic JSON contract for `fnotify send`. Any agent runtime (Cursor, Codex, Claude, Pi, DeepSeek, shell, CI) emits the same envelope.

## Defaults (product)

| Setting | Value |
|---------|--------|
| Default route | `dm_self` — Bot P2P with you |
| Default identity | `bot` |
| `agent.progress` format | `card` |
| Progress delivery | **M2**：同 `run_id` 首条 `send`，后续 **patch** 同一张卡 |
| Scenes | Only built-in templates in this package (no `custom` + external `card.json`) |

## Envelope

```json
{
  "fnp_version": 1,
  "scene": "agent.conclusion",
  "scene_version": "1.0",
  "format": "auto",
  "identity": "auto",
  "route": "dm_self",
  "locale": "zh_cn",
  "payload": { },
  "context": {
    "harness": "cursor",
    "run_id": "required for agent.progress when progress.mode=m2",
    "trace_id": "optional"
  },
  "delivery": {
    "mode": "auto",
    "message_id": "optional; used when mode=patch"
  }
}
```

### M2 progress (`progress.mode: m2`)

1. First `agent.progress` for `context.run_id` → **`send`** → stores `message_id` in `~/.config/fnotify/runs.json`.
2. Later `agent.progress` with same `run_id` → **`patch`** that card (`lark-cli im messages patch`).
3. Terminal scenes (`agent.conclusion`, `agent.failure`, …) **clear** the binding for that `run_id` after send.
4. Force M1-style: `"delivery": {"mode": "send"}` on a single envelope.
5. Explicit patch: `fnotify patch --stdin` or `"delivery": {"mode": "patch", "message_id": "om_xxx"}`.

### Top-level fields

| Field | Required | Notes |
|-------|----------|-------|
| `fnp_version` | yes | Must be `1` |
| `scene` | yes | Built-in scene id (see `fnotify scenes list`) |
| `scene_version` | no | Default `1.0` |
| `format` | no | `auto` \| `text` \| `card` |
| `identity` | no | `auto` \| `bot` \| `user` |
| `route` | no | Config alias, default `dm_self` |
| `locale` | no | Default `zh_cn` |
| `payload` | yes | Scene-specific body (see below) |
| `context` | no | Metadata only; not shown unless template uses it |

### Common `payload` shape

Most scenes accept a shared subset:

| Field | Type | Notes |
|-------|------|-------|
| `title` | string | Header / first line |
| `summary` | string | Short text; required for most scenes |
| `status` | string | `success` \| `partial` \| `failed` \| `cancelled` \| `running` \| `info` |
| `fields` | array | `{ "label", "value" }[]` key-value rows |
| `body_md` | string | Long markdown; may become attachment when over limit |
| `actions` | array | `{ "id", "label", "kind": "url"\|"callback", "href"?, "value"? }` |
| `artifacts` | array | `{ "kind": "file"\|"url", "path"?, "href"?, "label"? }` |

**Rules**

- `actions` with `kind: callback` → forces `identity: bot` and `format: card`.
- Long `body_md` → file attachment + short summary in message (see `max_body_chars` in config).

## Identity (`auto`)

1. Any callback action → `bot`
2. Scene manifest `default_identity`
3. Global config `default_identity` (default `bot`)
4. Explicit `identity` on envelope wins if not `auto`

## Format (`auto`)

1. Callback actions → `card`
2. Scene manifest `default_format` (e.g. `agent.progress` → `card`)
3. If `fields` empty and no actions → may use `text` for `notify.plain`
4. `status: failed` on `agent.failure` / `agent.alert` → `card`

## CLI response (`--json-output`)

```json
{
  "status": 200,
  "headers": {},
  "body": {
    "ok": true,
    "dry_run": false,
    "scene": "agent.conclusion",
    "format_used": "card",
    "delivered_as": "bot",
    "route": "dm_self",
    "message_id": "om_xxx",
    "chat_id": null,
    "user_id": "ou_xxx"
  }
}
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Invalid FNP / unknown scene |
| 3 | Config missing or lark-cli auth failure |
| 5 | lark-cli delivery failed |
| 10 | Validation / render error |

## Config

`~/.config/fnotify/config.yaml` (see `fnotify install`).

```yaml
version: 1
default_route: dm_self
default_identity: bot
max_body_chars: 12000
routes:
  dm_self:
    type: bot_p2p
    user_id: ou_xxxxxxxx
redact_patterns: []
```

## Built-in scenes (v0.1)

| Scene | Purpose |
|-------|---------|
| `notify.plain` | Generic one-off notice（**默认卡片**） |
| `agent.ack` | Inbound command acknowledged |
| `agent.progress` | Throttled progress (card) |
| `agent.conclusion` | Successful completion |
| `agent.partial` | Partial success |
| `agent.failure` | Failed run |
| `agent.cancelled` | Cancelled run |
| `agent.alert` | Urgent attention |
| `agent.approval` | Human confirm / approve buttons |
| `agent.report` | Daily or work report |
| `agent.link_digest` | Links + short summary |
| `agent.artifact_ready` | File / artifact delivery |