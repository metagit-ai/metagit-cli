# Agent Capability Compilation (RFC-0019)

<!-- modality:capability_compilation -->

Metagit compiles its existing **request-class catalog** and **workspace topology** into a
deterministic, task-scoped **capability envelope** that an external agent orchestrator can
consume to select a repository + operating mode + contract — without a human in the loop
and without re-discovering topology.

This is **not** the routing run ledger (`metagit run`), the promotion-tier evaluator
(`metagit lane eval`), the task graph (RFC-0008), or the context compiler (RFC-0009) — it
*composes* the router and the context compiler into one envelope.

> **Status:** proposed (MVP). See `spec.md` at the repo root for the full implementation
> spec, deferred scope, and acceptance criteria.

## Concept

A **capability** is a `RequestClass` (routing catalog entry) whose optional `capability`
block is present. The block adds the dimensions routing lacks: a **selector** (which
topology slice it applies to), a **workflow** (ordered step names + gate flags — a
contract, not an executor), an **expected output**, and an advisory read/write **scope**.

> A `RequestClass` **without** a `capability` block behaves exactly as before. The word
> **lane** stays reserved for promotion tiers (`deterministic|skilled|novel`); a lane is
> **not** a workflow.

Hierarchy the envelope draws from:

```text
WORKSPACE → PROJECT → REPOSITORY → CAPABILITY → TASK
```

## Flow

```text
{ask, project?, repo?}
   │  metagit capability resolve   → rank_classes(triggers) + selector gate → candidates
   ▼
   │  metagit capability compile --id CAP --project P [--repo R]
   │     AgentInstructionsResolver → effective instructions (file→workspace→project→repo)
   │     AgentProfileService       → effective skills / mcp / rules
   │     ContextCompiler (RFC-0009)→ budgeted context artifact
   ▼
CapabilityEnvelope (JSON)  →  orchestrator selects model+process, enforces scope, emits MR
```

Everything left of the envelope is Metagit (the *what*). The orchestrator owns the *how*
(model, process, scheduling, retries, and **enforcement** of the advisory scope).

## Configuration

Activate the catalog with a `routing:` block, then add a `capability` block to any class:

```yaml
routing:
  catalog: knowledge/requests/entries
  runs: knowledge/requests/runs

# knowledge/requests/entries/REQ-terraform-module-change.yml
id: REQ-terraform-module-change
title: Terraform module change
triggers: [upgrade terraform module, modify vpc module, bump module version]
skill: terraform-module-editing
gates: [fmt, validate, plan]
tier: skilled            # ROUTING tier — unchanged
mutates: true
capability:              # NEW block — makes this a capability
  selector:
    project_types: [iac]
    tags: { iac: terraform, layer: module }
    path_globs: ["**/*.tf"]
  scope:                 # advisory: Metagit declares, the orchestrator enforces
    allowed_paths: ["**/*.tf", "**/*.tfvars", "CHANGELOG.md"]
    writable_paths: ["**/*.tf", "**/*.tfvars", "CHANGELOG.md"]
    forbidden_paths: ["*.tfstate", "*.tfstate.*"]
  workflow:
    - { name: inspect }
    - { name: fmt,      command: "terraform fmt -recursive", gate: true }
    - { name: validate, command: "terraform validate",       gate: true }
  expected_output: merge_request
  constraints: ["Never edit *.tfstate"]
```

## CLI

```bash
metagit capability list    [--project P] [--json]
metagit capability resolve "<ask>" [--project P] [--repo R] [--limit N] [--json]
metagit capability show    --id CAP [--json]
metagit capability compile --id CAP --project P [--repo R] \
    [--task-id N] [--graph-id G] [--objective-id ID] \
    [--tier 0|1|2] [--budget N] [--no-context] [--json]
metagit capability doctor  [--json]
```

`compile` writes a `CapabilityEnvelope` and, unless `--no-context`, links a RFC-0009
context artifact under `.metagit/context/compiled/<id>.json` (or the task node path when
`--task-id` resolves).

## MCP

`metagit_capability_list`, `metagit_capability_resolve`, `metagit_capability_show`,
`metagit_capability_compile` — active-workspace gated, mirroring `metagit_route_query`
and `metagit_context_compile`. Each returns the same payload as its CLI twin.

## Envelope schema

`CapabilityEnvelope` is orchestrator-agnostic (no orchestrator types leak in) and is
published as `schemas/capability_envelope.schema.json`. Key fields: `capability_id`,
`project`, `repository`, `cwd`, `allowed_paths`/`writable_paths` (advisory), `instructions`
(+ `instruction_layers`), `skills`/`mcp`/`rules`, `workflow`, `gates`, `expected_output`,
`context_artifact_path`, `source: metagit`.

## Events

`CapabilityCompiled` rows append to `.metagit/events/capability.jsonl` and appear in
`metagit context events` with `source: capability`.

## Selection semantics

1. **Trigger match** — existing `rank_classes` token-overlap over `triggers` (no LLM).
2. **Selector gate** — a hard AND-match over `project_types`, `domains`, `tags`,
   `path_globs`, `languages`; an empty selector matches any topology (global capability).

Deterministic routing is always sufficient to produce an answer. No match →
`no_capability_match` (never fabricate); selector matches >1 repo → `ambiguous_repo`
(require explicit `--repo`).

## Related

- Routing / request classes: `metagit route query|list|show`, `metagit run`,
  `metagit lane eval` (`src/metagit/core/routing/`)
- [Context compiler (RFC-0009)](context-compiler.md)
- [Task graph (RFC-0008)](task-graph.md)
- Agent instructions / profiles: `src/metagit/core/workspace/agent_instructions.py`,
  `src/metagit/core/agent/profile_service.py`
- Full spec: `spec.md` (repo root)
