---
name: metagit-sharing-state
description: >-
  Configure shared coordination state (objectives, handoffs, approvals, events)
  across multiple agents and machines via METAGIT_STATE_URL and the ops HTTP
  backend. Use when Hermes subagents, CI runners, or humans must see the same
  objective queue without Syncthing JSON files.
metadata:
  internal: true
---
# Metagit shared coordination state

Use when **more than one agent or machine** must read/write the same objectives,
handoffs, approvals, and event feed — without syncing `.metagit/sessions/*.json`
via Syncthing.

Full reference: [docs/reference/sharing-state.md](../../../../docs/reference/sharing-state.md)

## When to use

- Hermes controller + subagents on different hosts
- Human on Metagit Web + agents on MCP/CLI
- CI runner updating objectives while developers use Cursor MCP

Prefer **remote state** over Syncthing for coordination JSON when agents run on
separate machines. Keep Syncthing (or git) for `.metagit.yml` catalog edits only.

## Coordinator setup

On one host with the workspace manifest:

```bash
metagit web serve --host 127.0.0.1 --port 8787
# production: TLS reverse proxy + bearer token in front
```

Persistence stays on that host under `.metagit/sessions/` and `.metagit/approvals/`.

## Client setup (CLI, MCP, every agent host)

App config (`~/.config/metagit/config.yml`):

```yaml
config:
  state:
    backend: http
    url: https://coordinator.example.com:8787
    token: your-bearer-token
    conflict_retries: 1
```

Or environment (overrides file — **must be set on the MCP server process**):

```bash
export METAGIT_AGENT_MODE=true
export METAGIT_STATE_URL=https://coordinator.example.com:8787
export METAGIT_STATE_TOKEN='…'
```

Restart MCP after changing env (`metagit mcp serve` inherits the shell env).

## Verify backend (MCP)

```text
resources/read → metagit://gate/status
```

Check `state_backend`:

| Field | Meaning |
|-------|---------|
| `backend` | `local` or `http` (effective) |
| `url` | Remote ops base when `http` |
| `token_configured` | Bearer token present (not the secret) |
| `env_overrides` | Which `METAGIT_STATE_*` vars are set |

If `backend` is `local` but you expected remote, the MCP host is missing env/config.

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

- Mixed backends (some agents local, some remote) — objectives diverge silently
- Syncthing `.metagit/sessions/objectives.json` **and** remote state on the same fleet
- Forgetting to export `METAGIT_STATE_*` in the MCP launcher JSON (Cursor/Claude Desktop)

## Related skills

- `metagit-context-pack` — session bootstrap + objective/approval CLI/MCP table
- `metagit-mcp-resources` — resource read ladder including events poll
- `metagit-control-center` — ongoing multi-repo coordination
