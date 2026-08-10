# MCP Project Context & Workspace Snapshot — Design Spec

**Status:** Draft for review  
**Priority:** Phase 2 (user-selected: pain A — losing place when switching projects)  
**Date:** 2026-05-15  
**Related:** [MCP refinement brainstorm session]; extends `.mex/context/mcp-runtime.md`

---

## Problem

Agents working across large multi-project workspaces must manually:

- Remember which workspace `project` is active
- Re-discover repo paths, branches, and dirty state after switching
- Reconstruct environment hints from `.metagit.yml` and scattered notes

Existing tools (`metagit_workspace_index`, `metagit_repo_inspect`, CLI `metagit workspace select`) do not persist or restore **working context** across switches.

## Goals

1. **Switch project context in one MCP call** with structured facts the agent can apply immediately.
2. **Persist lightweight session state** per workspace project under `.metagit/sessions/` (gitignored).
3. **Capture and restore workspace snapshots** for multi-repo git state (not file contents).
4. **Share core logic** between MCP tools and CLI where practical.
5. **Preserve guardrails:** read-only by default; no secret values in session files.

## Non-Goals (this spec)

- Cross-project dependency graphs (separate spec / Phase 2B).
- Semantic search, bulk sync, template apply.
- Host IDE integration (Cursor recent-files API) — metagit returns hints; host applies them.
- Storing uncommitted file diffs or full workspace copies.

---

## Architecture

### Responsibility split

| Concern | Owner |
|---------|--------|
| Active project, repo list, branches, dirty flags | Metagit (`ProjectContextService`) |
| Env **names** and non-secret defaults from config | Metagit |
| Env **secret values** | Host / existing secret tooling — never written to session files |
| Recent files, editor tabs, TODO apps | Host agent — optional `agent_hints` in session JSON written by agent |
| Git state snapshot / restore | Metagit (`WorkspaceSnapshotService`) |

### New components

```
src/metagit/core/mcp/services/
  project_context.py      # ProjectContextService
  session_store.py        # SessionStore (.metagit/sessions/)
  workspace_snapshot.py   # WorkspaceSnapshotService

src/metagit/core/workspace/
  context_models.py       # Pydantic models (shared MCP + CLI)

src/metagit/cli/commands/
  workspace_context.py    # optional: metagit workspace context switch|snapshot
```

Runtime dispatch in `MetagitMcpRuntime._dispatch_tool`; schemas in `_tool_schemas`; registry in `ToolRegistry._active_tools`.

### Session storage layout

```
<workspace_root>/.metagit/
  sessions/
    _workspace.json          # active_project_name, last_switch_at
    <project_name>.json        # per-project session (see schema below)
  snapshots/
    <snapshot_id>.json         # immutable snapshot manifests
```

**Gitignore:** Document adding `.metagit/sessions/` and `.metagit/snapshots/` to workspace `.gitignore` template (or metagit init). Do not auto-modify user `.gitignore` without explicit opt-in.

---

## Data models

### `WorkspaceSessionMeta` (`_workspace.json`)

```yaml
active_project: str | null
last_switch_at: ISO8601
last_snapshot_id: str | null
```

### `ProjectSession` (`<project>.json`)

```yaml
project_name: str
updated_at: ISO8601
recent_repos: list[str]           # resolved repo paths, most recent first, max 10
primary_repo_path: str | null     # suggested cwd
agent_notes: str | null             # free text from agent, bounded 4KB
env_overrides: dict[str, str]       # non-secret only; keys validated ^[A-Z][A-Z0-9_]*$
last_snapshot_id: str | null
```

**Never persist:** secret values, tokens, password fields, full `.env` contents.

### `ProjectContextBundle` (tool response)

```yaml
ok: bool
error: str | null
project_name: str
workspace_root: str
project_description: str | null
agent_prompt: str | null            # from WorkspaceProject.agent_prompt
repos:
  - repo_name: str
    repo_path: str
    configured_path: str | null
    exists: bool
    branch: str | null
    dirty: bool | null
    tags: dict[str, str]
env:
  export: dict[str, str]            # safe exports only (see Env resolution)
  hints: list[str]                  # e.g. "Set MYAPP_ENV from your secret store"
session:
  restored: bool
  recent_repos: list[str]
  primary_repo_path: str | null
  agent_notes: str | null
suggested_cwd: str | null
```

