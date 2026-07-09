# RFC-0009 Agent Context Compiler — Implementation Plan

> **For agentic workers:** Expand this phased plan into bite-sized TDD steps when the RFC-0009 MR starts. Prefer subagent-driven-development.

**Goal:** Add `metagit context compile` (CLI + MCP) that builds a budgeted context artifact from a task node or objective+repo, reusing existing context-pack tiers and repomix profiles.

**Architecture:** Extend `src/metagit/core/context/` with a `ContextCompiler` that orchestrates pack/repomix helpers, applies a token heuristic budget, and writes an artifact path onto the task node / agent manifest fields.

**Tech Stack:** Existing context pack services, Pydantic, Click, MCP, pytest.

**Design:** [2026-07-09-rfc-0009-context-compiler-design.md](../specs/2026-07-09-rfc-0009-context-compiler-design.md)

## Out of scope

Semantic KG expansion, scheduler, merge, tiktoken-as-required-dep, SPA, auto-compile inside dispatch-plan (keep explicit).

## File map

| Action | Path |
|--------|------|
| Create | `src/metagit/core/context/compiler.py` |
| Create | `tests/core/context/test_compiler.py` |
| Modify | `src/metagit/cli/commands/context.py` (or sibling) — `compile` subcommand |
| Modify | MCP registry/runtime — `metagit_context_compile` |
| Modify | `scripts/modality-parity.yml`, docs/skills (`metagit-context-pack`), CHANGELOG, ROUTER, series index |

## Phases

- [ ] **Phase 0 — Contract:** Define `CompiledContext` model (sections, estimated_tokens, artifact_path, inputs). Document CLI flags in design-aligned help strings.
- [ ] **Phase 1 — Compiler core:** Given project/repo + tier + budget, call existing pack path; trim/omit sections when over budget (deterministic order). Unit tests with fixtures.
- [ ] **Phase 2 — Task/objective inputs:** Resolve `--task-id` via taskgraph store when present; else `--objective-id` + repo. Write artifact under `.metagit/context/compiled/` or task graph path.
- [ ] **Phase 3 — CLI + MCP:** `context compile --json`; MCP tool; agent_mode safe.
- [ ] **Phase 4 — Manifest hook:** Optional update of `context_budget` / artifact reference on `AgentExecutionManifest` or task node metadata.
- [ ] **Phase 5 — Docs + parity + QA:** Update context-pack skill; modality feature; `task qa:prepush`; `task gitnexus:analyze`; mark series index.

## Acceptance checklist

- [ ] Compile under budget for fixture workspace.
- [ ] Works without taskgraph (objective+repo fallback).
- [ ] No required LLM; no new heavy deps.
- [ ] Events optional (`ContextCompiled`) — include if low-cost.

## Expand-at-MR-start

Break Phase 1–3 into write-failing-test → implement → commit steps following RFC-0008 plan style.
