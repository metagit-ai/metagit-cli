---
name: context-reduction-large-workspace
description: Keep large umbrella manifests on disk; page catalog/map/campaign JSON; link campaigns to Azure Boards.
triggers:
  - "context reduction"
  - "large umbrella"
  - "500 repos"
  - "board-sync"
  - "azure devops work item"
  - "full_manifest_refused"
edges:
  - target: context/mcp-runtime.md
    condition: when changing MCP tools or layered resources that emit workspace JSON
  - target: patterns/add-mcp-tool.md
    condition: when adding campaign or catalog MCP tools
  - target: patterns/modality-feature-registry.md
    condition: when changing CLI/MCP/docs/skills parity for context_reduction or campaign_board_link
last_updated: 2026-09-18
---

# Context reduction and board-linked campaigns

## Context

Agents fail at 500+ repos if they load `.metagit.yml`, `workspace list` with `summary.workspace`, an unpaged map, or a full campaign overlay. Caps live in `metagit.core.context.reduction`. Campaign YAML may freeze 2000 matches on disk; agent JSON is counts + a page. Azure DevOps WIT is the first `BoardProvider`; refs are provider-agnostic (`ExternalWorkRef`).

## Steps

1. Catalog: `WorkspaceCatalogService.list_workspace(..., include_workspace=False)` and paged `repos_index`. Slim `list_repos` omits `agent_instructions`.
2. Map/pack: default 80 map repos; `max_tokens` drops cards → digest → map rows (cap 20) → empty repos.
3. Refuse full dumps above 80 repos unless `confirm=1` / `--confirm-full` (MCP `workspace/config`, CLI `config show --json` in agent mode).
4. Campaigns: `status`/`expand`/`board-sync` page at 40; `new --json` returns `_campaign_create_payload` (no `repos[]`).
5. Board-sync: parent Feature + paged User Stories; skip rows that already have `work_item`; `dry_run` before PAT calls.
6. Skills and prompt kind `large-workspace` teach search → scoped pack → frozen campaign → paged expand → board-sync.

## Gotchas

- `summary.workspace=config.workspace` was a silent triple dump of the umbrella. Keep it opt-in.
- `max_tokens` used to drop cards/digest and leave the map unbounded.
- `campaign status --json` used to dump the overlay. Do not add the document back to MCP/CLI JSON.
- Tokens never belong in `_campaigns/*.yml`.
- Human Config Studio may still show the full tree.

## Verify

- [ ] `workspace list --json` has `summary.workspace` null and `truncated` when over the index cap
- [ ] `metagit://workspace/config?view=full` returns `full_manifest_refused` above 80 repos
- [ ] `metagit_campaign_status` with `limit: 1` sets `truncated` and omits `selection`
- [ ] `campaign board-sync --dry-run --json` pages children and does not call ADO
- [ ] Skills under `src/metagit/data/skills/` carry `modality:context_reduction` / `campaign_board_link`
