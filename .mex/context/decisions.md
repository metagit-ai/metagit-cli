---
name: decisions
description: Key architectural and technical decisions with reasoning. Load when making design choices or understanding why something is built a certain way.
triggers:
  - "why do we"
  - "why is it"
  - "decision"
  - "alternative"
  - "we chose"
edges:
  - target: context/architecture.md
    condition: when a decision relates to system structure
  - target: context/stack.md
    condition: when a decision relates to technology choice
  - target: context/mcp-runtime.md
    condition: when decisions involve MCP capability scope, transport, or gating
last_updated: 2026-07-14
---

# Decisions

## Decision Log

### Keep project intelligence in repository-local `.metagit.yml`
**Date:** 2026-05-05  
**Status:** Active  
**Decision:** Project/workspace situational awareness is modeled in `.metagit.yml` and related schema/model files.  
**Reasoning:** Keeps context version-controlled, shareable, and inspectable by both humans and agents without external state dependencies.  
**Alternatives considered:** External-only metadata store (rejected — higher setup burden and weaker local/offline UX), ad-hoc markdown notes (rejected — no schema/validation guarantees).  
**Consequences:** Changes to project/workspace metadata must preserve model/schema compatibility and validation paths.

### Use Python CLI + core service modules as primary architecture
**Date:** 2026-05-05  
**Status:** Active  
**Decision:** Core functionality stays in Python modules under `src/metagit/core/*`, with Click command wrappers under `src/metagit/cli/commands/*`.  
**Reasoning:** Separates UX routing from business logic and keeps features testable in isolation.  
**Alternatives considered:** Fat command handlers (rejected — logic duplication and weaker test boundaries), full web-service-first architecture (rejected — project is CLI-first).  
**Consequences:** New features should be implemented in core services/managers with thin command glue.

### Gate MCP capabilities by valid workspace configuration
**Date:** 2026-05-05  
**Status:** Active  
**Decision:** MCP tool/resource surface is state-aware and only fully enabled when a valid `.metagit.yml` is present at resolved workspace root.  
**Reasoning:** Prevents unsafe or context-poor actions and aligns multi-repo operations with explicit workspace declarations.  
**Alternatives considered:** Always-on toolset (rejected — increases misuse risk), hard failure when config missing (rejected — poorer diagnostic/bootstrapping UX).  
**Consequences:** MCP runtime must keep gate checks, limited inactive tooling, and explicit mutation guardrails for sync operations.

### Derived projects stay in-manifest; skills suggest deferred
**Date:** 2026-07-14  
**Status:** Active  
**Decision:** Surgical agent working sets are first-class derived `workspace.projects[]` entries in the same umbrella `.metagit.yml` (frozen membership, refreshable identity via `derived_from`). Skills v1 is inventory (`skills surface`) only; stack-based suggest into `agent_profile` is phase 2 and must not vendor CC BY-NC registries (e.g. autoskills).  
**Reasoning:** Keeps one SoT file for agents, reuses sync/dedupe/ACL, and avoids coupling checkout scope to campaigns or git subtrees.  
**Alternatives considered:** Sibling manifests (deferred federation), git subtrees (rejected for v1), campaign-driven mounts (wrong abstraction), live membership queries (unstable for agents).  
**Consequences:** Schema adds `derived` / `derived_from`; CLI/MCP create-refresh-include-exclude; skill suggest remains a follow-on design.
