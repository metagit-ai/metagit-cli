# RFC-0014: Metagit Atlas — Design

**Status:** Proposed (awaiting review)  
**Date:** 2026-07-14  
**Feature name:** Atlas  
**Primary command namespace:** `metagit atlas`  
**Plan (Phase 0–1):** [2026-07-14-rfc-0014-atlas.md](../plans/2026-07-14-rfc-0014-atlas.md)  
**Supersedes draft:** `docs/superpowers/plans/2026-07-14-atlas.md` (promoted into this design + Phase 0–1 plan)

## Summary

Atlas is a versioned, machine-readable semantic layer for a source repository (and later, federations of repositories). It complements the physical source tree with an explicit map of capabilities, concepts, contracts, decisions, implementation evidence, dependencies, risks, and verification evidence.

An Atlas is stored beside the code in `.atlas/`. It is not a replacement for source code, documentation, a package graph, Metagit’s workspace catalog, RFC-0010 semantic ownership, or GitNexus. It is the layer that connects those artifacts to the intent they serve.

Atlas has two deliberately separate kinds of information:

- **Generated evidence** — what currently exists, based on parsers, repository metadata, tests, dependency graphs, and configured integrations.
- **Curated intent** — why it exists and what must remain true: domain vocabulary, capability boundaries, invariants, decisions, ownership, and risk classification.

Source files remain authoritative for implementation. The Atlas is authoritative only for explicitly curated semantic metadata and is otherwise a reproducible projection with provenance.

## Relationship to existing Metagit features

| System | Owns | Atlas relationship |
|--------|------|--------------------|
| Workspace catalog / `.metagit.yml` | Repo membership, tags, sync paths | Atlas may discover repo identity via Metagit; does not replace catalog |
| Context packs / RFC-0009 compiler | Budgeted session/task packs from workspace + repo text | Atlas **context** packets are repo-semantic; compiler may later *include* Atlas slices (Phase 2+), not fork packs |
| RFC-0010 semantic KG | Workspace-level concept → path ownership under `.metagit/graph/` | Orthogonal: ownership advice for claims. Atlas capabilities/concepts are repo-local under `.atlas/` and richer (contracts, evidence, verification). Optional later `maps_to` bridges |
| `graph.relationships` | Cross-project edges in `.metagit.yml` | Federation (Phase 4) may reference these; local Atlas does not write them |
| GitNexus | Structural/call graph | Optional adapter (Phase 3); never a core dependency |
| mex | Local conventions/patterns | Optional adapter (Phase 3) |
| Campaign “atlas” wording | Informal name for workspace repo membership checks in `CampaignService` | **Naming collision only.** CLI `metagit atlas` is unrelated. Follow-up may rename campaign comments/docs to “workspace membership” |

## Goals

Atlas SHALL:

1. Give humans and agents a small, navigable starting context for safe work in an unfamiliar repository.
2. Represent repository knowledge as typed entities and relationships, not disconnected summaries.
3. Trace capabilities and concepts to concrete evidence: files, symbols, APIs, schemas, tests, decisions, dependency edges.
4. Federate repository-local Atlases through Metagit without one central monolithic database (Phase 4).
5. Integrate structural intelligence through pluggable adapters and stable import contracts; mex and GitNexus are non-required examples.
6. Support deterministic full generation and fast incremental refresh after local changes.
7. Expose read-only query and context-routing through CLI first; MCP in Phase 2.
8. Preserve provenance, confidence, freshness, and access classification for every generated assertion.
9. Be useful before a repository is perfectly documented; incomplete knowledge must be representable, never fabricated.

## Non-goals (first implementation / Phase 0–1)

- Replace Git, code review, issue tracking, ADRs, or source documentation.
- Infer business intent with certainty from source alone.
- Make Atlas a required build dependency for ordinary application builds.
- Automatically rewrite production code or open pull requests.
- Expose secrets or restricted metadata through federation or MCP.
- Require formal proofs (contracts/verification must remain extensible).
- Universal ontology for every organization or language.
- MCP server, federation publish/pull, mex/GitNexus adapters, OpenAPI extractors (later phases).
- Public HTTP API surface (Phase 0–1 uses in-process Python services only).

## Design principles

