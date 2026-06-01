---
name: workspace-content-grep
description: Search file contents across managed workspace repos via ripgrep.
triggers:
  - "workspace grep"
  - "search repo contents"
  - "ripgrep workspace"
---

# Workspace content grep

Use **`metagit workspace grep`** (or MCP `metagit_workspace_search`, HTTP `GET /v2/workspace/grep`) to search **on-disk repo files**.

Do **not** use `metagit search` for file contents — that command searches manifest metadata only.

## Scope

- Whole workspace: omit `--project` / `--repo`
- One project: `--project NAME`
- One repo: `--project NAME --repo REPO`

## Tool policy

1. Prefer `rg` when available (gitignore-aware by default).
2. Hard excludes always applied: `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, etc.
3. Python walk fallback only when `rg` is missing.

## Examples

```bash
metagit workspace grep "DATABASE_URL" --json
metagit workspace grep "module \"vpc\"" --project platform --json
metagit workspace grep "def main" --project portfolio --repo api -C 2 --json
```
