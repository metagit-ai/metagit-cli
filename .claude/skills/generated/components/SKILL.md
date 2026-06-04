---
name: components
description: "Skill for the Components area of metagit-cli. 41 symbols across 8 files."
---

# Components

41 symbols | 8 files | Cohesion: 90%

## When to Use

- Working with code in `web/`
- Understanding how postHealth, postPrunePreview, postPrune work
- Modifying components-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/components/FieldEditor.tsx` | scalarTypes, isMaskedSensitiveValue, normalizeDraftValue, FieldEditor, shouldSkipSensitiveSet (+5) |
| `web/src/components/RepoTable.tsx` | RepoTable, toggleProject, selectors, ProjectSection, matchesFilter (+2) |
| `web/src/api/client.ts` | postHealth, postPrunePreview, postPrune, postSync, getSyncJob |
| `web/src/components/SyncDialog.tsx` | SyncDialog, reset, poll, timer, handleSubmit |
| `web/src/components/GraphDiagram.tsx` | edgeStroke, center, GraphDiagram, computeLayout, layout |
| `web/src/components/OpsPanel.tsx` | OpsPanel, runHealth, runPrunePreview, runPruneExecute |
| `web/src/components/SchemaTree.tsx` | isOptionalToggleable, displayType, isListItemNode, TreeNode |
| `web/src/pages/workspaceQueries.ts` | repoSelector |

## Entry Points

Start here when exploring this area:

- **`postHealth`** (Function) — `web/src/api/client.ts:261`
- **`postPrunePreview`** (Function) — `web/src/api/client.ts:295`
- **`postPrune`** (Function) — `web/src/api/client.ts:305`
- **`OpsPanel`** (Function) — `web/src/components/OpsPanel.tsx:17`
- **`runHealth`** (Function) — `web/src/components/OpsPanel.tsx:37`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `postHealth` | Function | `web/src/api/client.ts` | 261 |
| `postPrunePreview` | Function | `web/src/api/client.ts` | 295 |
| `postPrune` | Function | `web/src/api/client.ts` | 305 |
| `OpsPanel` | Function | `web/src/components/OpsPanel.tsx` | 17 |
| `runHealth` | Function | `web/src/components/OpsPanel.tsx` | 37 |
| `runPrunePreview` | Function | `web/src/components/OpsPanel.tsx` | 53 |
| `runPruneExecute` | Function | `web/src/components/OpsPanel.tsx` | 78 |
| `postSync` | Function | `web/src/api/client.ts` | 270 |
| `getSyncJob` | Function | `web/src/api/client.ts` | 277 |
| `SyncDialog` | Function | `web/src/components/SyncDialog.tsx` | 20 |
| `reset` | Function | `web/src/components/SyncDialog.tsx` | 34 |
| `poll` | Function | `web/src/components/SyncDialog.tsx` | 56 |
| `timer` | Function | `web/src/components/SyncDialog.tsx` | 87 |
| `handleSubmit` | Function | `web/src/components/SyncDialog.tsx` | 97 |
| `repoSelector` | Function | `web/src/pages/workspaceQueries.ts` | 15 |
| `RepoTable` | Function | `web/src/components/RepoTable.tsx` | 43 |
| `toggleProject` | Function | `web/src/components/RepoTable.tsx` | 75 |
| `selectors` | Function | `web/src/components/RepoTable.tsx` | 97 |
| `FieldEditor` | Function | `web/src/components/FieldEditor.tsx` | 88 |
| `queueSetOp` | Function | `web/src/components/FieldEditor.tsx` | 172 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `OpsPanel → ApiError` | cross_community | 5 |
| `SyncDialog → ApiError` | cross_community | 5 |
| `SchemaTree → IsOptionalToggleable` | cross_community | 4 |
| `SchemaTree → IsListItemNode` | cross_community | 4 |
| `SchemaTree → DisplayType` | cross_community | 4 |
| `FieldEditor → IsMaskedSensitiveValue` | intra_community | 3 |
| `FieldEditor → ShouldSkipSensitiveSet` | cross_community | 3 |
| `FieldEditor → ParseDraftValue` | cross_community | 3 |
| `SyncDialog → Reset` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Api | 5 calls |
| Pages | 2 calls |

## How to Explore

1. `gitnexus_context({name: "postHealth"})` — see callers and callees
2. `gitnexus_query({query: "components"})` — find related execution flows
3. Read key files listed above for implementation details