1. **Evidence before assertion.** Generated claims carry source, timestamp, extractor version, and confidence.
2. **Intent is curated.** Automation may propose intent but cannot silently promote it to a trusted invariant or decision.
3. **Local ownership, federated discovery.** A repository owns its `.atlas`; Metagit indexes published views later.
4. **Contracts over implementation topology.** Agents should discover a capability, its constraints, and its evidence before traversing files.
5. **Additive adoption.** `atlas init` creates useful output without reorganizing code or requiring symlinks.
6. **Portable, inspectable artifacts.** Canonical files are text formats suitable for review and version control.
7. **Least disclosure.** Export, federation, and MCP obey classification policy (Phase 2/4).
8. **Staleness is data.** An old Atlas is not silently presented as current.

## Architecture

```text
                          Human-curated intent
                    (capabilities, invariants, ADRs)
                                     |
                                     v
Source + docs + tests + config -> Extractors -> Local .atlas/ graph
                                     ^                   |
                                     |                   v
          Optional adapters --------+             Query/index projection
          (mex, GitNexus, ...) -----+                   |
          Metagit repo catalog ----+                   v
                            Metagit federation / MCP context API
                            (Phase 3–4; not Phase 0–1)
```

### Components (full vision)

| Component | Responsibility | Phase |
|-----------|----------------|-------|
| Atlas CLI | init, validate, generate, refresh, query, … | 1+ |
| Extractor framework | Structural evidence from parsers, docs, tests, manifests | 1+ |
| Canonical store | YAML in `.atlas/` | 0–1 |
| Derived index | Rebuildable local JSON/SQLite under `.atlas/index/` (gitignored) | 1 |
| Ontology validator | Schemas, IDs, relations, policy | 0–1 |
| Federation service | Cross-repo published exports | 4 |
| MCP server | Read-only discovery / context / impact | 2 |

### Package

`src/metagit/core/atlas/` — models, paths, validation, extractors, store, service, query.  
CLI: `src/metagit/cli/commands/atlas.py` → `atlas_group`.

### Source of truth and precedence

| Artifact | Authority | Write mode |
|----------|-----------|------------|
| Source code, schemas, build configuration | Implementation fact | Existing project workflow |
| `.atlas/intent/**`, `.atlas/ontology/**` | Curated intent | Human-reviewed edits or explicit import |
| `.atlas/generated/**` | Generated observations | CLI only |
| `.atlas/overrides/**` | Curated corrections | Human-reviewed edits |
| `.atlas/index/**` | Derived cache | Rebuilt; ignored by Git |
| Federated registry | Published projection | Phase 4; derived from local exports |

Curated metadata overrides a generated classification only through an explicit override record. It never alters underlying evidence.

## Ontology model

API version: `atlas.metagit.dev/v1alpha1`.

### Core entity kinds

`Domain`, `Concept`, `Capability`, `Component`, `Interface`, `Contract`, `Invariant`, `Decision`, `Implementation`, `DataAsset`, `Verification`, `Actor`, `Risk`, `Repository`.

### Core relationships

```yaml
implements: exposes: consumes: depends_on: contains: owns:
governed_by: constrained_by: verified_by: stores: produces:
modifies: supersedes: maps_to:
```

Extensions MAY use namespaced types (`pci:processes_cardholder_data`). Unnamespaced core terms are reserved.

### Entity envelope

```yaml
apiVersion: atlas.metagit.dev/v1alpha1
kind: Capability
metadata:
  id: capability:payment.capture
  name: Capture Payment
  lifecycle: active                 # proposed | active | deprecated | retired
  classification: confidential       # public | internal | confidential | restricted
  owners: [team:payments]
  labels: { domain: billing }
  provenance:
    source: curated                  # curated | generated | imported
    updatedAt: 2026-07-14T00:00:00Z
spec:
  purpose: Convert an authorized payment into a settled transaction.
  # type-specific fields…
```

### Evidence

Generated entities/edges MUST include an `evidence` array:

```yaml
evidence:
  - id: evidence:symbol:billing/PaymentService.capture
    kind: symbol
    locator: src/billing/payment_service.py#PaymentService.capture
    revision: 8b4c6e2
    extractor: python-ast@1.0.0
    observedAt: 2026-07-14T18:20:00Z
    confidence: 1.0
```

## `.atlas/` directory layout

