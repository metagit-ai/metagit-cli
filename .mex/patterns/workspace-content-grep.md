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

Ripgrep status: CLI `metagit workspace grep info`, MCP `metagit_workspace_grep_info`, HTTP `GET /v2/workspace/grep/info`.

Install bundled skill **`metagit-workspace-grep`** for full modality tables and examples.

Do **not** use `metagit search` for file contents — that command searches manifest metadata only.

## Scope

- Whole workspace: omit `--project` / `--repo`
- One project: `--project NAME`
- One repo: `--project NAME --repo REPO`

## Tool policy

1. Prefer `rg` when available (gitignore-aware by default).
2. Hard excludes always applied (ripgrep globs **and** post-filter on path segments): `.git`, `.metagit`, `node_modules`, `.venv`, `venv`, `__pycache__`, `.tox`, `.pytest_cache`, `dist`, `build`, `.next`, `vendor`, `target`, etc. — see `_SCAFFOLD_PATH_SEGMENTS` in `workspace_search.py`.
3. Python walk fallback only when `rg` is missing; walk prunes scaffold directories.

## Examples

```bash
# whole workspace
metagit workspace grep "DATABASE_URL" --json
# one project
metagit workspace grep 'module "vpc"' --project platform --json
# one repo with context
metagit workspace grep "def main" --project portfolio --repo api -C 2 --json
# ripgrep backend
metagit workspace grep info --json
```

Run `metagit workspace grep --help` for the full example list.
