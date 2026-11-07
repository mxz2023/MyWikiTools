#!/usr/bin/env bash
# Run pytest in every tools/* package that has tests/.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
status=0
for tool in "${ROOT}"/tools/*/; do
  [[ -d "${tool}/tests" ]] || continue
  [[ -f "${tool}/pyproject.toml" ]] || continue
  name="$(basename "${tool}")"
  echo "==> ${name}"
  if (cd "${tool}" && python -m pytest -q); then
    :
  else
    status=1
  fi
done
exit "${status}"
