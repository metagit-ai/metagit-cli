#!/usr/bin/env zsh
# Token-efficient wrapper for agent-access optimization.
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
REPO_ROOT="${1:-.}"
shift || true

exec uv run python "${SCRIPT_DIR}/optimize_agent_access.py" "${REPO_ROOT}" "$@"
