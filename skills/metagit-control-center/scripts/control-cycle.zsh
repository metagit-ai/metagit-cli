#!/usr/bin/env zsh
set -euo pipefail

ROOT="${1:-$PWD}"
QUERY="${2:-}"
PRESET="${3:-infra}"

"$(dirname "$0")/../../metagit-mcp-gating/scripts/gate-status.zsh" "$ROOT"

if [[ -n "$QUERY" ]]; then
  "$(dirname "$0")/../../metagit-upstream-discovery/scripts/upstream-scan.zsh" "$ROOT" "$QUERY" "$PRESET" 20
else
  echo "status=ok\tmessage=no-query-provided"
fi