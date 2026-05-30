---
name: components
description: "Skill for the Components area of metagit-cli. 38 symbols across 9 files."
---

# Components

38 symbols | 9 files | Cohesion: 87%

## When to Use

- Working with code in `web/`
- Understanding how SyncDialog, poll, handleSubmit work
- Modifying components-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/components/FieldEditor.tsx` | revert, scalarTypes, formatValidationErrors, isMaskedSensitiveValue, normalizeDraftValue (+5) |
| `web/src/api/client.ts` | postSync, getSyncJob, postHealth, postPrunePreview, postPrune |
| `web/src/components/RepoTable.tsx` | matchesFilter, matchesSearch, RepoTable, toggleProject, ProjectSection |
| `web/src/components/OpsPanel.tsx` | OpsPanel, runHealth, runPrunePreview, runPruneExecute |
| `web/src/components/SchemaTree.tsx` | isOptionalToggleable, displayType, isListItemNode, TreeNode |
| `web/src/components/GraphDiagram.tsx` | edgeStroke, computeLayout, center, GraphDiagram |
| `web/src/components/SyncDialog.tsx` | SyncDialog, poll, handleSubmit |
| `src/metagit/data/web/assets/index-DOullneW.js` | invalidateQueries, add |
| `web/src/pages/workspaceQueries.ts` | repoSelector |

## Entry Points

Start here when exploring this area:

- **`SyncDialog`** (Function) — `web/src/components/SyncDialog.tsx:20`
- **`poll`** (Function) — `web/src/components/SyncDialog.tsx:56`
- **`handleSubmit`** (Function) — `web/src/components/SyncDialog.tsx:97`
- **`postSync`** (Function) — `web/src/api/client.ts:268`
- **`getSyncJob`** (Function) — `web/src/api/client.ts:275`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `SyncDialog` | Function | `web/src/components/SyncDialog.tsx` | 20 |
| `poll` | Function | `web/src/components/SyncDialog.tsx` | 56 |
| `handleSubmit` | Function | `web/src/components/SyncDialog.tsx` | 97 |
| `postSync` | Function | `web/src/api/client.ts` | 268 |
| `getSyncJob` | Function | `web/src/api/client.ts` | 275 |
| `revert` | Function | `web/src/components/FieldEditor.tsx` | 203 |
| `OpsPanel` | Function | `web/src/components/OpsPanel.tsx` | 17 |
| `runHealth` | Function | `web/src/components/OpsPanel.tsx` | 37 |
| `runPrunePreview` | Function | `web/src/components/OpsPanel.tsx` | 53 |
| `runPruneExecute` | Function | `web/src/components/OpsPanel.tsx` | 78 |
| `postHealth` | Function | `web/src/api/client.ts` | 259 |
| `postPrunePreview` | Function | `web/src/api/client.ts` | 293 |
| `postPrune` | Function | `web/src/api/client.ts` | 303 |
| `repoSelector` | Function | `web/src/pages/workspaceQueries.ts` | 15 |
| `RepoTable` | Function | `web/src/components/RepoTable.tsx` | 43 |
| `toggleProject` | Function | `web/src/components/RepoTable.tsx` | 75 |
| `FieldEditor` | Function | `web/src/components/FieldEditor.tsx` | 78 |
| `GraphDiagram` | Function | `web/src/components/GraphDiagram.tsx` | 89 |
| `queueSetOp` | Function | `web/src/components/FieldEditor.tsx` | 161 |
| `saveAllPending` | Function | `web/src/components/FieldEditor.tsx` | 185 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `FieldEditor → ApiError` | cross_community | 5 |
| `OpsPanel → ApiError` | cross_community | 5 |
| `SyncDialog → ApiError` | cross_community | 5 |
| `FieldEditor → IsMaskedSensitiveValue` | intra_community | 3 |
| `SyncDialog → InvalidateQueries` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Pages | 6 calls |
| Api | 1 calls |

## How to Explore

1. `gitnexus_context({name: "SyncDialog"})` — see callers and callees
2. `gitnexus_query({query: "components"})` — find related execution flows
3. Read key files listed above for implementation details
