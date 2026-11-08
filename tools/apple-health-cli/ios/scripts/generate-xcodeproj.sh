#!/usr/bin/env bash
# Generate AHPSync.xcodeproj via XcodeGen (brew install xcodegen).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v xcodegen >/dev/null 2>&1; then
  echo "XcodeGen not found. Install: brew install xcodegen" >&2
  echo "Or open Xcode → File → New → iOS App, copy sources from ios/AHPSync/AHPSync/" >&2
  exit 1
fi
(cd "${ROOT}" && xcodegen generate)
echo "Generated: ${ROOT}/AHPSync.xcodeproj (or use committed ios/AHPSync.xcodeproj)"
open "${ROOT}/AHPSync.xcodeproj" 2>/dev/null || true
