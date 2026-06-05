---
name: components
description: "Skill for the Components area of metagit-cli. 55 symbols across 11 files."
---

# Components

55 symbols | 11 files | Cohesion: 92%

## When to Use

- Working with code in `web/`
- Understanding how postHealth, postPrunePreview, postPrune work
- Modifying components-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/components/FieldEditor.tsx` | scalarTypes, isMaskedSensitiveValue, normalizeDraftValue, FieldEditor, shouldSkipSensitiveSet (+5) |
| `web/src/lib/explorerFilter.ts` | explorerQueryHint, parseExplorerQuery, tagEntries, matchesTagFilters, matchesTextTokens (+2) |
| `web/src/components/RepoTable.tsx` | RepoTable, toggleProject, selectors, ProjectSection, matchesFilter (+2) |
| `web/src/components/WorkspaceExplorer.tsx` | formatTag, WorkspaceExplorer, toggleProject, ProjectBranch, RepoLeaf (+1) |
| `web/src/api/client.ts` | postHealth, postPrunePreview, postPrune, postSync, getSyncJob |
| `web/src/components/SyncDialog.tsx` | SyncDialog, reset, poll, timer, handleSubmit |
| `web/src/components/GraphDiagram.tsx` | edgeStroke, center, GraphDiagram, computeLayout, layout |
| `web/src/components/OpsPanel.tsx` | OpsPanel, runHealth, runPrunePreview, runPruneExecute |
| `web/src/components/SchemaTree.tsx` | isOptionalToggleable, displayType, isListItemNode, TreeNode |
| `web/src/lib/editorLinks.ts` | editorProtocolUrl |

## Entry Points

Start here when exploring this area:

- **`postHealth`** (Function) — `web/src/api/client.ts:263`
- **`postPrunePreview`** (Function) — `web/src/api/client.ts:297`
- **`postPrune`** (Function) — `web/src/api/client.ts:307`
- **`OpsPanel`** (Function) — `web/src/components/OpsPanel.tsx:17`
- **`runHealth`** (Function) — `web/src/components/OpsPanel.tsx:37`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `postHealth` | Function | `web/src/api/client.ts` | 263 |
| `postPrunePreview` | Function | `web/src/api/client.ts` | 297 |
| `postPrune` | Function | `web/src/api/client.ts` | 307 |
| `OpsPanel` | Function | `web/src/components/OpsPanel.tsx` | 17 |
| `runHealth` | Function | `web/src/components/OpsPanel.tsx` | 37 |
| `runPrunePreview` | Function | `web/src/components/OpsPanel.tsx` | 53 |
| `runPruneExecute` | Function | `web/src/components/OpsPanel.tsx` | 78 |
| `postSync` | Function | `web/src/api/client.ts` | 272 |
| `getSyncJob` | Function | `web/src/api/client.ts` | 279 |
| `SyncDialog` | Function | `web/src/components/SyncDialog.tsx` | 20 |
| `reset` | Function | `web/src/components/SyncDialog.tsx` | 34 |
| `poll` | Function | `web/src/components/SyncDialog.tsx` | 56 |
| `timer` | Function | `web/src/components/SyncDialog.tsx` | 87 |
| `handleSubmit` | Function | `web/src/components/SyncDialog.tsx` | 97 |
| `editorProtocolUrl` | Function | `web/src/lib/editorLinks.ts` | 2 |
| `explorerQueryHint` | Function | `web/src/lib/explorerFilter.ts` | 187 |
| `WorkspaceExplorer` | Function | `web/src/components/WorkspaceExplorer.tsx` | 27 |
| `toggleProject` | Function | `web/src/components/WorkspaceExplorer.tsx` | 46 |
| `filterExplorerGroups` | Function | `web/src/lib/explorerFilter.ts` | 142 |
| `groups` | Function | `web/src/components/WorkspaceExplorer.tsx` | 41 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `OpsPanel → ApiError` | cross_community | 5 |
| `SyncDialog → ApiError` | cross_community | 5 |
| `WorkspaceExplorer → FormatTag` | intra_community | 4 |
| `WorkspaceExplorer → EditorProtocolUrl` | intra_community | 4 |
| `SchemaTree → IsOptionalToggleable` | cross_community | 4 |
| `SchemaTree → IsListItemNode` | cross_community | 4 |
| `SchemaTree → DisplayType` | cross_community | 4 |
| `FieldEditor → IsMaskedSensitiveValue` | intra_community | 3 |
| `FieldEditor → ShouldSkipSensitiveSet` | cross_community | 3 |
| `FieldEditor → ParseDraftValue` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Api | 5 calls |
| Pages | 2 calls |

## How to Explore

1. `gitnexus_context({name: "postHealth"})` — see callers and callees
2. `gitnexus_query({query: "components"})` — find related execution flows
3. Read key files listed above for implementation details
