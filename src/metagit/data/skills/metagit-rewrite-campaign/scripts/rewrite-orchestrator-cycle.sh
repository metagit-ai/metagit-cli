#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
SLUG="${2:-language-rewrite}"
MANIFEST="${ROOT}/.metagit.yml"

if [[ ! -f "$MANIFEST" ]]; then
  echo "status=error\tmessage=missing-manifest\tpath=${MANIFEST}"
  exit 1
fi

export METAGIT_AGENT_MODE=true

SINCE="$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"

echo "phase=bootstrap"
metagit context pack --tier 2 --json -c "$MANIFEST" 2>/dev/null || echo "context_pack=skipped"

echo "phase=campaign_status"
if metagit campaign status --slug "$SLUG" --json -c "$MANIFEST" 2>/dev/null; then
  :
else
  echo "campaign_status=missing\tslug=${SLUG}"
fi

PARITY="${ROOT}/_rewrite/parity-registry.yml"
if [[ -f "$PARITY" ]]; then
  echo "parity_registry=present\tpath=${PARITY}"
else
  echo "parity_registry=missing\thint=copy examples/metagit-rewrite/_rewrite/parity-registry.example.yml"
fi

echo "phase=events"
metagit context events --campaign "$SLUG" --since "$SINCE" --json -c "$MANIFEST" 2>/dev/null \
  || echo "events=empty"

echo "phase=handoffs"
metagit context handoff list --json -c "$MANIFEST" 2>/dev/null || echo "handoffs=empty"

echo "status=ok\tslug=${SLUG}"
