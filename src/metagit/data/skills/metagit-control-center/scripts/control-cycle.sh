#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
QUERY="${2:-}"
PRESET="${3:-infra}"

"$(dirname "$0")/../../metagit-gating/scripts/gate-status.sh" "$ROOT"

if [[ -n "$QUERY" ]]; then
  "$(dirname "$0")/../../metagit-upstream-scan/scripts/upstream-scan.sh" "$ROOT" "$QUERY" "$PRESET" 20
else
  echo "status=ok\tmessage=no-query-provided"
fi
