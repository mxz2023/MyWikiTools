# 小米运动健康 CLI（`mfp`）

在 Mac 上把 **小米运动健康** 云端数据同步到本地 SQLite，并用命令行或 Agent 查询。

**非官方工具**，与小米无隶属关系。

## 数据流

手表/体脂秤 → 小米运动健康 App → 小米云端 → **`mfp sync`** → Mac SQLite

CLI 不直连设备，只读取与 App 一致的云端数据。

## 安装

```bash
./tools/mi-fitness-cli/scripts/install.sh
mfp setup
```

## 登录方式

| 方式 | 命令 |
|------|------|
| 扫码 | `mfp login`（见下方说明，**不要用运动健康 App 内扫码**） |
| passToken（推荐若扫码失败） | `mfp login --pass-token … --user-id …` |
| 导入会话 | `mfp login import session.json` |

环境变量：`MI_FITNESS_USER_ID`、`MI_FITNESS_PASS_TOKEN`（无会话文件时）。

### 扫码登录说明

`mfp login` 会在 Mac 上用「预览」打开**小米账号官方二维码**。请用手机 **设置 → 小米账号 → 扫一扫**（或「小米账号」类 App），**不要**用「小米运动健康」App 里的扫码入口，否则会提示「暂不支持此二维码」。

若仍失败，在浏览器登录 [account.xiaomi.com](https://account.xiaomi.com) 后，从 Cookie 复制 `userId` / `passToken`，执行 passToken 登录。

## 同步

```bash
mfp sync --days 30
mfp sync --start-date 2026-01-01 --end-date 2026-03-01
mfp sync --type sleep --days 14
```

支持类型：`daily_activity`、`sleep`、`heart_rate`、`workouts`、`body_measurements`（含体脂秤上云后的体重/体成分）。

## 查询

```bash
mfp doctor --json-output
mfp status --json-output
mfp steps --days 7 --json-output
mfp weight --full --json-output
```

## 定时同步（示例）

```bash
# crontab: 每天 6:00 拉最近 7 天
0 6 * * * /Users/you/.local/bin/mfp sync --days 7 --json-output
```

## 路径

- 凭证：`~/.config/mi-fitness/session.json`（权限 600）
- 数据库：`~/.local/share/mi-fitness/health.db`

## 免责声明

使用逆向消费者接口，可能不符合小米服务条款；仅用于访问**本人**账号数据，风险自负。
