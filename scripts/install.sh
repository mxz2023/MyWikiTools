#!/usr/bin/env bash
# Install garmin-personal-cli from monorepo (backward-compatible path).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${ROOT}/tools/garmin-personal-cli/scripts/install.sh" "$@"
