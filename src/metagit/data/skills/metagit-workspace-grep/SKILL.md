---
name: metagit-workspace-grep
description: Search on-disk file contents across managed workspace repos via ripgrep (or Python fallback). Use when hunting code strings, configs, or Terraform/Docker patterns — not for manifest metadata.
metadata:
  internal: true
---
# Workspace content grep

Use this skill when you need **file contents** inside managed repos. Use `metagit search` / `metagit_repo_search` only for **catalog metadata** (names, URLs, tags).

Scaffold paths (`node_modules`, `.venv`, `__pycache__`, `.git`, etc.) are always excluded.

## Modalities (same semantics)

| Modality | Search | Ripgrep / backend status |
|----------|--------|---------------------------|
| CLI | `metagit workspace grep "QUERY" …` | `metagit workspace grep info [--json]` |
| MCP (ACTIVE gate) | `metagit_workspace_search` | `metagit_workspace_grep_info` |
| HTTP (`metagit api serve`) | `GET /v2/workspace/grep?q=…` | `GET /v2/workspace/grep/info` |
| Web UI | Workspace Console → Grep tab | (uses HTTP grep routes) |

## CLI examples

```bash
# whole workspace
metagit workspace grep "DATABASE_URL" --json

# one project
metagit workspace grep 'module "vpc"' --project platform --json

# one repo + context lines
metagit workspace grep "def main" --project portfolio --repo api -C 2 --json

# paths only
metagit workspace grep "TODO" --files-with-matches --limit 50

# backend status (install ripgrep for best performance)
metagit workspace grep info --json
```

Run `metagit workspace grep --help` for the full example list.

## MCP (`metagit_workspace_search`)

Required: `query`. Optional: `repos`, `preset`, `intent`, `paths`, `exclude`, `context_lines`, `include_paths`, `max_results`.

```json
{"query": "DATABASE_URL", "max_results": 25}
{"query": "module", "preset": "terraform", "repos": ["infra/vpc"]}
```

`metagit_workspace_grep_info` — no arguments; returns `ripgrep_available`, `ripgrep_path`, `ripgrep_version`, `search_backend`.

Related: `metagit_workspace_discover` lists files by `intent` or `pattern` (no line content).

## HTTP API

- `GET /v2/workspace/grep?q=…` — optional `project`, `repo` (repeatable), `preset`, `intent`, `max_results`, `context_lines`, `include_paths=true`
- `GET /v2/workspace/grep/info` — ripgrep status JSON

## When not to use

- Manifest / repo discovery → `metagit search` or `metagit_repo_search`
- GitNexus-ranked code flows → `metagit_workspace_semantic_search`
