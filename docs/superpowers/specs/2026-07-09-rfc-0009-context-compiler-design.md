# RFC-0009: Agent Context Compiler — Design

**Status:** Draft  
**Date:** 2026-07-09  
**Series:** [ACL RFC series index](2026-07-09-acl-rfc-series-index.md)  
**Vision:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007 vision; original spec.md retired) § Context Isolation  
**Depends on:** RFC-0008 task identity (preferred); may stub with objective/handoff + repo scope  
**Plan:** [2026-07-09-rfc-0009-context-compiler.md](../plans/2026-07-09-rfc-0009-context-compiler.md)

## Summary

Compute **minimum viable context** for an agent run from a task node (or objective/repo fallback), reusing existing context-pack tiers and repomix profiles. Emit a compiled artifact that fits `context_budget` and can be attached to handoff / agent execution manifest.

## Goals

- CLI/MCP `context compile` that takes task/objective + project/repo and returns a budgeted pack.
- Hierarchy: Global → Workspace → Repository → Directory → Task → File (implement as layered includes, not six separate products).
- Reuse `metagit context pack` tiers 0/1/2 and repomix profiles; do not fork a second pack pipeline.
- Write compile result metadata into task node and/or `AgentExecutionManifest.context_budget` + artifact path.
- Deterministic core path (no required LLM); optional enrichment later.

## Non-Goals

- Semantic KG concept expansion (RFC-0010) beyond optional “include paths from owners” hook.
- Scheduler or merge orchestration.
- Replacing layered MCP resources; compiler may *call* the same services.
- SPA; new embedding index product.

## Architecture

```text
TaskNode | Objective+Repo
        │
        ▼
 ContextCompiler
        ├── ContextPackService (tiers)
        ├── Repomix / repo card helpers
        └── budget trim (token estimate heuristic)
        │
        ▼
 CompiledContext artifact + manifest fields
```

**Package:** prefer extending `src/metagit/core/context/` with `compiler.py` rather than a wholly separate top-level package, unless file size/clarity demands `context_compiler/`.

## Interfaces

### CLI

```bash
metagit context compile --task-id NODE|--objective-id ID \
  --project P --repo R [--tier 1] [--budget N] [--profile bugfix-local] [--json]
```

### MCP

`metagit_context_compile` — returns JSON envelope with sections, estimated tokens, artifact path.

### Artifact (proposed)

`.metagit/tasks/<graph_id>/context/<node_id>.json` or `.metagit/context/compiled/<id>.json` when no graph.

## Persistence

Compiled artifacts under session root; no new global DB.

## Events

Optional: `ContextCompiled` with `source=context` or `taskgraph`.

## Acceptance

- Compile for a known fixture repo returns tier-bounded JSON under budget.
- Without RFC-0008 node, objective+repo path still works.
- Modality parity + docs; skill note in `metagit-context-pack` and/or task-graph skill.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| Context packs, RFC-0008 (preferred) | RFC-0012 (cost estimates), RFC-0013 status |

## Open questions

1. Token estimator: char/4 heuristic vs tiktoken optional dependency?
2. Should compile auto-run inside `dispatch-plan` or remain explicit?

**Recommendation:** heuristic default; optional tiktoken later; keep compile explicit in v1.