### `WorkspaceSnapshot`

```yaml
snapshot_id: str                    # uuid4
created_at: ISO8601
active_project: str | null
label: str | null                   # optional user/agent label
repos:
  - project_name: str
    repo_name: str
    repo_path: str
    branch: str | null
    dirty: bool
    ahead: int | null
    behind: int | null
    uncommitted_count: int | null
env_key_names: list[str]            # names only, no values
session_ref: str | null             # project session file path relative to workspace root
```

---

## MCP tools

### 1. `metagit_project_context_switch`

**Gate:** Active workspace only (same as `metagit_repo_search`).

**Input schema:**

```json
{
  "type": "object",
  "required": ["project_name"],
  "properties": {
    "project_name": { "type": "string" },
    "setup_env": { "type": "boolean", "default": true },
    "restore_session": { "type": "boolean", "default": true },
    "save_previous": { "type": "boolean", "default": true },
    "primary_repo": { "type": "string", "description": "repo_name or path to prefer as suggested_cwd" }
  },
  "additionalProperties": false
}
```

**Behavior:**

1. Validate `project_name` exists in `config.workspace.projects`.
2. If `save_previous` and prior `active_project` set: touch prior project's session (`updated_at`, keep `recent_repos`).
3. Build repo rows from `WorkspaceIndexService` filtered to project.
4. For each existing git repo: `RepoOperationsService.inspect` (batch, max 20 repos per call — return `inspect_truncated: true` if more).
5. If `restore_session`: load `<project>.json`; merge `recent_repos`, `agent_notes`, `primary_repo_path`.
6. If `setup_env`: resolve env exports (see below).
7. Update `_workspace.json` `active_project`.
8. Return `ProjectContextBundle`.

**Env resolution (`setup_env: true`):**

- Always set: `METAGIT_WORKSPACE_ROOT`, `METAGIT_PROJECT`, `METAGIT_PROJECT_REPOS` (comma-separated paths).
- From root `.metagit.yml` `variables` where `kind` is safe for export (document allowlist: literal/string refs only; skip `secret`, `remote_*`).
- From `WorkspaceProject.agent_prompt` — not env; returned as `agent_prompt` field.
- Session `env_overrides` merged last (non-secret keys only).

### 2. `metagit_workspace_state_snapshot`

**Input schema:**

```json
{
  "type": "object",
  "properties": {
    "label": { "type": "string" },
    "project_name": { "type": "string", "description": "default: active project" },
    "include_all_projects": { "type": "boolean", "default": false },
    "include_env_state": { "type": "boolean", "default": true },
    "link_session": { "type": "boolean", "default": true }
  },
  "additionalProperties": false
}
```

**Behavior:**

1. Determine repo scope: active project repos, or all workspace repos if `include_all_projects`.
2. Collect git metadata per repo (`inspect` + `ahead`/`behind` via `git rev-list --left-right --count @{u}...HEAD` when upstream exists).
3. Write `snapshots/<snapshot_id>.json`.
4. If `link_session`: set `last_snapshot_id` on workspace + project session files.
5. Return snapshot JSON (not full file paths outside workspace).

### 3. `metagit_workspace_state_restore`

**Input schema:**

```json
{
  "type": "object",
  "required": ["snapshot_id"],
  "properties": {
    "snapshot_id": { "type": "string" },
    "switch_project": { "type": "boolean", "default": true },
    "restore_session": { "type": "boolean", "default": true }
  },
  "additionalProperties": false
}
```

**Behavior:**

1. Load snapshot by id; 404-style error if missing.
2. If `switch_project` and `active_project` set: call internal `ProjectContextService.switch` (no duplicate MCP round-trip).
3. If `restore_session`: copy `session_ref` fields into live session files (metadata only — **does not** run git checkout, reset, or stash).
4. Return `{ ok, snapshot_id, context: ProjectContextBundle | null, notes: [...] }` with explicit list of what was **not** restored (branches, uncommitted changes).

