# MyWikiTools

[English](README.md)

**仓库：** [github.com/mxz2023/MyWikiTools](https://github.com/mxz2023/MyWikiTools)

多个 **CLI 小工具** 的 monorepo（一般用 **pipx** 按工具单独安装）。Agent **Skill** 统一放在仓库根目录的 `skills/`。

## 工具列表

| 工具 | 命令 | 目录 | 文档 |
|------|------|------|------|
| Garmin Personal API | `gmp`、`garmin-personal` | [`tools/garmin-personal-cli/`](tools/garmin-personal-cli/) | [README](tools/garmin-personal-cli/README.zh.md) |
| Apple 健康 / 手表 | `ahp`、`apple-health` | [`tools/apple-health-cli/`](tools/apple-health-cli/) | [README](tools/apple-health-cli/README.zh.md) |
| 小米运动健康 | `mfp`、`mi-fitness` | [`tools/mi-fitness-cli/`](tools/mi-fitness-cli/) | [README](tools/mi-fitness-cli/README.zh.md) |

**安装 Garmin CLI**（已克隆仓库）：

```bash
./scripts/install.sh
# 等价于 ./tools/garmin-personal-cli/scripts/install.sh
```

**从 GitHub 安装**（无需克隆）：

```bash
pipx install "git+https://github.com/mxz2023/MyWikiTools.git@master#subdirectory=tools/garmin-personal-cli"
gmp setup
```

## 目录约定

```
MyWikiTools/
├── README.md
├── skills/                          # 每个工具一个 Skill 目录
│   └── <tool>-cli/SKILL.md
├── tools/
│   └── <tool>-cli/
│       ├── pyproject.toml           # 独立包与入口命令
│       ├── README.md / README.zh.md
│       ├── src/<python_package>/
│       ├── tests/
│       └── scripts/install.sh       # 可选
└── scripts/
    ├── install.sh                   # 便捷安装（如默认工具）
    └── test-all.sh                  # 跑各工具测试
```

## 新增 CLI 的步骤

1. 参照 `tools/garmin-personal-cli/` 新建 `tools/<tool>-cli/`。
2. 增加 `skills/<tool>-cli/SKILL.md`；Cursor 可用 `.cursor/skills/<tool>-cli` 链到 `skills/`。
3. 在本 README 表格中登记。
4. 按需更新 `scripts/test-all.sh`。

## Agent Skill

Skill 路径固定在 **`skills/<tool>-cli/`**，以便  
`npx skills add mxz2023/MyWikiTools@garmin-personal-cli` 等引用方式不变。

各工具用法见 `tools/` 下对应 README。

## 许可

Apache-2.0（以各工具包内说明为准）。
