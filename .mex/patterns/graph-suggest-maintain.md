---
name: graph-suggest-maintain
description: Maintaining workspace graph.relationships (durable fields, validation, ignore-aware suggest scanning, stale review).
triggers:
  - "graph.relationships"
  - "graph suggest"
  - "GraphRelationship"
  - "stale_manual"
edges:
  - target: "../context/conventions.md"
    condition: when writing or reviewing config/graph code
last_updated: 2026-07-28
---

# Graph Suggest / Maintain

## Context
`workspace.graph.relationships` is a thin durable edge list (`src/metagit/core/config/models.py::GraphRelationship`)
maintained via `metagit config graph suggest|export` (`src/metagit/core/config/graph_suggest.py`,
`src/metagit/cli/commands/config.py`). Design:
`docs/superpowers/specs/2026-07-28-durable-graph-suggest-design.md`.

## Steps
1. Use leaf `--config-path/-c` on `graph suggest`/`graph export` for the manifest path
   (mirrors `config validate`); `--workspace-root` is the separate scan/checkout root
   (default `appconfig.workspace.path`). Global `metagit -c` is appconfig only, never
   `.metagit.yml`.
2. Any new recursive scan over managed repos (import hints, terraform, etc.) must go
   through `metagit.core.utils.repo_walk.iter_repo_files()` — it always applies the
   shared scaffold denylist (`metagit.core.utils.scaffold_paths`) and honors nested,
   git-scoped `.gitignore` (pruned during the walk, not post-filtered). Do not add a new
   `Path.rglob`/`os.walk` for this purpose.
3. New/edited `GraphRelationship` entries need a non-blank `id` and valid `from`/`to`
   endpoints (`workspace.projects[].repos`; project-level edges with no `repo` are fine).
   `graph_validation.validate_graph_relationships()` enforces this — `config validate`
   calls it, and `suggest --apply` validates the *patched document* via
   `ConfigPatchService.draft()` (the same `apply_operations` path `patch()` writes) before
   saving (failures surface as `GraphSuggestApplyResult.validation_errors`, no write).
4. Lifecycle fields: `status` (`active`/`deprecated`/`proposed`) and `provenance`
   (`manual`/`promoted`/`imported`). Suggested edges get `provenance="promoted"`. Setting
   `status="deprecated"` on a manual edge excludes it from `stale_manual` review.
5. `GraphSuggestResult.stale_manual[]` is report-only: active manual edges with no
   supporting inferred edge in the current scan. There is no auto-mutate/`--mark-stale` —
   an agent or human reviews and edits the manifest by hand.
6. After changing suggest/validation behavior, regenerate schema/docs:
   `schemas/metagit_config.schema.json`, `docs/reference/metagit-config.*`, and
   `docs/reference/metagit-config.full-example.yml` (via `metagit config example`).

## Gotchas
- Nested `.gitignore` patterns are scoped to the directory that declared them (ancestor
  chain check), not merged into one global set — a pattern in `a/.gitignore` must not
  exclude files under sibling directory `b/`.
- `stale_manual` must only flag `status == "active" and provenance == "manual"` — exclude
  `proposed`, `promoted`, `imported`, and `deprecated`, or maintained/generated edges get
  incorrectly flagged. Support is matched on **endpoints only**: an inferred edge between
  the same two endpoints backs a manual edge even when the relationship type differs.
- Apply must not depend on `SchemaTreeService` defaults. `enable`/`append` seed placeholder
  values (an `example-value` relationship), so promotion issues one
  `set graph.relationships` with the complete list rebuilt from the manifest on disk.
- `graph.relationships` are written under the `from:` serialization alias with explicit
  `status`/`provenance` (`graph_models.graph_relationships_payload()`). YAML dumps that skip
  `by_alias=True` emit `from_endpoint:`, which fails the published JSON schema.
- Per-project `map_dependencies` calls each re-scan every workspace repo, so walk stats must
  be merged by repo path (`repo_walk.sum_scan_stats`) rather than accumulated.
- `ConfigExampleGenerator` must emit a valid member for `Literal`-typed fields (not a
  placeholder string) so the generated exemplar still validates against `MetagitConfig`.