**Important:** Restore is **context restoration for agents**, not git workspace rewind.

### 4. `metagit_session_update` (supporting tool)

Allows agent to persist notes and recents without full switch.

```json
{
  "project_name": "acme-platform",
  "recent_repos": ["..."],
  "agent_notes": "...",
  "primary_repo_path": "...",
  "env_overrides": { "METAGIT_FEATURE_BRANCH": "feat/foo" }
}
```

Validates project exists; merges into session file.

---

## CLI parity (optional in v1, recommended v1.1)

```bash
metagit workspace context switch --project acme-platform [--json]
metagit workspace context show [--project acme-platform] [--json]
metagit workspace snapshot create [--label "before vacation"] [--json]
metagit workspace snapshot restore <snapshot_id> [--json]
```

Implementation calls same services as MCP.

---

## Agent usage contract

After `metagit_project_context_switch`, the agent should:

1. Set mental scope to `project_name` and `agent_prompt` if present.
2. Prefer `suggested_cwd` / `primary_repo_path` for file operations.
3. Prioritize `recent_repos` when searching or syncing.
4. Apply `env.export` to subprocess invocations where relevant (never log values marked sensitive).

Before switching away, agent may call `metagit_session_update` with `agent_notes` summary and `recent_repos` ordering.

---

## Error handling

| Condition | Response |
|-----------|----------|
| Unknown project | `ok: false`, `error: "project_not_found"` |
| Inactive gate | Tool not in `tools/list` |
| Session file corrupt | Log warning; treat as empty session |
| Repo inspect failure | Include repo with `branch: null`, `dirty: null`, `inspect_error` |
| Snapshot id missing | `ok: false`, `error: "snapshot_not_found"` |

All tools return JSON-serializable dicts; MCP wraps in `content: [{ type: "text", text: json }]}` per existing runtime pattern.

---

## Security

- Reject `env_overrides` keys not matching `^[A-Z][A-Z0-9_]{0,63}$`.
- Reject override values matching secret heuristics (e.g. `AKIA`, `Bearer `, `-----BEGIN`).
- Cap `agent_notes` at 4096 chars.
- Session and snapshot directories created with mode `0700` where OS permits.

---

## Testing

| Area | Tests |
|------|--------|
| `SessionStore` | read/write, corrupt file, merge updates |
| `ProjectContextService` | switch valid/invalid project, restore_session, env export allowlist |
| `WorkspaceSnapshotService` | create/restore, missing id, include_all_projects |
| MCP runtime | tools/list visibility, schema validation, -32602 on bad args |
| Integration | temp workspace with `.metagit.yml` + 2 projects + git repos |

Fixtures: `tests/fixtures/workspace_multi_project/`.

---

## Rollout

1. **v0.1:** MCP tools only + session store + docs.
2. **v0.2:** CLI commands + `metagit-workspace-scope` / `metagit-control-center` skill updates.
3. **v0.3:** Optional MCP resource `metagit://workspace/context` for polling active project without tool call.

**Schema versioning:** Additive optional fields only in patch releases; new tools are `feat:` per ROUTER commit semantics.

---

## Open questions (defaults chosen)

| Question | Decision |
|----------|----------|
| Max repos inspected per switch? | 20; paginate or summarize remainder |
| Auto-snapshot on switch? | No; explicit `metagit_workspace_state_snapshot` only |
| Store active project in `.metagit.yml`? | No; session files only to avoid config churn |

---

## Success criteria

- Agent can switch from project A → B → A and recover `recent_repos`, `agent_notes`, and repo dirty/branch summary without manual exploration.
- Session files contain zero secret values (unit test scans fixtures).
- `task test` MCP + workspace tests green; skills reference new tools.

---

## References

- `src/metagit/core/mcp/services/workspace_index.py` — repo rows
- `src/metagit/core/mcp/services/repo_ops.py` — inspect
- `src/metagit/cli/commands/workspace.py` — `workspace select` (interactive repo picker; context switch is complementary)
- `.mex/patterns/add-mcp-tool.md` — implementation checklist
