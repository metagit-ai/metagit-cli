# MCP Cross-Project Dependencies — Design Spec

**Status:** Implemented  
**Date:** 2026-05-15

## Tool

`metagit_cross_project_dependencies` (active workspace gate)

## Parameters

| Field | Description |
|-------|-------------|
| `source_project` | Workspace project to analyze (required) |
| `dependency_types` | Subset of `declared`, `imports`, `shared_config`, `url_match`, `ref` |
| `depth` | Graph hop limit from source (default 2) |
| `include_external_repos` | Include edges to non-workspace targets (default false) |

## Layers

1. **declared / ref** — workspace repo tags (`depends_on`, `project`), `ProjectPath.ref`, root `dependencies` / `components`
2. **shared_config / url_match** — identical repo URLs or `configured_path` values across projects
3. **imports** — manifest scanners (`package.json`, `pyproject.toml`, `go.mod`, terraform `module` sources) resolving to sibling workspace checkouts
4. **GitNexus status** — `~/.gitnexus/registry.json` lookup + optional `npx gitnexus status` per repo (`indexed`, `stale`, `missing`)

Symbol-level import graphs are not exported by this tool; use GitNexus MCP/CLI after `gitnexus analyze`.

## Response

- `nodes` — `project` and `repo` nodes with optional `gitnexus_status`
- `edges` — typed relationships with `evidence[]`
- `graph_status` — map of repo path → GitNexus status
- `impact_summary` — `risk`, `affected_projects`, `affected_repos`, `notes`
