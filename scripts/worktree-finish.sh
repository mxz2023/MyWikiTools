#!/usr/bin/env bash
# Remove a finished .worktrees/<slug> and delete the local feature branch if merged.
set -euo pipefail

SLUG="${1:?usage: worktree-finish.sh <slug>}"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
WT="${ROOT}/.worktrees/${SLUG}"

if [[ -d "${WT}" ]]; then
  if git worktree remove "${WT}" 2>/dev/null; then
    :
  else
    git worktree remove --force "${WT}"
  fi
  echo "Removed worktree: .worktrees/${SLUG}"
else
  echo "No directory .worktrees/${SLUG} (skip remove)" >&2
fi

for br in "tool/${SLUG}" "feature/${SLUG}" "fix/${SLUG}"; do
  if git show-ref --verify --quiet "refs/heads/${br}"; then
    if git branch -d "${br}" 2>/dev/null; then
      echo "Deleted merged branch: ${br}"
    else
      echo "Branch ${br} not fully merged; delete manually if intended" >&2
    fi
  fi
done

git fetch -p