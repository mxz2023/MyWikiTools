#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
pipx install "$ROOT"
echo ""
echo "Next:"
echo "  fnotify install"
echo "  fnotify doctor --json-output"