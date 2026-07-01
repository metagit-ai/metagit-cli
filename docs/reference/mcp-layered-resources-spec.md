# Metagit MCP layered resources — specification

**Status:** Implemented (Phases 1–4)  
**Version:** 1.1  
**Last updated:** 2026-06-30  

## Problem

Metagit exposes rich agent context via MCP **tools** (`metagit_context_pack`, `metagit_session_begin`, objectives, approvals, search, sync). MCP **resources** were flat and often heavy (full manifest dumps, no prompt read path).

Agents and MCP hosts that auto-subscribe to resources therefore loaded maximum context before work begins. Tools that **mutate** session state (`metagit_context_pack` tier 2, `metagit_session_begin`) must not be mirrored as passive resources.

## Goals

1. **Lazy escalation** — default reads are tier-0 sized (~100–400 tokens).
2. **Layered prompts** — operational checklists as `text/plain` resources and MCP `prompts/get`.
3. **Read-only resources** — no resource read updates `.metagit/sessions/` or approval/objective stores.
4. **Discovery anchor** — `metagit://catalog` documents URI patterns, read order, and token estimates.
5. **Parity** — reuse core services; agent dispatch plans include `handoff.mcp_resources`.

## URI taxonomy

### Always available

| URI | MIME | Gate | Description |
|-----|------|------|-------------|
| `metagit://catalog` | JSON | any | Resource index, read order, dynamic patterns |
| `metagit://gate/status` | JSON | any | MCP activation state + `state_backend` diagnostics (`local`/`http`, URL, env overrides) |
| `metagit://workspace/ops-log` | JSON | any | Operations audit trail (`?limit=N`) |

### Active gate only

| URI | MIME | Tier | Description |
|-----|------|------|-------------|
| `metagit://workspace/map` | JSON | T0 | `WorkspaceMapResult` |
| `metagit://session/meta` | JSON | T0 | Active project + session notes |
| `metagit://session/digest` | JSON | T2 | Read-only digest (no boundary bump) |
| `metagit://session/digest/summary` | JSON | T2 | Compact digest counts |
| `metagit://prompt/catalog` | JSON | T0 | Prompt kinds × scopes (no bodies) |
| `metagit://objectives` | JSON | L1 | Slim objective list (`?status=`, `?full=1`) |
| `metagit://approvals/pending` | JSON | L1 | Pending approval queue |
| `metagit://handoffs/open` | JSON | L1 | Open/claimed handoffs |
| `metagit://events/recent` | JSON | L2 | Poll feed (`?since=` ISO cursor) |
| `metagit://workspace/config` | JSON | L3 | Default `?view=summary`; `?view=full` for manifest |
| `metagit://workspace/repos/status` | JSON | L2 | Index rows; `?project=`, `?summary=1` |
| `metagit://workspace/health` | JSON | L2 | Health check payload |
| `metagit://workspace/context` | JSON | T0 | **Deprecated alias** of `session/meta` |

### Dynamic (read via `resources/read`; documented in catalog)

| Pattern | MIME | Tier |
|---------|------|------|
| `metagit://prompt/{scope}/{kind}` | plain | L1 |
| `metagit://project/{project}/summary` | JSON | L1 |
| `metagit://repo/{project}/{repo}/card` | JSON | L1 |

## MCP prompts capability

- `prompts/list` — catalog entries as `scope/kind` names with argument schema.
- `prompts/get` — same bodies as `metagit://prompt/{scope}/{kind}` resources; `_meta.resource_uri` cross-links.

## Tool vs resource matrix

| Need | Resource | Tool |
|------|----------|------|
| Workspace map | `workspace/map` | `metagit_context_pack` tier 0 |
| Repo card | `repo/{p}/{r}/card` | `metagit_repo_card` |
| Session bootstrap + boundary | — | `metagit_session_begin` |
| Tier-2 pack + boundary bump | — | `metagit_context_pack` tier 2 |
| Operational checklist | `prompt/{scope}/{kind}` or `prompts/get` | CLI `metagit prompt` |
| Objective CRUD | `objectives` (list) | `metagit_objective_upsert` |
| Search / sync / mutations | — | respective tools |

## Recommended read order (session start)

1. `metagit://catalog`
2. `metagit://workspace/map`
3. `metagit://prompt/workspace/session-start?instructions=0`
4. `metagit://session/meta`
5. Tool: `metagit_session_begin` when a full bootstrap envelope is required (mutates boundary)

## Agent dispatch integration (Phase 4)

`metagit agent dispatch-plan` and MCP `metagit_agent_dispatch_plan` return `handoff.mcp_resources[]` — ordered URIs scoped to project/repo and prompt kind.

Agent templates and Hermes init manifests reference the resource ladder instead of full config dumps.

## Implementation phases

| Phase | Status | Deliverables |
|-------|--------|--------------|
| **1** | Done | catalog, map, session/meta, prompt/catalog, prompt/{scope}/{kind}, project/summary, repo/card, config summary default |
| **2** | Done | objectives, approvals/pending, handoffs/open, session/digest (+ summary), repos/status?summary=1 |
| **3** | Done | MCP prompts/list + prompts/get; events/recent poll feed; resources.listChanged capability |
| **4** | Done | Agent template checklist, dispatch `mcp_resources`, Hermes manifest updates |

## References

- `src/metagit/core/mcp/resource_catalog.py`
- `src/metagit/core/mcp/resource_service.py`
- `src/metagit/core/mcp/prompt_mcp.py`
- Skill: `metagit-mcp-resources`
