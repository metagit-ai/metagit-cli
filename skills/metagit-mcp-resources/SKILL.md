---
name: metagit-mcp-resources
description: >-
  Token-efficient MCP resource ladder for metagit workspaces — catalog, map,
  layered prompts, project/repo drill-down. Use when the IDE host exposes metagit
  resources/read instead of shell CLI.
metadata:
  internal: true
---
# Metagit MCP layered resources

Use this skill when an agent connects via **MCP** (`metagit mcp serve`) and should
minimize context bloat. Prefer **`resources/read`** and **`prompts/get`** over dumping
the full manifest or calling `metagit_context_pack` tier 2 repeatedly.

## Session start (MCP)

1. `resources/read` → `metagit://catalog`
2. `metagit://gate/status` — confirm `state_backend.backend` (`local` vs `http`) when using shared coordination state
3. `metagit://workspace/map`
4. `metagit://prompt/workspace/session-start?instructions=0` **or** `prompts/get` name `workspace/session-start`
5. `metagit://session/meta`
6. **Once per session window:** tool `metagit_session_begin` when a full bootstrap envelope is required (mutates boundary)

Idle return: `metagit://session/digest/summary` (read-only; does not bump boundary).

## Resource ladder

| Layer | URI | When |
|-------|-----|------|
| L0 | `metagit://catalog` | First read every connect |
| L0 | `metagit://workspace/map` | Boundaries, clone existence |
| L0 | `metagit://session/meta` | Active project context |
| L1 | `metagit://prompt/{scope}/{kind}?instructions=0` | Task procedure |
| L1 | `metagit://project/{project}/summary` | After project scope is known |
| L1 | `metagit://repo/{project}/{repo}/card` | Single-repo health |
| L1 | `metagit://objectives` | Shared objective state |
| L1 | `metagit://approvals/pending` | Before mutating ops |
| L1 | `metagit://handoffs/open` | Multi-agent coordination |
| L2 | `metagit://session/digest/summary` | Return-after-idle |
| L2 | `metagit://workspace/health` | Preflight before sync |
| L2 | `metagit://workspace/repos/status?summary=1` | Aggregate index health |
| L2 | `metagit://events/recent?since=` | Poll objective/approval/handoff changes |
| L3 | `metagit://workspace/config?view=full` | Manifest editing only |

## MCP prompts capability

| Method | Use |
|--------|-----|
| `prompts/list` | Discover `scope/kind` names |
| `prompts/get` | Same bodies as prompt resources; check `_meta.resource_uri` |

## Tools vs resources

| Need | Resource | Tool |
|------|----------|------|
| Backend mode | `gate/status` (`state_backend`) | — |
| Map | `workspace/map` | `metagit_context_pack` tier 0 |
| Repo card | `repo/{p}/{r}/card` | `metagit_repo_card` |
| Objectives | `objectives` | `metagit_objective_*` |
| Approvals | `approvals/pending` | `metagit_approval_*` |
| Handoffs | `handoffs/open` | `metagit_handoff_*` |
| Events poll | `events/recent?since=` | `metagit_events` |
| Digest (read-only) | `session/digest` | `metagit_session_digest` |
| Full bootstrap + boundary | — | `metagit_session_begin` |
| Search / sync / mutations | — | respective tools |

**Dispatch plans:** `metagit_agent_dispatch_plan` returns `handoff.mcp_resources[]` with scoped read order.

## Anti-patterns

- Auto-subscribing to `metagit://workspace/config` without `?view=summary`
- Calling `metagit_context_pack` tier 2 on every turn
- Loading all repo cards when only one repo is in scope

## Spec

Full URI taxonomy: `docs/reference/mcp-layered-resources-spec.md`

## Related skills

- `metagit-sharing-state` — `METAGIT_STATE_URL`, MCP host env, multi-agent setup
- `metagit-context-pack` — CLI + tool tier workflow
- `metagit-workspace-scope` — gate and boundaries
- `metagit-control-center` — ongoing multi-repo coordination
