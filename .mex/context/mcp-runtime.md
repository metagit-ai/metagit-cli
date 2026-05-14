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
last_updated: 2026-05-12
---

# MCP Runtime

## Overview
- Entry command is `metagit mcp serve` from `src/metagit/cli/commands/mcp.py`.
- Runtime implementation lives in `src/metagit/core/mcp/runtime.py`.
- Runtime uses stdio JSON-RPC with MCP framing (`Content-Length` header + body).
- Gate state is resolved from workspace root + `.metagit.yml` validation before exposing tools.

## Active Runtime Services
- `WorkspaceRootResolver` + `WorkspaceGate` + `ToolRegistry` for state-aware tool visibility.
- Workspace services: index, path-based workspace search, upstream hints.
- `ManagedRepoSearchService` for `metagit_repo_search` (managed `.metagit.yml` repos only, with tags/status).
- Repo ops service for inspect/sync with mutation guardrails.
- Resource publisher for config/repo-status/ops-log resources.
- Bootstrap sampling service with fallback and optional client sampling flow.

## Protocol Notes
- Supported methods: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `ping`.
- Invalid tool arguments normalize to JSON-RPC error `-32602` with `data.kind=invalid_arguments`.
- Runtime tracks client sampling capability from initialize params and can call `sampling/createMessage`.

## Guardrails
- Inactive gate state only exposes safe baseline tools.
- Mutating sync operations require explicit opt-in arguments/flags.
- Tool schemas are explicitly published in `tools/list` and should stay aligned with dispatcher validation.
