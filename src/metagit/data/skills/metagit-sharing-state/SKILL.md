---
name: metagit-sharing-state
description: >-
  Configure shared coordination state (objectives, handoffs, approvals, events)
  across multiple agents and machines via METAGIT_STATE_URL, optional DynamoDB /
  MongoDB DocumentStore backends, and the ops HTTP path. Use when Hermes
  subagents, CI runners, or humans must see the same objective queue without
  Syncthing JSON files.
metadata:
  internal: true
---
# Metagit shared coordination state

Use when **more than one agent or machine** must read/write the same objectives,
handoffs, approvals, and event feed — without syncing `.metagit/sessions/*.json`
via Syncthing.

Full references:

- [docs/reference/sharing-state.md](../../../../docs/reference/sharing-state.md) — HTTP ops contract
- [docs/reference/central-state-plane.md](../../../../docs/reference/central-state-plane.md) — plane backends, extras, org/workspace ids, Dynamo bootstrap

## When to use

- Hermes controller + subagents on different hosts
- Human on Metagit Web + agents on MCP/CLI
- CI runner updating objectives while developers use Cursor MCP
- Org-scale coordination on DynamoDB / MongoDB (RFC-0015)

Prefer **shared state** (HTTP or cloud DocumentStore) over Syncthing for
coordination JSON when agents run on separate machines. Keep Syncthing (or git)
for `.metagit.yml` catalog edits only.

## Backends

| Backend | Extra | Typical use |
|---------|-------|-------------|
| `local` | — | Single machine default |
| `http` | — | Agents → `metagit web serve` via `METAGIT_STATE_URL` |
| `memory` | — | Tests only |
| `dynamodb` | `metagit-cli[state-dynamodb]` | Direct cloud or ops-server-hosted |
| `mongodb` | `metagit-cli[state-mongodb]` | Direct cloud or ops-server-hosted |

```bash
uv tool install 'metagit-cli[state-dynamodb]'
uv tool install 'metagit-cli[state-mongodb]'
```

## Coordinator setup (HTTP / deployment B)

On one host with the workspace manifest (local JSON **or** cloud DocumentStore
on the server):

```bash
metagit web serve --host 127.0.0.1 --port 8787
# production: TLS reverse proxy + bearer token in front
# optional: METAGIT_STATE_BACKEND=dynamodb + table/region on this host only
```

Agents keep `METAGIT_STATE_URL` — they do not need cloud extras when the
coordinator hosts Dynamo/Mongo.

## Client setup (CLI, MCP, every agent host)

App config (`~/.config/metagit/config.yml`):

```yaml
config:
  state:
    backend: http
    url: https://coordinator.example.com:8787
    token: your-bearer-token
    conflict_retries: 1
    org_id: ""            # optional plane partition
    workspace_id: ""
```

Or environment (overrides file — **must be set on the MCP server process**):

```bash
export METAGIT_AGENT_MODE=true
export METAGIT_STATE_URL=https://coordinator.example.com:8787
export METAGIT_STATE_TOKEN='…'
# optional plane identity:
# export METAGIT_STATE_ORG_ID=acme
# export METAGIT_STATE_WORKSPACE_ID=platform-ws
```

### Deployment A (agents → cloud directly)

```bash
uv tool install 'metagit-cli[state-dynamodb]'
export METAGIT_STATE_BACKEND=dynamodb
export METAGIT_STATE_ORG_ID=acme
export METAGIT_STATE_WORKSPACE_ID=platform-ws
export METAGIT_STATE_DDB_TABLE=metagit-state
export METAGIT_STATE_DDB_REGION=us-east-1
# AWS credentials via IAM/env — never commit
```

Restart MCP after changing env (`metagit mcp serve` inherits the shell env).

## Verify backend (MCP)

```text
resources/read → metagit://gate/status
```

Check `state_backend`:

| Field | Meaning |
|-------|---------|
| `backend` | `local` \| `http` \| `dynamodb` \| `mongodb` \| `memory` |
| `org_id` / `workspace_id` | Plane partitions |
| `url` | Remote ops base when `http` |
| `token_configured` | Bearer token present (not the secret) |
| `extras` | Whether dynamodb/mongodb extras are importable |
| `env_overrides` | Which `METAGIT_STATE_*` vars are set |

If `backend` is `local` but you expected remote/cloud, the MCP host is missing env/config.

## MCP tools (unchanged names — remote-aware)

| Coordination | MCP tool | Resource |
|--------------|----------|----------|
| Objectives | `metagit_objective_list`, `metagit_objective_upsert`, `metagit_objective_edit` | `metagit://objectives` |
| Approvals | `metagit_approval_request`, `metagit_approval_list`, `metagit_approval_resolve` | `metagit://approvals/pending` |
| Handoffs | `metagit_handoff_list`, `metagit_handoff_create`, `metagit_handoff_claim`, `metagit_handoff_complete` | `metagit://handoffs/open` |
| Events poll | `metagit_events` | `metagit://events/recent?since=` |

All use `resolve_backend()` — no separate remote MCP tools.

## CLI parity

```bash
metagit context objective list --json
metagit context handoff list --json
metagit context approval list --json
```

## Anti-patterns

- Mixed backends (some agents local, some remote/cloud) — objectives diverge silently
- Syncthing `.metagit/sessions/objectives.json` **and** remote/cloud state on the same fleet
- Forgetting to export `METAGIT_STATE_*` in the MCP launcher JSON (Cursor/Claude Desktop)
- Committing AWS keys, Mongo URIs, or bearer tokens into git or `.metagit.yml`

## Related skills

- `metagit-context-pack` — session bootstrap + objective/approval CLI/MCP table
- `metagit-mcp-resources` — resource read ladder including events poll
- `metagit-control-center` — ongoing multi-repo coordination
- `metagit-agent-coordination` — git isolation (branches/leases/worktrees); orthogonal to shared state JSON
