#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-git+https://github.com/mxz2023/MyWikiTools.git@master#subdirectory=tools/apple-health-cli}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() { printf '%s\n' "$*"; }

ensure_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    return 0
  fi
  log "pipx not found. Installing pipx…"
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
  export PATH="${HOME}/.local/bin:${PATH}"
  command -v pipx >/dev/null 2>&1
}

install_cli() {
  if [[ -f "${TOOL_ROOT}/pyproject.toml" ]]; then
    pipx install --force "${TOOL_ROOT}"
  else
    pipx install --force "${REPO_URL}"
  fi
}

main() {
  ensure_pipx
  install_cli
  export PATH="${HOME}/.local/bin:${PATH}"
  command -v ahp >/dev/null 2>&1 && ahp setup || log "Run: ahp setup"
}

main "$@"
