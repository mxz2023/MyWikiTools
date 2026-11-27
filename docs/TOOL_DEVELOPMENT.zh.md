# 工具开发在哪里做？

新工具在 **本仓库内** 的 **`.worktrees/<工具名>`** 开发，不要堆在 `develop` / `master` 主工作区根目录。

## 位置与分支

| 项 | 约定 |
|----|------|
| Worktree 路径 | `MyWikiTools/.worktrees/<工具名>`（仅此一处，不在 `Code/` 外并列建目录） |
| 集成分支 | **`develop`**（PR 目标） |
| 发布 | `develop` → `master` |

```bash
git worktree list
# …/MyWikiTools/.worktrees/ictrl-app-sync  [tool/ictrl-app-sync]
```

## PR 合并后

合并到 **`develop`** 后 **删除** 对应 worktree：

```bash
./scripts/worktree-finish.sh <工具名>
```

Cursor 规则在 **仓库根** `.cursor/rules/tool-worktree-development.mdc`（维护在 `develop`）；任意 `.worktrees/<工具>` worktree 打开后同样生效。工具 feature 分支勿长期独占规则改动，应合入 `develop` 后对全员 worktree 可见。