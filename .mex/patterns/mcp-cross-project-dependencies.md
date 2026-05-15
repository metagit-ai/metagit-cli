---
name: mcp-cross-project-dependencies
description: Map or extend MCP cross-project dependency graph tooling.
triggers:
  - "cross project dependencies"
  - "metagit_cross_project_dependencies"
edges:
  - target: context/mcp-runtime.md
    condition: when changing runtime schemas or services
  - target: patterns/mcp-project-context.md
    condition: when combining with project context switch workflows
last_updated: 2026-05-15
---

# MCP Cross-Project Dependencies

## Context
Load `context/mcp-runtime.md`. Core logic: `cross_project_dependencies.py`, `import_hint_scanner.py`, `gitnexus_registry.py`.

## Layers
1. **declared/ref** — `.metagit.yml` tags, `ProjectPath.ref`, root `dependencies` / `components`
2. **shared_config/url_match** — identical URLs or `configured_path` across projects
3. **imports** — `package.json`, `pyproject.toml`, `go.mod`, terraform module paths between local repos
4. **GitNexus status** — `~/.gitnexus/registry.json` + optional `npx gitnexus status` per repo (not full graph export)

## Steps
1. Extend collectors in `CrossProjectDependencyService._collect_edges`.
2. Add MCP schema + dispatch in `runtime.py` and `tool_registry.py`.
3. Mock `GitNexusRegistryAdapter` in unit tests to avoid slow `npx` calls.
4. Update `metagit-repo-impact` skill when agent workflow changes.

## Verify
- [ ] `uv run pytest tests/core/mcp/services/test_cross_project_dependencies.py -q`
- [ ] `docs/cli_reference.md` documents tool parameters
