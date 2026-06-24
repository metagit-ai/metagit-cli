#!/usr/bin/env bash
# Token-efficient wrapper for agent-access optimization.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-.}"
shift || true

exec uv run python "${SCRIPT_DIR}/optimize_agent_access.py" "${REPO_ROOT}" "$@"
