# Context reduction for large umbrellas and board-linked campaigns

**Status:** Accepted (MVP implemented)  
**Date:** 2026-09-18  
**Depends on:** Context packs, MCP layered resources, native campaigns, Azure DevOps source/CI provider  
**Related:** [RFC-0025 workspace index](2026-08-27-rfc-0025-workspace-index-design.md) · [Azure DevOps CI topology](2026-08-20-azure-devops-ci-topology-design.md)

## Problem

Agents treating a metagit umbrella as “load `.metagit.yml` then work” fail at 500+ repos:

1. Catalog JSON (`workspace list`, MCP `metagit_workspace_list`, `GET /v2/workspace`) embedded the **full** `workspace` object.
2. Tier-0 maps, repo lists, session digests, and `campaign status --json` returned **every** repo with no page.
3. `max_tokens` on context packs dropped cards/digest but **never the map**.
4. Campaigns froze selection into YAML (correct) then dumped that YAML back into agent context (incorrect).
5. Azure DevOps existed as git source + CI topology only. Campaigns could not bind Azure Boards / WIT items.

## Goals

1. **Never inject a full umbrella manifest into agent state** by default (CLI JSON, MCP tools/resources, local HTTP API).
2. **Page and truncate** maps, catalog indexes, digest rows, campaign status, and campaign expand.
3. **Search-first** agent loop for >500 repos: query → paged pack → frozen campaign on disk → paged status/expand.
4. **Board linking** for campaigns and objectives (`ExternalWorkRef`) with an Azure DevOps WIT client that creates a parent Feature plus paged child User Stories.

## Non-goals

- Replacing ripgrep with a content index (still RFC-0025).
- Live Azure Pipelines monitoring (still Phase 2 of the CI topology design).
- GitHub Issues / Jira / Linear clients in this MVP (refs are provider-agnostic; only ADO WIT is implemented).
- Changing Config Studio’s human full-tree editor.

## Decisions

| # | Decision |
|---|----------|
| D1 | `WorkspaceSummary.workspace` is omitted unless `include_workspace=true`. |
| D2 | Default map/index/repo-list page size is **80**. Campaign status/expand/board-sync page size is **40**. |
| D3 | `metagit://workspace/config?view=full` and `config show --json` in agent mode refuse above **80** repos unless `confirm=1` / `--confirm-full`. |
| D4 | Campaign YAML may freeze 2000 matches on disk. Agent JSON returns **counts + a page**, never the overlay. |
| D5 | Work items are pointers (`provider`, `id`, `url`, `organization`, `project`, `kind`). Tokens stay in AppConfig / env. |
| D6 | `campaign board-sync` is paged and idempotent: skip rows that already have `work_item`. |

## Agent loop (500+ repos)

```text
search --limit 10
  → context pack --tier 0 --project P   (check truncated)
  → campaign new --query … --json       (counts only)
  → campaign status --limit 40 --offset N
  → campaign expand --limit 40 --offset N
  → campaign board-sync --organization ORG --ado-project PROJ --limit 40
  → context repo-card / repomix for the current repo only
```

Prompt kind: `large-workspace`.

## Follow-on

- RFC-0025 path index for grep across 500 clones.
- GitHub Issues / Jira board providers behind the same `BoardProvider` protocol.
- WIQL pull of ADO state back onto campaign rows (`board-sync --pull`).
- ADO org index analogue of GitHub `org search`.
