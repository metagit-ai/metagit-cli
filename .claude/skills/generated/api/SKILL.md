---
name: api
description: "Skill for the Api area of metagit-cli. 58 symbols across 16 files."
metadata:
  internal: true
---
# Api

58 symbols | 16 files | Cohesion: 82%

## When to Use

- Working with code in `web/`
- Understanding how requestJson, patchMetagitConfig, patchAppconfig work
- Modifying api-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/api/client.ts` | ApiError, requestJson, patchMetagitConfig, patchAppconfig, postConfigPreview (+9) |
| `src/metagit/core/api/server.py` | _parse_tag_filters_from_query, _first, do_GET, do_POST, do_DELETE (+1) |
| `src/metagit/core/api/layout_handler.py` | handle, _layout_flags, _bool_param, _load_config, _respond_layout (+1) |
| `src/metagit/core/api/catalog_handler.py` | handle, _load_config, _parse_body, _respond_mutation, _first |
| `web/src/pages/agentQueries.ts` | fetchAgentCatalog, fetchAgentTemplate, fetchAgentPreview, initAgentOverlay |
| `src/metagit/core/api/grep_handler.py` | handle, _load_config, _first, _bounded_int |
| `tests/api/test_grep_api.py` | _write_grep_fixture, test_workspace_grep_requires_query, test_workspace_grep_info_returns_ripgrep_status, test_workspace_grep_returns_enriched_hits |
| `web/src/pages/configQueries.ts` | patchConfigTree, fetchConfigPreview, fetchConfigTree |
| `web/src/components/SchemaTree.tsx` | mergePendingOp, mutationFn, queryFn |
| `web/src/components/FieldEditor.tsx` | mutationFn, queryFn |

## Entry Points

Start here when exploring this area:

- **`requestJson`** (Function) — `web/src/api/client.ts:75`
- **`patchMetagitConfig`** (Function) — `web/src/api/client.ts:116`
- **`patchAppconfig`** (Function) — `web/src/api/client.ts:127`
- **`postConfigPreview`** (Function) — `web/src/api/client.ts:138`
- **`getWorkspace`** (Function) — `web/src/api/client.ts:217`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ApiError` | Class | `web/src/api/client.ts` | 63 |
| `requestJson` | Function | `web/src/api/client.ts` | 75 |
| `patchMetagitConfig` | Function | `web/src/api/client.ts` | 116 |
| `patchAppconfig` | Function | `web/src/api/client.ts` | 127 |
| `postConfigPreview` | Function | `web/src/api/client.ts` | 138 |
| `getWorkspace` | Function | `web/src/api/client.ts` | 217 |
| `postOpenPath` | Function | `web/src/api/client.ts` | 331 |
| `getWorkspaceGrepInfo` | Function | `web/src/api/client.ts` | 411 |
| `getAgentCatalog` | Function | `web/src/api/client.ts` | 479 |
| `getAgentTemplate` | Function | `web/src/api/client.ts` | 483 |
| `getAgentPreview` | Function | `web/src/api/client.ts` | 489 |
| `postAgentOverlayInit` | Function | `web/src/api/client.ts` | 519 |
| `fetchAgentCatalog` | Function | `web/src/pages/agentQueries.ts` | 15 |
| `fetchAgentTemplate` | Function | `web/src/pages/agentQueries.ts` | 23 |
| `fetchAgentPreview` | Function | `web/src/pages/agentQueries.ts` | 31 |
| `initAgentOverlay` | Function | `web/src/pages/agentQueries.ts` | 38 |
| `patchConfigTree` | Function | `web/src/pages/configQueries.ts` | 21 |
| `fetchConfigPreview` | Function | `web/src/pages/configQueries.ts` | 32 |
| `fetchWorkspaceGrepInfo` | Function | `web/src/pages/grepQueries.ts` | 35 |
| `fetchWorkspace` | Function | `web/src/pages/workspaceQueries.ts` | 4 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `QueryFn → ApiError` | cross_community | 5 |
| `OpsPanel → ApiError` | cross_community | 5 |
| `SyncDialog → ApiError` | cross_community | 5 |
| `Do_GET → Load_config` | cross_community | 4 |
| `Do_POST → Load_config` | cross_community | 4 |
| `Do_POST → _bool_param` | cross_community | 4 |
| `Do_DELETE → Load_config` | cross_community | 4 |
| `FetchAgentCatalog → ApiError` | intra_community | 4 |
| `FetchAgentTemplate → ApiError` | intra_community | 4 |
| `FetchWorkspaceGrepInfo → ApiError` | intra_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 6 calls |
| Project | 1 calls |
| Services | 1 calls |

## How to Explore

1. `gitnexus_context({name: "requestJson"})` — see callers and callees
2. `gitnexus_query({query: "api"})` — find related execution flows
3. Read key files listed above for implementation details
