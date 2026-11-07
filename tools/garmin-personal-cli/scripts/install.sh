#!/usr/bin/env bash
# Install garmin-personal-cli via pipx, then guide user to create & configure Garmin Personal API key.
set -euo pipefail

REPO_URL="${REPO_URL:-git+https://github.com/mxz2023/MyWikiTools.git@master#subdirectory=tools/garmin-personal-cli}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() { printf '%s\n' "$*"; }

ensure_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    return 0
  fi
  log "pipx not found. Installing pipx for current user..."
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
  log ""
  log "Added pipx to PATH (see above). Open a new terminal or run: source ~/.zshrc"
  log ""
  if ! command -v pipx >/dev/null 2>&1; then
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  command -v pipx >/dev/null 2>&1 || {
    log "ERROR: pipx still not on PATH. Fix PATH then re-run this script." >&2
    exit 1
  }
}

install_cli() {
  if [[ -f "${TOOL_ROOT}/pyproject.toml" ]]; then
    log "Installing from local tool dir: ${TOOL_ROOT}"
    pipx install --force "${TOOL_ROOT}"
  else
    log "Installing from: ${REPO_URL}"
    pipx install --force "${REPO_URL}"
  fi
}

run_setup() {
  # Prefer pipx shims over pyenv editable installs.
  export PATH="${HOME}/.local/bin:${PATH}"
  if command -v gmp >/dev/null 2>&1; then
    gmp setup
  else
    log "WARNING: gmp not found on PATH after install. Open a new terminal and run: gmp setup" >&2
  fi
}

main() {
  ensure_pipx
  install_cli
  run_setup
}

main "$@"