```text
.atlas/
├── atlas.yaml
├── README.md
├── ontology/          # curated domain, concepts, capabilities, extensions/
├── intent/            # contracts, invariants, decisions, risks, ownership
├── generated/         # inventory, symbols, interfaces, dependencies, verifications, imports/, manifests/
├── mappings/          # semantic-to-evidence, external-ids
├── overrides/         # classifications, links, suppressions
├── federation/        # export.yaml, imports/   (Phase 4)
├── policy/            # access.yaml, generation.yaml
└── index/             # gitignored derived index
```

Symlink mirrors are optional and not required. Locators reference the source tree directly.

## CLI (full vision)

| Command | Purpose | Phase |
|---------|---------|-------|
| `metagit atlas init` | Create layout; optional first generate | 1 |
| `metagit atlas generate` | Full deterministic generation | 1 |
| `metagit atlas refresh [paths…]` | Incremental update | 1 (basic) |
| `metagit atlas validate` | Schemas, links, policy, freshness | 1 |
| `metagit atlas status` | Freshness, coverage, adapters | 1 |
| `metagit atlas query <expression>` | Local graph query (DSL + JSON) | 1 (subset) |
| `metagit atlas context …` | Bounded agent context packet | 2 |
| `metagit atlas impact …` | Semantic + structural blast radius | 2 |
| `metagit atlas import <adapter>` | Optional integration refresh | 3 |
| `metagit atlas propose` | Reviewable mapping/intent proposals | 2+ |
| `metagit atlas publish` / `pull` | Federation | 4 |
| `metagit atlas doctor` | Diagnostics | 2 |
| `metagit atlas ecosystem query` | Cross-repo | 4 |

## Query / service API (Phase 0–1)

In-process only (no HTTP listener in Phase 0–1):

- `get_entity(id)`, `list_entities(kind=…, labels=…)`
- `traverse(start, relations=…)`
- `query(expression | JSON object)`
- `status()`

Phase 2 adds `context` / `impact` and MCP tools (`atlas_find`, `atlas_describe`, `atlas_context`, …) with `metagit_atlas_*` naming to match Metagit MCP conventions.

## Security and privacy

1. Never parse, index, export, or return secret values. Default exclusions: `.env`, credential stores, private keys, token files, build caches, configurable sensitive paths.
2. Evidence locators reference paths/symbols, not source snippets.
3. Every entity/edge/export has a classification; federation/MCP apply the most restrictive included classification.
4. Export is deny-by-default; `restricted` must not leave the repo without an explicit rule (Phase 4).
5. Adapters receive minimal filesystem/env access; must not serialize credentials into Atlas artifacts (Phase 3).
6. Generated output is untrusted until schema-validated.

## Extensibility

- Schema version `atlas.metagit.dev/v1alpha1`; additive changes within a compatibility line.
- Entity kinds, relations, extractors, adapters are extension points.
- Unknown extension fields retained by compatible tools; ignored safely by others.
- Core MUST operate with zero optional adapters.

## Implementation phases

### Phase 0 — Design and schema foundation (this MR series start)

JSON/Pydantic schemas, ID rules, lifecycle/classification enums, directory layout helpers, deterministic serialization, validation library, fixtures for a small Python (and minimal Node inventory) repository.

### Phase 1 — Local Atlas MVP

`init`, `generate`, `validate`, `status`, local query index. File inventory, language/module discovery, Python symbol locators, test discovery, provenance, manifests, curated concepts/capabilities/invariants, basic incremental refresh, modality CLI+docs (no MCP yet).

### Phase 2 — Context routing and contracts

Mappings UX, `atlas context`, OpenAPI/protobuf/schema extraction, decisions/risks/overrides freshness CI, read-only MCP (`metagit_atlas_*`).

### Phase 3 — Integration adapters

mex + GitNexus reference adapters behind flags; graceful degradation; generic adapter protocol.

### Phase 4 — Federation

Exports, publish/pull, cross-repo lookup, explicit semantic linking, conflict reporting, classification-aware filtering, Metagit workspace integration.

### Phase 5 — Advanced assurance

Proof references, SAST/SBOM, policy-as-code gates, richer editor views, org ontology packages.

## Acceptance criteria

### Phase 0–1 (MVP) acceptance

