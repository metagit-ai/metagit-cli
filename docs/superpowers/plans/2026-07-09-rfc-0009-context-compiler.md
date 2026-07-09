# RFC-0009 Agent Context Compiler — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `metagit context compile` (CLI + MCP) that builds a budgeted context artifact from a task node or objective+repo, reusing existing context-pack tiers and repomix profile hints.

**Architecture:** `ContextCompiler` in `src/metagit/core/context/compiler.py` orchestrates `ContextPackService`, applies char/4 budget, writes artifacts under `.metagit/context/compiled/` or task graph paths, stamps task node metadata, emits `ContextCompiled` events.

**Tech Stack:** Existing context pack services, Pydantic, Click, MCP, pytest.

**Design:** [2026-07-09-rfc-0009-context-compiler-design.md](../specs/2026-07-09-rfc-0009-context-compiler-design.md)

## Out of scope

Semantic KG expansion, scheduler, merge, tiktoken-as-required-dep, SPA, auto-compile inside dispatch-plan (keep explicit).

## File map

| Action | Path |
|--------|------|
| Create | `src/metagit/core/context/compiler.py` |
| Create | `tests/core/context/test_compiler.py` |
| Create | `docs/reference/context-compiler.md` |
| Modify | `src/metagit/core/context/models.py` — `CompiledContext` |
| Modify | `src/metagit/cli/commands/context.py` — `compile` |
| Modify | MCP registry/runtime — `metagit_context_compile` |
| Modify | modality-parity, skills, CHANGELOG, ROUTER, series index |

## Phases

- [x] **Phase 0 — Contract:** `CompiledContext` / `CompiledContextInputs` models.
- [x] **Phase 1 — Compiler core:** pack + budget + artifact write; unit tests.
- [x] **Phase 2 — Task/objective inputs:** resolve `--task-id`; stamp node; objective linkage.
- [x] **Phase 3 — CLI + MCP:** `context compile --json`; `metagit_context_compile`.
- [x] **Phase 4 — Manifest hook:** `compiled_context_path` + `context_budget` on task node.
- [x] **Phase 5 — Docs + parity + QA:** (run at closeout).

## Acceptance checklist

- [x] Compile under budget for fixture workspace.
- [x] Works without taskgraph (objective+repo fallback).
- [x] No required LLM; no new heavy deps.
- [x] Events (`ContextCompiled`, `source=context`).
