---
name: api
description: "Skill for the Api area of metagit-cli. 45 symbols across 12 files."
---

# Api

45 symbols | 12 files | Cohesion: 81%

## When to Use

- Working with code in `src/`
- Understanding how fetchWorkspace, fetchWorkspaceGrepInfo, fetchConfigTree work
- Modifying api-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/api/client.ts` | ApiError, requestJson, getMetagitConfigTree, getAppconfigTree, patchMetagitConfig (+4) |
| `src/metagit/core/api/server.py` | _parse_tag_filters_from_query, _first, do_GET, do_POST, do_DELETE (+1) |
| `src/metagit/core/api/layout_handler.py` | handle, _layout_flags, _bool_param, _load_config, _respond_layout (+1) |
| `src/metagit/core/api/catalog_handler.py` | handle, _load_config, _parse_body, _respond_mutation, _first |
| `tests/api/test_grep_api.py` | _write_grep_fixture, test_workspace_grep_requires_query, test_workspace_grep_info_returns_ripgrep_status, test_workspace_grep_returns_enriched_hits |
| `src/metagit/core/api/grep_handler.py` | handle, _load_config, _first, _bounded_int |
| `web/src/pages/configQueries.ts` | fetchConfigTree, patchConfigTree, fetchConfigPreview |
| `web/src/pages/ConfigPage.tsx` | findNodeByPath, mergePendingOp, ConfigPage |
| `web/src/components/SchemaTree.tsx` | mergePendingOp, SchemaTree |
| `web/src/pages/workspaceQueries.ts` | fetchWorkspace |

## Entry Points

Start here when exploring this area:

- **`fetchWorkspace`** (Function) — `web/src/pages/workspaceQueries.ts:4`
- **`fetchWorkspaceGrepInfo`** (Function) — `web/src/pages/grepQueries.ts:35`
- **`fetchConfigTree`** (Function) — `web/src/pages/configQueries.ts:17`
- **`patchConfigTree`** (Function) — `web/src/pages/configQueries.ts:21`
- **`fetchConfigPreview`** (Function) — `web/src/pages/configQueries.ts:32`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ApiError` | Class | `web/src/api/client.ts` | 63 |
| `fetchWorkspace` | Function | `web/src/pages/workspaceQueries.ts` | 4 |
| `fetchWorkspaceGrepInfo` | Function | `web/src/pages/grepQueries.ts` | 35 |
| `fetchConfigTree` | Function | `web/src/pages/configQueries.ts` | 17 |
| `patchConfigTree` | Function | `web/src/pages/configQueries.ts` | 21 |
| `fetchConfigPreview` | Function | `web/src/pages/configQueries.ts` | 32 |
| `SchemaTree` | Function | `web/src/components/SchemaTree.tsx` | 45 |
| `ConfigPreview` | Function | `web/src/components/ConfigPreview.tsx` | 11 |
| `requestJson` | Function | `web/src/api/client.ts` | 75 |
| `getMetagitConfigTree` | Function | `web/src/api/client.ts` | 108 |
| `getAppconfigTree` | Function | `web/src/api/client.ts` | 112 |
| `patchMetagitConfig` | Function | `web/src/api/client.ts` | 116 |
| `patchAppconfig` | Function | `web/src/api/client.ts` | 127 |
| `postConfigPreview` | Function | `web/src/api/client.ts` | 138 |
| `getWorkspace` | Function | `web/src/api/client.ts` | 215 |
| `getWorkspaceGrepInfo` | Function | `web/src/api/client.ts` | 390 |
| `ConfigPage` | Function | `web/src/pages/ConfigPage.tsx` | 51 |
| `do_GET` | Function | `src/metagit/core/api/server.py` | 69 |
| `do_POST` | Function | `src/metagit/core/api/server.py` | 170 |
| `do_DELETE` | Function | `src/metagit/core/api/server.py` | 183 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `WorkspacePage → ApiError` | cross_community | 5 |
| `FieldEditor → ApiError` | cross_community | 5 |
| `ConfigPage → ApiError` | intra_community | 5 |
| `SchemaTree → ApiError` | intra_community | 5 |
| `OpsPanel → ApiError` | cross_community | 5 |
| `SyncDialog → ApiError` | cross_community | 5 |
| `Do_POST → Load_config` | cross_community | 4 |
| `Do_POST → _bool_param` | cross_community | 4 |
| `Do_DELETE → Load_config` | cross_community | 4 |
| `FetchWorkspace → ApiError` | intra_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Config | 4 calls |
| Project | 1 calls |
| Commands | 1 calls |

## How to Explore

1. `gitnexus_context({name: "fetchWorkspace"})` — see callers and callees
2. `gitnexus_query({query: "api"})` — find related execution flows
3. Read key files listed above for implementation details
