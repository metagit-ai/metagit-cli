# Component Context Graph Series Index (RFC-0026+)

**Status:** Living index
**Date:** 2026-09-06
**Audience:** Coding agents working on [metagit-cli](https://github.com/metagit-ai/metagit-cli)
**Scope:** Add a repository-agnostic **component** layer under existing workspace → project → repository so monorepo sub-projects and polyrepo services share one orchestration model.
**Related series:**
- [ACL RFC series 0007–0013](2026-07-09-acl-rfc-series-index.md)
- [Atlas 0014](2026-07-14-rfc-0014-atlas-design.md)
- [Central State Plane 0015–0018](2026-07-31-central-state-plane-series-index.md)
- [Agent reliability 0019–0025](2026-08-27-agent-reliability-series-index.md)

## Why this series exists

Metagit models software as Workspace → Project → Repository. That matches polyrepo catalogs. It does not treat independently meaningful applications, services, libraries, or infra stacks **inside** one Git repository as first-class context units.

This series adds:

```text
Workspace → Project → Repository → Component
```

Repository remains the version-control boundary. Component is the semantic/operational boundary. Orchestrators should reason about `project/repo/component` without a separate “monorepo mode.”

## Numbering lock

RFC numbers **0016–0025 are reserved** (central state plane + agent reliability). This series starts at **RFC-0026**.

| RFC | Title | Status |
|-----|-------|--------|
| 0026 | Component model (schema, identity, catalog, validation) | Implemented |
| 0027 | Component resolution + CLI (`list` / `show` / `resolve`) | Implemented |
| 0028 | Graph integration (`GraphEndpoint.component`, traversal) | Implemented |
| 0029 | Context compiler (`--component`, depth, inherited profile) | Implemented |
| 0030 | Component ownership / claims | Implemented |
| 0031 | Component discovery (`component detect` / `init`) | Implemented |
| 0032 | Derived working sets from component graphs | Implemented |

Do not reuse 0016–0025. If a later slice is dropped, retire the number in this index rather than recycling it.

## Shared locks (all slices)

- **Additive and backward compatible.** Manifests with no `repos[].components` keep today’s behavior.
- **No monorepo mode.** Do not branch architecture on `ProjectKind.MONOREPO`.
- **One Component model.** Workspace attachment is `repos[].components[]`. Application manifests participate via a catalog adapter over existing `paths[]` and path-bearing top-level `components[]`. Do not retype those YAML lists to `Component` in this series until a later explicit migration RFC.
- **Identity** is always `project/repo/component`. Application manifests use `config.name` for both project and repo.
- **`ProjectPath` stays the git-repo type.** Do not subclass `ProjectPath` as `Component` (git-only fields and YAML key order).
- **Existing top-level `components[]` that are `ref`-only** remain dependency-like (cross-project refs). They are **not** catalog members.
- **`local_workspace_project`** continues to treat `paths` + `dependencies` as synthetic repos. Do not break that.
- **Modality:** RFC-0026 is schema + `config validate` (Config Studio tree comes from schema). RFC-0027 ships `metagit component list|show|resolve`, MCP `metagit_component_*`, and GET `/v3/ops/components` as modality `component_resolve`. RFC-0028 ships `metagit component graph`, MCP `metagit_component_graph`, and GET `/v3/ops/components/graph` as modality `component_graph`. RFC-0029 compile stays `context_compile`. RFC-0030 ownership extends `acl_claim`. RFC-0031 ships `metagit component detect|init`, MCP `metagit_component_detect|init`, GET `/v3/ops/components/detect`, and POST `/v3/ops/components/init` as modality `component_detect`.
- **No LLM** required for discovery or context ranking.
- **Public docs:** ship operator docs with each slice; do not add `docs/reference/rfc-002N*` stubs.

## Dependency graph

```text
RFC-0026 Component model
  └─► RFC-0027 Resolution + CLI
        ├─► RFC-0028 Graph integration
        │     └─► RFC-0029 Context compiler
        │           └─► RFC-0032 Derived working sets
        └─► RFC-0031 Discovery
RFC-0030 Ownership (after 0026 identity; may parallel 0027)
```

## Status table

| RFC | Title | Design | Plan | Status |
|-----|-------|--------|------|--------|
| 0026 | Component model | [design](2026-09-06-rfc-0026-component-model-design.md) | [plan](../plans/2026-09-06-rfc-0026-component-model.md) | **Implemented** |
| 0027 | Resolution + CLI | [design](2026-09-06-rfc-0027-component-resolution-design.md) | [plan](../plans/2026-09-06-rfc-0027-component-resolution.md) | **Implemented** |
| 0028 | Graph integration | [design](2026-09-06-rfc-0028-component-graph-design.md) | [plan](../plans/2026-09-06-rfc-0028-0032-remaining-series.md) | **Implemented** |
| 0029 | Context compiler | [design](2026-09-06-rfc-0029-component-compile-design.md) | [plan](../plans/2026-09-06-rfc-0028-0032-remaining-series.md) | **Implemented** |
| 0030 | Ownership / claims | [design](2026-09-06-rfc-0030-component-ownership-design.md) | [plan](../plans/2026-09-06-rfc-0028-0032-remaining-series.md) | **Implemented** |
| 0031 | Discovery | [design](2026-09-06-rfc-0031-component-discovery-design.md) | [plan](../plans/2026-09-06-rfc-0028-0032-remaining-series.md) | **Implemented** |
| 0032 | Derived working sets | [design](2026-09-06-rfc-0032-derived-components-design.md) | [plan](../plans/2026-09-06-rfc-0028-0032-remaining-series.md) | **Implemented** |

## Architectural north star

Metagit is a context and coordination graph for software systems. Git repositories are one physical boundary. Components sit between repository and files so the same orchestration machinery works for polyrepo, monorepo, and hybrid layouts.
