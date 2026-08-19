# RFC-0019: Agent Capability Compilation — Design

**Status:** Proposed
**Date:** 2026-08-18
**Parent:** [Routing Engine spec](2026-08-10-metagit-routing-engine-spec.md) (RequestClass, `route`/`run`/`lane`)
**Depends on:** RFC-0009 (context compiler), existing routing engine, `AgentInstructionsResolver`, `AgentProfileService`
**Intersects:** RFC-0017 (Agentic Workload Harness) — see [§Relationship to RFC-0017](#relationship-to-rfc-0017)
**MVP spec:** [`spec.md`](../../../spec.md) (repo root)
**Plan:** (pending)

## Summary

Compile Metagit's existing **request-class catalog** plus **workspace topology** into a
deterministic, task-scoped **`CapabilityEnvelope`** that an external agent orchestrator can
consume to select a repository + operating mode + contract — without a human in the loop and
without re-discovering topology. Metagit supplies the *what*; the orchestrator owns the *how*
(model, process, scheduling, retries, and enforcement of the advisory scope).

A **capability** is a `RequestClass` whose optional `capability` block is present. The block
adds the dimensions routing lacks: a **selector** (which topology slice), a **workflow**
(ordered step names + gate flags — a contract, not an executor), an **expected output**, and
an advisory read/write **scope**.

## Goals

1. Extend `RequestClass` **in place** with one optional `capability` block. No parallel model.
2. `metagit capability resolve "<ask>"` → deterministic ranked candidates (reuse the existing
   token-overlap router) filtered by a selector gate against topology.
3. `metagit capability compile --id CAP --project P [--repo R]` → a `CapabilityEnvelope`
   composing resolved repo + layered instructions + effective profile + RFC-0009 context.
4. Expose both over MCP (`metagit_capability_resolve`, `metagit_capability_compile`).
5. Zero breaking changes to existing manifests or to `route`/`run`/`lane`.

## Non-Goals

- Model selection, subagent process/lifecycle, scheduling, concurrency, retries, board state.
- **Enforcement** of path scope — Metagit *declares*, the orchestrator *enforces*.
- A workflow *engine* — Metagit emits an ordered step list + gate flags (a contract), not an
  executor.
- Multi-repo capabilities, dependency-graph scope expansion, semantic/LLM routing, generated
  static skills, HTTP API — all deferred (see `spec.md` §13).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | A capability **is** a `RequestClass` with a non-null `capability` block. The routing catalog is the capability catalog — no new store. |
| D2 | **`lane` stays a promotion tier, never a workflow.** Overloading it would break `lane eval` / `run --lane`. The operating mode lives in `capability.workflow`. |
| D3 | Selection is **deterministic**: existing `rank_classes` trigger overlap + a hard selector AND-gate. LLM tie-break is deferred. |
| D4 | Compilation **reuses** `ContextCompiler` (RFC-0009); no second context pipeline. |
| D5 | `capability.scope` is **advisory** in Metagit; enforcement is the orchestrator's responsibility. |
| D6 | The `CapabilityEnvelope` is **orchestrator-agnostic** — no orchestrator types leak into the schema. |

## Architecture

```text
{ask, project?, repo?}
   │  capability resolve   → rank_classes(triggers) + selector gate → candidates
   ▼
CapabilityService.compile(--id CAP --project P [--repo R])
   ├─► AgentInstructionsResolver → effective instructions (file→workspace→project→repo)
   ├─► AgentProfileService       → effective skills / mcp / rules
   ├─► ContextCompiler (RFC-0009)→ budgeted context artifact (by reference)
   └─► capability.scope          → advisory allowed/writable paths
   ▼
CapabilityEnvelope (JSON)  →  orchestrator selects model+process, enforces scope, emits MR
```

Hierarchy drawn from: `WORKSPACE → PROJECT → REPOSITORY → CAPABILITY → TASK` (the requested
`FILE` level collapses into the existing instruction layer; `LANE` is replaced by `CAPABILITY`).

## Interfaces

New models in `src/metagit/core/routing/models.py` (extension) and
`src/metagit/core/routing/capability_models.py` (envelope). Full definitions and YAML examples
live in `spec.md` §6. New service: `core/routing/capability_service.py`.

### CLI

```bash
metagit capability list    [--project P] [--json]
metagit capability resolve "<ask>" [--project P] [--repo R] [--limit N] [--json]
metagit capability show    --id CAP [--json]
metagit capability compile --id CAP --project P [--repo R] [--task-id N] [--tier 0|1|2] [--json]
metagit capability doctor  [--json]
```

### MCP

`metagit_capability_list`, `metagit_capability_resolve`, `metagit_capability_show`,
`metagit_capability_compile` — active-workspace gated, mirroring `metagit_route_query` and
`metagit_context_compile`.

## Persistence

- Capabilities: existing routing catalog (one YAML per class under `routing.catalog`).
- Compiled context: existing RFC-0009 artifact paths.
- Events: `CapabilityCompiled` rows append to `.metagit/events/capability.jsonl`
  (mirror `ContextCompiler._append_event`).

No new store, no new plane namespace.

## Relationship to RFC-0017

RFC-0017 (Agentic Workload Harness) defines a **`WorkloadEnvelope`**. The two envelopes are
**complementary legs of one pipeline, not competitors** — and must not grow into two parallel
schemas.

| | RFC-0019 `CapabilityEnvelope` | RFC-0017 `WorkloadEnvelope` |
|---|---|---|
| Leg | **Selection + operating mode** (the *what*) | **Claim + lifecycle** (the *how it runs*) |
| Answers | "Given this ask, which repo + workflow + gates + expected output + instructions + scope?" | "Claim the next ready node safely; heartbeat; complete." |
| Statefulness | Stateless projection of config (deterministic) | Stateful: lease ids, run status, heartbeat, plane namespaces `harness.*` |
| Context | Composes + references an RFC-0009 artifact | References context by pointer (`context_ref`) |
| Owns | workflow, gates, expected_output, instructions, advisory scope | lease/claim safety, run status machine, at-least-once semantics |

**Recommended reconciliation (for whoever implements the second of the two):**

1. **Capability is the single source of "operating mode."** A `WorkloadEnvelope` must **not**
   re-derive `workflow` / `scope` / `instructions`. It should carry a reference —
   `capability_ref: { capability_id, compiled_path }` — or embed a `CapabilityEnvelope` whole,
   rather than duplicate those fields.
2. **Division of ownership:** RFC-0019 owns *selection + mode contract*; RFC-0017 owns
   *claim + lease + lifecycle*. Neither invents the other's concern (RFC-0017 D5: "never
   invents a third lock type" — likewise capability never invents a lease/run state).
3. **Shared substrate both reuse:** repo scope, ACL command hints, the RFC-0009
   `context_ref`, and the lean-pointer principle (RFC-0017 §Context-lean; RFC-0019 embeds a
   *reference*, not file dumps).
4. **Concrete wiring if both ship:** `metagit harness next` returns a `WorkloadEnvelope`
   whose `capability_ref` points at a `capability compile` output; the agent resolves the
   capability for its mode contract, then heartbeats/completes via the harness.

This keeps a clean seam: **one envelope for "what to do and how it's shaped" (0019), one for
"safely claiming and running it" (0017).**

## Acceptance

See `spec.md` §16. Summary: existing manifests/tests pass unchanged; `resolve` is deterministic
with a selector-aware `why`; `compile` emits a schema-valid envelope with repo/cwd/scope/
instructions/skills/workflow/gates/expected_output/context ref; MCP twins match CLI; `route`/
`run`/`lane` behave identically to pre-change.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0009 context compiler; routing engine; `AgentInstructionsResolver`; `AgentProfileService` | RFC-0017 harness (`capability_ref` on workload envelopes); any external orchestrator's selection step |

## Open questions

1. When both RFC-0017 and RFC-0019 exist, does `capability_ref` embed the whole envelope or
   just `{capability_id, compiled_path}`?
   **Recommendation:** reference by `{capability_id, compiled_path}`; the agent fetches the
   full envelope on demand (consistent with RFC-0017's lean-pointer rule).
2. Single-repo MVP `repository` vs. future `repositories[]` for multi-repo — widen the field
   when multi-repo lands (`spec.md` §13), keeping the singular case as `repositories[0]`.
