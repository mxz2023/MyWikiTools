#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_URL="${REPO_URL:-git+https://github.com/mxz2023/MyWikiTools.git@master#subdirectory=tools/mi-fitness-cli}"

log() { printf '%s\n' "$*"; }

ensure_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    return 0
  fi
  log "Installing pipx..."
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
  export PATH="${HOME}/.local/bin:${PATH}"
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
  if command -v mfp >/dev/null 2>&1; then
    mfp setup
  else
    log "Open a new terminal, then run: mfp setup"
  fi
}

main "$@"
