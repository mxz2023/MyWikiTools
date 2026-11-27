# MyWikiTools 开发流程

目标：**新功能在独立 worktree 里开发与验证，不影响线上默认分支上的现有功能**；集成到 `develop` 后由维护者验收；稳定后再进 `master`。

## 分支

| 分支 | 含义 |
|------|------|
| `master` | 对外默认稳定（如 `pipx install …@master`） |
| `develop` | 日常集成；可多特性并存，但每项应先在自己的 worktree 验证后再合入 |
| `tool/<名>` | 新工具或大改某一工具 |
| `feature/<名>` | 跨工具能力、文档、规则、共享库 |
| `fix/<名>` | 缺陷修复 |

## 标准路径

```mermaid
flowchart LR
  WT[.worktrees/slug 开发+自测]
  DEV[develop 集成]
  YOU[你验收]
  MAS[master 发布]
  WT -->|PR 或 merge| DEV
  DEV --> YOU
  YOU -->|确认无问题| MAS
```

1. **`git fetch`**，从 **`origin/develop`** 创建 worktree 与分支。
2. 在 **`.worktrees/<slug>`** 内完成实现、文档、测试。
3. 推送分支，合并到 **`develop`**（建议 PR，便于看 diff 与 CI）。
4. **你在 develop 环境做最后验证**（真实配置、daemon、联调等）。
5. 全部满意后 **`develop` → `master`**，再按需打 tag / 安装发布。

合并到 develop 后清理 worktree：

```bash
./scripts/worktree-finish.sh <slug>
```

## Worktree 约定

| 项 | 约定 |
|----|------|
| 路径 | 仅 `MyWikiTools/.worktrees/<slug>` |
| 打开方式 | Cursor / 终端以该目录为项目根 |
| 分支名 | 与 slug 对应：`tool/foo` → `.worktrees/foo` |

新工具详见 [TOOL_DEVELOPMENT.zh.md](./TOOL_DEVELOPMENT.zh.md)。

## 隔离与低耦合

- 单 worktree 只交付**一件事**；禁止「顺便改一圈」无关目录。
- 新 Agent / 新 CLI：**加** `harnesses/<名>` 或新 `tools/<名>`，少改 `bridge/dispatch` 的分支逻辑。
- 改 `pipeline`、`config`、共享 scene 前，评估对所有工具的影响并补测试。
- 合入 develop 前至少跑：`cd tools/<相关工具> && python -m pytest -q`（或该工具文档中的检查命令）。

## Agent / Cursor

仓库根 `.cursor/rules/repo-development-workflow.mdc` 对全仓生效；`tool-worktree-development.mdc` 补充 `tools/**` 细节。在 worktree 里打开项目时，规则与主仓一致（规则文件在 Git 里，不随 worktree 目录复制）。

## 与 release 的关系

- **日常开发**：只碰 `develop` 与你的 feature 分支。
- **发布**：仅在你验收 develop 后合并 `master`；紧急 hotfix 可用 `fix/*` worktree，仍建议先进 develop 短测再进 master（除非你指定直接修 master）。