#!/usr/bin/env zsh

set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  exec uv run python "./scripts/prepush-gate.py" "$@"
fi

exec python3 "./scripts/prepush-gate.py" "$@"
