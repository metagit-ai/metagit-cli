# RFC-0017: Agentic Workload Harness — Design

**Status:** Proposed  
**Date:** 2026-07-31  
**Series:** [Central State Plane series index](2026-07-31-central-state-plane-series-index.md)  
**Depends on:** RFC-0015 (plane), RFC-0007–0013 (ACL, task, context compile, scheduler, merge, AOS), optionally RFC-0016 (plane catalog)  
**Intersects:** RFC-0019 (Agent Capability Compilation) — its `CapabilityEnvelope` is the *selection + operating-mode* leg; this harness is the *claim + lifecycle* leg. A `WorkloadEnvelope` should carry a `capability_ref` rather than re-deriving workflow/scope/instructions. See RFC-0019 §"Relationship to RFC-0017".  
**Plan:** (pending)

## Summary

Define a **context-lean agent harness** on top of the central state plane and existing coordination engines. The harness does not replace Cursor/Hermes/OpenClaw runtimes; it standardizes how agents **claim work**, **fetch a budgeted envelope**, **heartbeat**, and **complete** against shared org state — so multi-threaded fleets stay safe and skills-accessible without stuffing full workspace graphs into every prompt.

## Goals

1. Introduce a small **WorkloadEnvelope** document: task/objective identity, repo scope, ACL hints, compiled context ref, token budget, lease ids.
2. Persist envelopes and run records under plane namespaces `harness.envelopes`, `harness.runs`.
3. Wire `metagit aos next` / `schedule next` / `task ready` into a single **harness next** flow that returns an envelope, not a novel scheduler.
4. Enforce lease + claim checks before marking a run `running` (reuse 0007; no new lock primitive).
5. Expose CLI + MCP + skill (`metagit-workload-harness`) for agents.
6. Keep prompts lean: envelope points at `context compile` / context-pack artifacts by reference; agents fetch detail on demand via MCP resources.

## Non-Goals

- Building a new agent runtime, queue broker, or container orchestrator.
- Replacing RFC-0012 scoring policy.
- Embedding full Atlas/GitNexus graphs in the envelope.
- Guaranteeing exactly-once execution across crashed agents (at-least-once + lease expiry is enough).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Harness is a **composition + persistence** layer (like AOS), not a new engine. |
| D2 | Envelope size target: ≤ 2–4 KB JSON typical; hard warn above configurable threshold. |
| D3 | Context bodies live in existing compiler/pack outputs or short-lived plane keys `harness.context/{run_id}` with TTL guidance (delete on complete). |
| D4 | Skills call harness MCP tools; humans may use CLI. |
| D5 | Multi-thread safety = plane CAS + ACL leases; harness never invents a third lock type. |

## Architecture

```text
metagit harness next|heartbeat|complete
        │
        ▼
 HarnessService
   ├─► SchedulerService.preview_next / task ready   (0012 / 0008)
   ├─► ACL lease/claim checks                      (0007)
   ├─► Context compiler / pack (ref only)          (0009 / packs)
   ├─► AOS doctor signals                          (0013)
   └─► DocumentStore harness.*                     (0015)
```

### Models (proposed)

- `WorkloadEnvelope`: `envelope_id`, `run_id`, `task_node_id?`, `objective_id?`, `project`, `repos[]`, `goal`, `acceptance[]`, `acl_hints`, `context_ref`, `budget_tokens`, `lease_id?`, `expires_at`, `created_at`
- `HarnessRun`: `run_id`, `envelope_id`, `agent_id`, `status` (`leased|running|completed|failed|expired`), `heartbeat_at`, `result_summary?`, timestamps
- `ContextRef`: `{kind: pack|compile|resource, uri|path, tier?}`

### Status machine

```text
leased → running → completed
                 → failed
leased/running → expired  (lease TTL)
```

## Interfaces

### CLI

```bash
metagit harness next [--agent-id …] [--json]
metagit harness heartbeat --run-id … [--json]
metagit harness complete --run-id … [--summary …] [--json]
metagit harness fail --run-id … --reason … [--json]
metagit harness status [--run-id …] [--json]
```

### MCP

`metagit_harness_next`, `metagit_harness_heartbeat`, `metagit_harness_complete`, `metagit_harness_fail`, `metagit_harness_status`

### Skill

`metagit-workload-harness`: when to call next/heartbeat/complete; how to resolve `context_ref` via MCP resources; never hold leases past heartbeat policy.

### Plane namespaces

| Namespace | Keys |
|-----------|------|
| `harness.envelopes` | `{envelope_id}` |
| `harness.runs` | `{run_id}` |
| `harness.context` | `{run_id}` optional blob (prefer external compile artifact) |

## Context-lean rules

1. Envelope includes **pointers and budgets**, not file dumps.
2. Default `context_ref.kind=compile` using RFC-0009 with the task/objective id.
3. Agents MAY fetch tier-0 map / repo card via existing MCP resources after `next`.
4. Ontology slices (0018) attach as optional `knowledge_refs[]` of `{adapter, query, max_tokens}` — never inline full graphs.

## Acceptance

- Two concurrent agents calling `harness next` cannot receive the same task node while a lease is held.
- Heartbeat failure / expiry returns the node to schedulable ready set (via existing lease/task semantics).
- Envelope JSON under budget threshold in fixture tests.
- MCP tools gated like other ACTIVE workspace tools.
- Works with `state.backend=local` and with plane cloud/http backends from 0015.
- Docs + skill + modality entry when implemented.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| 0015 plane, 0007–0013 engines, optional 0016 catalog | 0018 knowledge_refs on envelopes |
| Context packs / compile | Skills-accessible multi-agent fleets |

## Open questions

1. Alias `metagit aos next` to harness or keep separate?  
   **Recommendation:** `aos next` remains composition preview; `harness next` persists run + envelope. Cross-link in docs.
2. Should CI runners use harness without ACL worktrees?  
   **Recommendation:** yes — ACL bindings optional when `repos` empty or read-only inspect.
