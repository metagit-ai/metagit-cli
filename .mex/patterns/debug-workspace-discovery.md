---
name: debug-workspace-discovery
description: Diagnose missing/incorrect upstream repo discovery results in workspace index/search/hints flows.
triggers:
  - "upstream discovery"
  - "workspace search no results"
  - "hints look wrong"
edges:
  - target: context/architecture.md
    condition: when discovery issues involve config/workspace structure assumptions
  - target: context/mcp-runtime.md
    condition: when failures occur through MCP tool calls rather than direct service tests
  - target: patterns/bootstrap-metagit-config.md
    condition: when root issue is invalid or incomplete `.metagit.yml`
last_updated: 2026-05-05
---

# Debug Workspace Discovery

## Context
Discovery path spans `WorkspaceIndexService`, `WorkspaceSearchService`, and `UpstreamHintService`, usually driven by valid workspace config entries.

## Steps
1. Validate `.metagit.yml` and confirm `workspace.projects[].repos` is populated as expected.
2. Build index and inspect resolved `repo_path`, `exists`, and `sync` fields.
3. Check search inputs (`query`, `preset`, `max_results`) and whether target repo paths actually exist locally.
4. Inspect upstream hint scoring inputs (repo metadata + blocker text).
5. Run focused service tests and patch deterministic scoring/search behavior with regression tests.

## Gotchas
- Empty or invalid workspace repo definitions produce zero-index and cascade into no search/hints.
- Query term selection can be too strict or too broad depending on preset merge behavior.
- Local clone state (`exists=False`) can silently remove repos from search scope.

## Verify
- [ ] Index rows match expected repo definitions and path resolution.
- [ ] Search returns bounded hits from intended repositories/files.
- [ ] Hint ranking surfaces expected top candidates for blocker text.
- [ ] MCP tool path returns equivalent outputs when invoked via runtime.

## Debug
- If index is empty: fix config shape/path first.
- If hints rank poorly: inspect term overlap and score contributions.
- If MCP and direct service outputs differ: compare runtime dispatch argument parsing.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
