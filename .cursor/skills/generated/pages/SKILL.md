---
name: pages
description: "Skill for the Pages area of metagit-cli. 17 symbols across 8 files."
metadata:
  internal: true
---
# Pages

17 symbols | 8 files | Cohesion: 75%

## When to Use

- Working with code in `web/`
- Understanding how fetchWorkspace, fetchConfigTree, fetchConfigPreview work
- Modifying pages-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/api/client.ts` | ApiError, requestJson, getMetagitConfigTree, getAppconfigTree, postConfigPreview (+2) |
| `web/src/pages/ConfigPage.tsx` | findNodeByPath, mergePendingOp, ConfigPage |
| `web/src/pages/configQueries.ts` | fetchConfigTree, fetchConfigPreview |
| `web/src/pages/workspaceQueries.ts` | fetchWorkspace |
| `web/src/components/ConfigPreview.tsx` | ConfigPreview |
| `web/src/pages/graphQueries.ts` | fetchWorkspaceGraph |
| `web/src/pages/WorkspacePage.tsx` | WorkspacePage |
| `src/metagit/data/web/assets/index-DOullneW.js` | refetch |

## Entry Points

Start here when exploring this area:

- **`fetchWorkspace`** (Function) — `web/src/pages/workspaceQueries.ts:4`
- **`fetchConfigTree`** (Function) — `web/src/pages/configQueries.ts:17`
- **`fetchConfigPreview`** (Function) — `web/src/pages/configQueries.ts:31`
- **`ConfigPage`** (Function) — `web/src/pages/ConfigPage.tsx:51`
- **`requestJson`** (Function) — `web/src/api/client.ts:75`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ApiError` | Class | `web/src/api/client.ts` | 63 |
| `fetchWorkspace` | Function | `web/src/pages/workspaceQueries.ts` | 4 |
| `fetchConfigTree` | Function | `web/src/pages/configQueries.ts` | 17 |
| `fetchConfigPreview` | Function | `web/src/pages/configQueries.ts` | 31 |
| `ConfigPage` | Function | `web/src/pages/ConfigPage.tsx` | 51 |
| `requestJson` | Function | `web/src/api/client.ts` | 75 |
| `getMetagitConfigTree` | Function | `web/src/api/client.ts` | 108 |
| `getAppconfigTree` | Function | `web/src/api/client.ts` | 112 |
| `postConfigPreview` | Function | `web/src/api/client.ts` | 136 |
| `getWorkspace` | Function | `web/src/api/client.ts` | 213 |
| `ConfigPreview` | Function | `web/src/components/ConfigPreview.tsx` | 11 |
| `fetchWorkspaceGraph` | Function | `web/src/pages/graphQueries.ts` | 5 |
| `WorkspacePage` | Function | `web/src/pages/WorkspacePage.tsx` | 21 |
| `getWorkspaceGraph` | Function | `web/src/api/client.ts` | 243 |
| `findNodeByPath` | Function | `web/src/pages/ConfigPage.tsx` | 18 |
| `mergePendingOp` | Function | `web/src/pages/ConfigPage.tsx` | 37 |
| `refetch` | Method | `src/metagit/data/web/assets/index-DOullneW.js` | 8 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `FieldEditor → ApiError` | cross_community | 5 |
| `ConfigPage → ApiError` | intra_community | 5 |
| `WorkspacePage → ApiError` | cross_community | 5 |
| `OpsPanel → ApiError` | cross_community | 5 |
| `SyncDialog → ApiError` | cross_community | 5 |
| `SchemaTree → ApiError` | cross_community | 5 |
| `FetchWorkspace → ApiError` | intra_community | 4 |

## How to Explore

1. `gitnexus_context({name: "fetchWorkspace"})` — see callers and callees
2. `gitnexus_query({query: "pages"})` — find related execution flows
3. Read key files listed above for implementation details