1. `metagit atlas init` creates a valid layout without modifying source code.
2. `metagit atlas generate` produces deterministic generated output for an unchanged supported fixture repository.
3. Every generated entity and edge has provenance, revision, observed timestamp, and confidence.
4. A user can define a curated capability, link it to source evidence and an invariant, and validate the result.
5. A local query can traverse from a capability to implementation evidence and verification evidence.
6. A changed source file refreshes only the affected generated records on a supported fixture; the CLI reports its invalidation reason.
7. Missing/disabled/failed optional adapters never block core generation (adapters absent in Phase 1; status reports `n/a`).
8. A secret fixture is excluded from generated content.
9. Invalid IDs, dangling references, prohibited containment cycles, and classification violations fail validation with actionable diagnostics.
10. Modality parity entry for CLI + docs (+ optional skill); MCP deferred to Phase 2.

### Federation acceptance (Phase 4 — not this plan)

Two fixture repos publish exports; same-named capabilities are not auto-merged; restricted entities filtered; conflicts visible.

## Decisions (locked for Phase 0–1)

1. **Serialization:** YAML authoring for canonical `.atlas/` files; normalized JSON derived index under `.atlas/index/`; validate with Pydantic + `jsonschema` artifacts under `schemas/atlas/`.
2. **Derived index:** Fully portable inside the repo path; rebuild on demand; gitignore `.atlas/index/`.
3. **Query language:** Support both a small graph DSL string and a JSON query object; Phase 1 ships a minimal subset (kind/id/name filter + one-hop `traverse`).
4. **Generated files default:** Commit generated canonical YAML by default (`atlas.yaml` `commitGenerated: true`) so the next agent has an atlas without regenerating; teams may disable.
5. **Language extractors (Phase 1):**
   - **Python symbols:** stdlib `ast` (no new dependency).
   - **Node/JS:** inventory + test discovery from `package.json` / common test globs; full symbol extraction deferred unless a thin tree-sitter spike fits the MR without blocking MVP.
   - Tree-sitter (or equivalent) remains the preferred path for multi-language symbols in Phase 1.5/2; record spike notes in `.mex/context/decisions.md` when chosen.
6. **Service surface:** In-process Python API only in Phase 0–1; no `api serve` Atlas routes.
7. **MCP:** Deferred to Phase 2.
8. **Adapters (mex/GitNexus):** Deferred to Phase 3; core never imports them.
9. **Modality:** `atlas_local` feature — CLI + documentation (+ skill when useful); no MCP markers until Phase 2.
10. **Persistence root:** Repository-local `.atlas/` at the target repo root (the repo being mapped), not under workspace `.metagit/`. Session/workspace Metagit state remains separate.

## Open questions (defer past Phase 1)

1. Metagit federation transport, authentication, and export signing model (Phase 4 RFC addendum).
2. How Atlas links to existing ADR formats without duplicating content (Phase 2).
3. Organization-level ontology package governance (Phase 5).
4. Whether campaign code comments should rename “atlas” → “workspace membership” (docs-only cleanup; independent).

## Testing strategy (Phase 0–1 focus)

| Layer | Tests |
|-------|-------|
| Schema/model | Pydantic + jsonschema fixtures; ID normalization; relation validation |
| Extractors | Golden fixtures (Python); secret exclusion; deterministic output |
| Incremental | Change-set fixture; invalidation reason; stale curated links retained |
| Query | Traverse capability → evidence; JSON + DSL minimal forms |
| CLI | `CliRunner` init/generate/validate/status/query |
| Security | `.env` / key fixtures never appear in generated YAML |

Include a messy legacy fixture later (Phase 2+): inconsistent names, partial docs, unavailable adapter.

## Definition of done (pilot)

A representative repository can initialize a local Atlas with no optional adapters, capture curated capabilities and invariants, generate deterministic evidence, validate, and query capability→evidence locally via CLI. Phase 2+ adds MCP context packets and federation for multi-repo pilots.

## Worked example (curated capability)

```yaml
# .atlas/ontology/capabilities.yaml
entities:
  - apiVersion: atlas.metagit.dev/v1alpha1
    kind: Capability
    metadata:
      id: capability:refund.issue
      name: Issue Refund
      lifecycle: active
      classification: internal
      owners: [team:payments]
      provenance: { source: curated }
    spec:
      purpose: Return settled funds without duplicate refunds.
      invariants:
        - invariant:refund.amount_not_exceeds_capture
        - invariant:refund.idempotent
```

See original proposal narrative for longer agent-context examples (Phase 2).
