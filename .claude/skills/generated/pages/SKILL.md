---
name: pages
description: "Skill for the Pages area of metagit-cli. 20 symbols across 9 files."
---

# Pages

20 symbols | 9 files | Cohesion: 75%

## When to Use

- Working with code in `web/`
- Understanding how fetchWorkspace, fetchWorkspaceGrepInfo, fetchConfigTree work
- Modifying pages-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/api/client.ts` | ApiError, requestJson, getMetagitConfigTree, getAppconfigTree, postConfigPreview (+3) |
| `web/src/pages/ConfigPage.tsx` | findNodeByPath, mergePendingOp, ConfigPage |
| `web/src/pages/grepQueries.ts` | fetchWorkspaceGrepInfo, grepQueryKey |
| `web/src/pages/configQueries.ts` | fetchConfigTree, fetchConfigPreview |
| `web/src/pages/workspaceQueries.ts` | fetchWorkspace |
| `web/src/components/ConfigPreview.tsx` | ConfigPreview |
| `web/src/pages/graphQueries.ts` | fetchWorkspaceGraph |
| `web/src/pages/WorkspacePage.tsx` | WorkspacePage |
| `src/metagit/data/web/assets/index-C6eUwfs-.js` | refetch |

## Entry Points

Start here when exploring this area:

- **`fetchWorkspace`** (Function) — `web/src/pages/workspaceQueries.ts:4`
- **`fetchWorkspaceGrepInfo`** (Function) — `web/src/pages/grepQueries.ts:35`
- **`fetchConfigTree`** (Function) — `web/src/pages/configQueries.ts:17`
- **`fetchConfigPreview`** (Function) — `web/src/pages/configQueries.ts:32`
- **`ConfigPage`** (Function) — `web/src/pages/ConfigPage.tsx:51`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ApiError` | Class | `web/src/api/client.ts` | 63 |
| `fetchWorkspace` | Function | `web/src/pages/workspaceQueries.ts` | 4 |
| `fetchWorkspaceGrepInfo` | Function | `web/src/pages/grepQueries.ts` | 35 |
| `fetchConfigTree` | Function | `web/src/pages/configQueries.ts` | 17 |
| `fetchConfigPreview` | Function | `web/src/pages/configQueries.ts` | 32 |
| `ConfigPage` | Function | `web/src/pages/ConfigPage.tsx` | 51 |
| `requestJson` | Function | `web/src/api/client.ts` | 75 |
| `getMetagitConfigTree` | Function | `web/src/api/client.ts` | 108 |
| `getAppconfigTree` | Function | `web/src/api/client.ts` | 112 |
| `postConfigPreview` | Function | `web/src/api/client.ts` | 138 |
| `getWorkspace` | Function | `web/src/api/client.ts` | 215 |
| `getWorkspaceGrepInfo` | Function | `web/src/api/client.ts` | 390 |
| `ConfigPreview` | Function | `web/src/components/ConfigPreview.tsx` | 11 |
| `grepQueryKey` | Function | `web/src/pages/grepQueries.ts` | 8 |
| `fetchWorkspaceGraph` | Function | `web/src/pages/graphQueries.ts` | 5 |
| `WorkspacePage` | Function | `web/src/pages/WorkspacePage.tsx` | 27 |
| `getWorkspaceGraph` | Function | `web/src/api/client.ts` | 245 |
| `findNodeByPath` | Function | `web/src/pages/ConfigPage.tsx` | 18 |
| `mergePendingOp` | Function | `web/src/pages/ConfigPage.tsx` | 37 |
| `refetch` | Method | `src/metagit/data/web/assets/index-C6eUwfs-.js` | 8 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `WorkspacePage → ApiError` | cross_community | 5 |
| `FieldEditor → ApiError` | cross_community | 5 |
| `ConfigPage → ApiError` | intra_community | 5 |
| `OpsPanel → ApiError` | cross_community | 5 |
| `SyncDialog → ApiError` | cross_community | 5 |
| `SchemaTree → ApiError` | cross_community | 5 |
| `WorkspacePage → Append` | cross_community | 4 |
| `FetchWorkspace → ApiError` | intra_community | 4 |
| `FetchWorkspaceGrepInfo → ApiError` | intra_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Mcp | 1 calls |

## How to Explore

1. `gitnexus_context({name: "fetchWorkspace"})` — see callers and callees
2. `gitnexus_query({query: "pages"})` — find related execution flows
3. Read key files listed above for implementation details
