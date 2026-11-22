# 工具开发在哪里做？

新工具与未评审改动 **不在 `master` 主工作区里直接开发**，请使用 **git worktree** + **`developer` 集成分支**。

## 快速查看

```bash
cd /Users/gemini/Code/MyWikiTools && git worktree list
```

## 当前登记示例

| Worktree | 分支 | 内容 |
|----------|------|------|
| `../MyWikiTools-worktrees/ictrl-app-sync` | `tool/ictrl-app-sync` | `ias` / `ictrl-app-sync` 工具 |

流程：**worktree 开发 → 评审 → 合并 `developer` → 稳定后合并 `master`**。  
细则与脚手架命令见 worktree 内 `docs/TOOL_DEVELOPMENT.zh.md` 与 `.cursor/rules/tool-worktree-development.mdc`（随 `tool/*` 一并合入 `developer`）。