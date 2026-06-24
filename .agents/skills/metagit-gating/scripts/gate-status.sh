#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"

uv run python - "$ROOT" <<'PY'
import os
import sys
from metagit.core.mcp.gate import WorkspaceGate
from metagit.core.mcp.root_resolver import WorkspaceRootResolver
from metagit.core.mcp.tool_registry import ToolRegistry

root = sys.argv[1]
resolver = WorkspaceRootResolver()
gate = WorkspaceGate()
registry = ToolRegistry()

resolved = resolver.resolve(cwd=os.path.abspath(root), cli_root=root)
status = gate.evaluate(root_path=resolved)
tools = registry.list_tools(status)
print(f"state={status.state.value}\troot={status.root_path or 'none'}\ttools={len(tools)}")
PY
