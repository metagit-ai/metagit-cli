# Durable Graph Relationships + Suggest UX/Safety Design

**Date:** 2026-07-28  
**Status:** Approved  
**Related:** `docs/reference/metagit-config.md` (manual graph relationships), `metagit-graph-maintain` skill, `ImportHintScanner`, `GraphRelationshipSuggestService`

## Summary

Harden workspace `graph.relationships` as a thin durable edge list, fix agent-facing CLI/docs confusion around `-c` vs `--workspace-root`, make `config graph suggest` visibly informative, and ensure all recursive suggest/import scanning never walks virtualenvs, package caches, or gitignored trees.

## Problem

1. **Flag confusion:** Docs and skills show `metagit config graph suggest -c .metagit.yml`, but `-c` is only on the `config` group (and on some leaves like `validate`). Placing `-c` after `suggest` fails (`No such option '-c'`). Agents then fall back to `--workspace-root` / appconfig and miss the manifest knob. Global `metagit -c` means **appconfig**, not `.metagit.yml`.
2. **Suggest opacity:** Default suggest dumps JSON with little scan context (roots, prune counts, apply outcome).
3. **Unsafe walks:** `ImportHintScanner._scan_terraform_modules` uses unbounded `Path.rglob("*.tf")`, which can enter `.venv`, `node_modules`, and other caches. Workspace search already has a scaffold denylist; suggest does not reuse it or `.gitignore`.
4. **Thin durable edges:** Suggest computes `confidence` / `evidence` but buries them in `metadata` on apply. Missing required `id`, endpoint existence checks, lifecycle (`status` / `provenance`), and stale-manual refresh leave graphs hard for agents to maintain.

## Goals

- Leaf `-c` / `--config-path` on `graph suggest` and `graph export`, plus docs/skills that state the flag semantics clearly.
- `--verbose` human progress/summary for suggest (compatible with `--json`).
- Shared ignore-aware walker for recursive suggest/import scans: always-on scaffold denylist **and** per-repo `.gitignore` (nested, git-style).
- Schema/validation/prompt upgrades: required `id`, endpoint validation, `status` / `provenance`, suggest `stale_manual[]` (report-only in v1).

## Non-goals

- Expanding `graph.relationships` into Atlas (RFC-0014) or semantic ownership (RFC-0010).
- Constrained relationship-type enum (follow-up; keep free-string `type` + documented vocabulary).
- Auto-deprecate / rewrite of stale edges on apply (`--mark-stale` deferred).
- Changing global `metagit -c` (appconfig) semantics.

## Decisions

| Topic | Choice |
|-------|--------|
| Normalize `-c` | **Both:** leaf `-c` on suggest/export **and** docs/skills clarification |
| `--workspace-root` | Remains scan/checkout root; default `appconfig.workspace.path` |
| Scaffold denylist | **Always** applied, even if a path is tracked / not gitignored |
| `.gitignore` | Honor each managed repo’s ignore files (nested); prune during walk |
| Stale edges (item 4) | **Report-only** in v1 (`stale_manual[]`); no auto-mutate |
| Suggest default output | Readable summary + short candidate list; `--json` for machine payload |
| Durable fields | First-class `status` + `provenance` on `GraphRelationship`. Suggest result keeps first-class `confidence` / `evidence`. On `--apply`, evidence continues in `metadata` (as today); do **not** add first-class `confidence` on durable edges in v1 |

### Durable `GraphRelationship` fields (v1)

Existing: `id`, `from`, `to`, `type`, `label`, `description`, `tags`, `metadata`.

Add:

| Field | Values / rules |
|-------|----------------|
| `id` | **Required** for validation after this change; suggest `--apply` auto-generates when missing |
| `status` | `active` (default) \| `deprecated` \| `proposed` |
| `provenance` | `manual` (default for hand-authored) \| `promoted` \| `imported` |

Suggest `--apply` sets `provenance: promoted` and `status: active` unless overridden later.

### Endpoint validation

On `metagit config validate` (and suggest apply path):

- If `from`/`to`.`project` is set, it must match a `workspace.projects[].name` (or documented local alias if already supported).
- If `repo` is set, it must match a repo name under that project.
- `path` remains unchecked against the filesystem (optional hint only).

### Scan exclusions

Any recursive file discovery used by graph suggest / `ImportHintScanner` must:

1. Prune directories whose path segments intersect a shared scaffold set (reuse/extend `WorkspaceSearchService` / `_SCAFFOLD_PATH_SEGMENTS`: at least `.venv`, `venv`, `node_modules`, `__pycache__`, and the existing search list).
2. Apply `.gitignore` rules from the managed repo root and nested ignore files via existing `metagit.core.utils.files` helpers (`parse_gitignore`, `should_ignore_path`) or an equivalent git-style matcher — **prune during walk**, do not post-filter after full `rglob`.
3. Report prune stats when `--verbose` (dirs pruned, files skipped).

Root-level manifest reads (`package.json`, `pyproject.toml`, `go.mod`, `requirements.txt` at repo root only) are unchanged and do not need a full-tree walk.

## Surfaces

| Surface | Change |
|---------|--------|
| CLI `metagit config graph suggest` | Leaf `-c`; `--verbose`; ignore-aware scan; `stale_manual` in result; human summary |
| CLI `metagit config graph export` | Leaf `-c` |
| CLI `metagit config validate` | Enforce `id`, endpoints, new field enums |
| Models `graph_models.py` | `status`, `provenance`; id validation policy |
| `ImportHintScanner` | Shared ignore-aware walk for Terraform (and future recursive scanners) |
| MCP suggest/apply tools | Pass through new result fields; document `-c` equivalence via workspace root + manifest path already in MCP |
| Docs / skills / scripts | Trailing `-c` OK; document `-c` vs `--workspace-root`; lifecycle wording in `graph-maintain` / discover prompts |
| Schema / full-example | Regenerated via existing schema generate task |

## Ship order

1. **Scan ignore + leaf `-c` + `--verbose`** (correctness and agent UX).
2. **Docs / skills / scripts** normalize flag semantics.
3. **Schema:** `id` required, endpoints, `status` / `provenance` + validate + apply defaults.
4. **Suggest `stale_manual[]`** + prompt/skill lifecycle wording.

## Testing

- CLI: `config graph suggest -c <manifest>` and `config graph export -c <manifest>` succeed (leaf option).
- Fixture repo with `node_modules/foo/bar.tf` and a gitignored `*.tf` path: neither appears in import/suggest evidence.
- Verbose suggest emits prune counts and candidate summary; `--json` still valid schema.
- Validate rejects unknown project/repo endpoints and blank `id`.
- Apply sets `provenance=promoted`, generates `id` when absent.
- Suggest result includes `stale_manual` for a hand-authored edge with no matching inference.

## Open follow-ups (explicitly deferred)

- `--mark-stale` to set `status: deprecated` on stale manual edges.
- Constrained `type` vocabulary enum + `x-*` escape.
- First-class persisted `confidence` on durable edges (today: suggest-only + metadata).
- Extract shared “repo file walker” package used by both workspace search and import scanner.
