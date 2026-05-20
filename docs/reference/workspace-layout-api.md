# Workspace layout API (v2)

Rename and move operations for workspace projects and repositories. Intended for agents, CLI, MCP, and a future web UI.

## Sync root

Layout operations apply disk changes under `workspace.path` from app config (`metagit.config.yaml`). The HTTP server’s `--root` is the directory containing `.metagit.yml`.

## Endpoints

| Method | Path | Body |
|--------|------|------|
| POST | `/v2/projects/{from}/rename` | `{ "to_name": "apps" }` |
| POST | `/v2/repos/{project}/{repo}/rename` | `{ "to_name": "new-name" }` |
| POST | `/v2/repos/{project}/{repo}/move` | `{ "to_project": "platform" }` |

Query flags (or JSON body): `dry_run`, `manifest_only`, `force`, `no_update_sessions` (project rename only).

## Response shape

Same as catalog mutations:

```json
{
  "ok": true,
  "entity": "repo",
  "operation": "move",
  "project_name": "platform",
  "repo_name": "svc-a",
  "from_project": "portfolio",
  "to_project": "platform",
  "config_path": "/path/.metagit.yml",
  "data": {
    "dry_run": false,
    "manifest_changes": ["..."],
    "disk_steps": [{"action": "move", "source": "...", "target": "..."}],
    "warnings": [],
    "manifest_updated": true
  }
}
```

## CLI equivalents

```bash
metagit workspace project rename alpha apps --dry-run --json
metagit workspace repo rename -p alpha svc-a svc-b --json
metagit workspace repo move -p alpha -n svc-a --to-project beta --json
```

## MCP tools

- `metagit_workspace_project_rename`
- `metagit_workspace_repo_rename`
- `metagit_workspace_repo_move`

Always pass `dry_run: true` first when an agent is unsure about disk impact.
