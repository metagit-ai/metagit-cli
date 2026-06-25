---
name: architecture
description: How the major pieces of this project connect and flow. Load when working on system design, integrations, or understanding how components interact.
triggers:
  - "architecture"
  - "system design"
  - "how does X connect to Y"
  - "integration"
  - "flow"
edges:
  - target: context/stack.md
    condition: when specific technology details are needed
  - target: context/decisions.md
    condition: when understanding why the architecture is structured this way
  - target: context/conventions.md
    condition: when implementing changes across CLI, core services, and tests
  - target: context/mcp-runtime.md
    condition: when task scope includes MCP tools, resources, stdio runtime, or sampling
last_updated: 2026-05-12
---

# Architecture

## System Overview
User runs `metagit` CLI command via `src/metagit/cli/main.py` and command modules under `src/metagit/cli/commands/`.
CLI command loads app config (`metagit.config.yaml`) through `metagit.core.appconfig` and initializes `UnifiedLogger`.
Command handlers call core managers/services in `src/metagit/core/*` (config manager, detection manager, workspace/project helpers, record managers).
For project metadata, `.metagit.yml` is loaded/validated via `MetagitConfigManager` and Pydantic models in `metagit.core.config.models`.
For MCP mode, `metagit mcp serve` enters `MetagitMcpRuntime`, evaluates workspace gate state, exposes tools/resources, and dispatches calls to MCP services (including `metagit_repo_search` for managed-repo-only lookup via `ManagedRepoSearchService`).
For a **local** JSON HTTP surface (development and agents), `metagit api serve` serves `src/metagit/core/api/server.py` endpoints backed by the same search service — not a hosted production API.
Testing flow is pytest-driven from `tests/` with focused unit tests per core module and integration checks for cross-module behavior.

## Key Components
- **CLI command layer (`src/metagit/cli/commands/*.py`)** — routes user actions (`config`, `detect`, `project`, `record`, `workspace`, `mcp`, `search`/`find`, `api`), depends on Click context + core managers.
- **Config subsystem (`metagit.core.config.*`)** — loads/creates/saves `.metagit.yml` and validates schema via Pydantic models; foundational for workspace and MCP gating behavior.
- **Detection subsystem (`metagit.core.detect.*`)** — infers repository metadata (language/framework/dependencies) and feeds generated config/context output.
- **Record subsystem (`metagit.core.record.*`)** — manages normalized records and conversions; used for storage/search flows beyond raw config files.
- **MCP runtime (`metagit.core.mcp.*`)** — stdio JSON-RPC server for tools/resources with state-aware gating, workspace path search/index, managed-repo search (`metagit_repo_search`), upstream hints, repo ops, and bootstrap sampling flow.
- **MCP runtime (`metagit.core.mcp.*`)** — stdio JSON-RPC server for tools/resources with state-aware gating, workspace path search/index, managed-repo search (`metagit_repo_search`), upstream hints, repo ops, bootstrap sampling flow, and objective/session collaboration tools (session begin/digest + objective list/upsert/edit).
- **Managed repo search (`metagit.core.project.search_service`, `search_models`)** — ranks `.metagit.yml` workspace repos with tags/status; shared by CLI, MCP, and the local HTTP API.
- **Local HTTP API (`metagit.core.api.server`)** — optional `ThreadingHTTPServer` with read-only JSON routes for the same managed-repo search and resolve semantics.
- **Local Web ops API (`metagit.core.web.*`)** — localhost-only v3 ops endpoints for workspace maintenance plus objective/session workflows (`/v3/ops/objectives*`, `/v3/ops/session*`) used by the SPA.
- **Agents SPA surface (`web/src/pages/AgentsPage.tsx`)** — one route with `Templates`, `Objectives`, and `Sessions` sub-tabs; the page combines agent catalog calls (`/v3/agents/*`) with objective/session ops endpoints (`/v3/ops/objectives*`, `/v3/ops/session*`) and uses client-side polling controls for lightweight live updates.

## External Dependencies
- **Git providers (GitHub/GitLab APIs via provider modules)** — used for metadata/provider operations; provider wiring is optional/config-driven.
- **Git repository access (`GitPython`)** — used for repo introspection and sync-like operations (`inspect`, `fetch`, `pull`, `clone`) in project/MCP flows.
- **YAML/Pydantic stack (`PyYAML` + `pydantic`)** — enforces `.metagit.yml` and app config shape; all config entry points depend on this validation boundary.
- **MCP client host (Cursor/other MCP-compatible runtime)** — provides stdio transport and optional sampling capability (`sampling/createMessage`) for bootstrap generation.

## What Does NOT Exist Here
- No production-grade multi-tenant HTTP deployment; the bundled HTTP server is for local use alongside the CLI and MCP.
- No relational application database backing core runtime flows; state is file/workspace/repo driven.
- No centralized remote orchestration control plane for enterprise-wide repo execution in this repository.
- No full SBOM pipeline; project focuses on situational awareness metadata, not exhaustive dependency inventory.
