# garmin-personal-cli

[English](README.md)

**仓库：** [github.com/mxz2023/MyWikiTools](https://github.com/mxz2023/MyWikiTools)

[Garmin Connect Personal API](https://developer.garmin.com/gc-developer-program/personal/personal-api) 的命令行客户端：支持**多配置档 API Key**、**默认中国区**（`personal.connectapi.garmin.cn`）、以及便于 Agent 解析的 **`--json-output`**。

| 短命令 | 长命令 |
|--------|--------|
| **`gmp`** | **`garmin-personal`** |

> **命名**：**`gmp`** = **`gm`**（取自 Garmin）+ **`p`**（取自 personal）。

## 快速开始

1. 安装 **pipx**（为每个 CLI 单独建虚拟环境，互不污染；见 [pipx 文档](https://pipx.pypa.io/)）：

   ```bash
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```

   执行 **`pipx ensurepath`** 后请 **新开一个终端**（或 `source ~/.zshrc`），保证 `PATH` 中有 `~/.local/bin`。

2. 安装本工具（任选其一）：

   **一键脚本**（安装结束后会提示申请 Key 与配置命令）：

   ```bash
   git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools
   ./scripts/install.sh
   ```

   或仅 pipx（**pipx 不会自动弹出引导**，装完后请执行 `gmp setup`）：

   ```bash
   pipx install "git+https://github.com/mxz2023/MyWikiTools.git@master"
   gmp setup
   ```

   克隆后本地安装：

   ```bash
   git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools
   pipx install .
   ```

3. 若未用 `install.sh`，在浏览器中创建 [个人 API 密钥](https://connect.garmin.com/app/settings/personalApiToken)，并写入配置档：

   ```bash
   gmp profile add default --default "<你的-api-key>"
   ```

4. 试跑：

   ```bash
   gmp profile-settings
   gmp --help
   ```

## 环境要求

- Python **3.11+**（pipx 为 `gmp` 创建环境时会用到）
- 能访问 Garmin 接口（公司网络可设 `HTTPS_PROXY` / `HTTP_PROXY`）

## 安装（补充说明）

### 日常使用：pipx

与上文 [快速开始](#快速开始) 相同。建议用 **`python3 -m pip install --user pipx`**，避免与系统自带 `pip` 混用。

### 开发：可编辑安装

```bash
git clone https://github.com/mxz2023/MyWikiTools.git && cd MyWikiTools
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
gmp --help
```

### 安装结果检查

```bash
which gmp garmin-personal
gmp version
```

若提示 `command not found`，确认已执行 **`pipx ensurepath`** 且 shell 已加载 **`~/.local/bin`**。

## 个人 API 密钥

浏览器中创建：[Personal API Tokens](https://connect.garmin.com/app/settings/personalApiToken)。

**多用户（多配置档）**：

```bash
gmp profile add alice --default "<alice-的-key>"
gmp profile list
```

**或使用环境变量**（适合 CI / 临时使用）：

```bash
export GARMIN_API_KEY="你的密钥"
# 可选：仅当你已用该名称创建过配置档时设置
export GARMIN_PROFILE="alice"
```

未设置 `GARMIN_PROFILE` 时，使用配置文件中的 `default_profile`（或第一个已有配置档）。

优先级：**`--api-key` > `GARMIN_API_KEY` > 配置文件中的 `api_key`**（路径 `~/.config/garmin-personal/config.toml`）。

## 默认配置

| 项 | 默认值 |
|----|--------|
| API 根地址 | `https://personal.connectapi.garmin.cn` |
| Token URL | `{api_base}/personalapitoken-service/personal-api/personal-api-key/token` |

**全局覆盖：**

```bash
export GARMIN_API_BASE="https://personal.connectapi.garmin.com"
export GARMIN_TOKEN_URL="https://personal.connectapi.garmin.com/personalapitoken-service/personal-api/personal-api-key/token"
```

**按配置档**（写入配置文件）：

```bash
gmp profile add work YOUR_KEY --api-base https://personal.connectapi.garmin.com
```

配置目录：**`~/.config/garmin-personal/`**（含 token 缓存）。

## 帮助语言

- **`--lang both`**（默认）：固定文案尽量英/中对照。
- **`--lang en`** / **`--lang zh`**：单一语言。
- **`GARMIN_CLI_LANG`**：`both` | `en` | `zh`。

## 常用命令

```bash
gmp steps --start-date 2026-08-20 --end-date 2026-08-24
gmp sleep --date 2026-08-24
gmp activities --start 0 --limit 20
gmp activity 123456789
gmp activity-download 123456789 -o ./run.zip
gmp request GET '/userprofile-service/userprofile/settings'
gmp request GET '/userprofile-service/userprofile/settings' --json-output
```

更多子命令见 **`gmp --help`** 与 [Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)。

## 退出码

| 码 | 含义 |
|----|------|
| 0 | 成功 |
| 1 | 一般错误 |
| 2 | 用法 / 参数错误 |
| 3 | 缺少配置或凭证 |
| 4 | HTTP 4xx |
| 5 | HTTP 5xx |

## Agent Skill（Cursor 等）

规范文档：[`skills/garmin-personal-cli/SKILL.md`](skills/garmin-personal-cli/SKILL.md)（目录内仅含 `SKILL.md`，符合常见 Agent Skill 最小结构；Cursor 下 `.cursor/skills/` 为符号链接）。

**Open skills**（需安装 Node）：

```bash
npx skills add mxz2023/MyWikiTools@garmin-personal-cli -g -y
```

`@` 后子路径以发布后的仓库与 `npx skills add --help`、[skills.sh](https://skills.sh/) 为准。

**其他 Agent**：在知识库/说明中引用该 `SKILL.md` 或 raw 链接  
`https://raw.githubusercontent.com/mxz2023/MyWikiTools/master/skills/garmin-personal-cli/SKILL.md`。

## 合规说明

- Personal API **仅用于本人数据**；每人使用自己的 Key，不要用一把 Key 汇总他人数据。
- 密钥在网页上**只完整显示一次**，请妥善保管。

## 相关链接

- [官方 FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/)
- [Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)
- [connect-personal-api-python](https://github.com/garmin/connect-personal-api-python)

## 许可证

Apache-2.0
