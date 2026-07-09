---
name: mcp-runtime
description: Metagit MCP runtime architecture, tool/resource dispatch, gating, and sampling behavior.
triggers:
  - "mcp runtime"
  - "tools/list"
  - "tools/call"
  - "resources/read"
  - "sampling"
  - "stdio framing"
edges:
  - target: context/architecture.md
    condition: when MCP changes affect broader CLI/core system flow
  - target: context/conventions.md
    condition: when implementing or reviewing runtime/service code patterns
  - target: context/stack.md
    condition: when protocol/library/runtime version constraints matter
  - target: patterns/add-mcp-tool.md
    condition: when adding a new MCP tool or changing tool schemas
  - target: patterns/debug-mcp-runtime.md
    condition: when MCP message loop, framing, or tool dispatch fails
last_updated: 2026-06-30
---

# MCP Runtime

## Overview
- Entry command is `metagit mcp serve` from `src/metagit/cli/commands/mcp.py`.
- Runtime implementation lives in `src/metagit/core/mcp/runtime.py`.
- Runtime uses stdio JSON-RPC with MCP framing (`Content-Length` header + body).
- Gate state is resolved from workspace root + `.metagit.yml` validation before exposing tools.

## Active Runtime Services
- `WorkspaceRootResolver` + `WorkspaceGate` + `ToolRegistry` for state-aware tool visibility.
- Workspace services: index, path-based workspace search (`metagit_workspace_search`), GitNexus semantic query fan-out (`metagit_workspace_semantic_search`), semantic ownership (`metagit_semantic_*`), upstream hints.
- `ManagedRepoSearchService` for `metagit_repo_search` (managed `.metagit.yml` repos only, with tags/status).
- Repo ops service for inspect/sync with mutation guardrails.
- Project context service (`metagit_project_context_switch`, `metagit_session_update`) with session store under `.metagit/sessions/`.
- Workspace snapshot service (`metagit_workspace_state_snapshot`, `metagit_workspace_state_restore`) under `.metagit/snapshots/`.
- Workspace search uses ripgrep when `rg` is on PATH; `metagit_workspace_sync` batches guarded fetch/pull/clone across index rows.
- `metagit_cross_project_dependencies` combines config-declared edges, manifest import hints, shared URL/path detection, and GitNexus per-repo index status.
- Phase 3: `metagit_workspace_health_check` (branch-age / integration staleness when enabled), `metagit_workspace_discover`, `metagit_project_template_apply`, resources `metagit://workspace/health` and `metagit://workspace/context`.
- **Layered MCP resources (Phases 1–4):** `ResourceService` + catalog — static/dynamic URIs, read-only session digest, objectives/approvals/handoffs/events, MCP `prompts/list` + `prompts/get`, dispatch `mcp_resources`; see `docs/reference/mcp-layered-resources-spec.md`.
- Resource publisher for config/repo-status/ops-log resources.
- Bootstrap sampling service with fallback and optional client sampling flow.

## Protocol Notes
- Supported methods: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `prompts/list`, `prompts/get`, `ping`.
- **Layered resources:** start with `metagit://catalog`; escalate to map → prompts → project/repo URIs; avoid full config unless `?view=full`.
- Invalid tool arguments normalize to JSON-RPC error `-32602` with `data.kind=invalid_arguments`.
- Runtime tracks client sampling capability from initialize params and can call `sampling/createMessage`.

## Guardrails
- Inactive gate state only exposes safe baseline tools.
- Mutating sync operations require explicit opt-in arguments/flags.
- Tool schemas are explicitly published in `tools/list` and should stay aligned with dispatcher validation.
