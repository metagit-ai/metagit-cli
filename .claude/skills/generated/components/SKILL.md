---
name: components
description: "Skill for the Components area of metagit-cli. 61 symbols across 11 files."
metadata:
  internal: true
---
# Components

61 symbols | 11 files | Cohesion: 92%

## When to Use

- Working with code in `web/`
- Understanding how postHealth, postPrunePreview, postPrune work
- Modifying components-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `web/src/components/FieldEditor.tsx` | scalarTypes, isMaskedSensitiveValue, normalizeDraftValue, FieldEditor, shouldSkipSensitiveSet (+5) |
| `web/src/api/client.ts` | postHealth, postPrunePreview, postPrune, getApprovals, resolveApproval (+3) |
| `web/src/components/OpsPanel.tsx` | OpsPanel, loadApprovals, runHealth, runPrunePreview, runPruneExecute (+2) |
| `web/src/lib/explorerFilter.ts` | explorerQueryHint, parseExplorerQuery, tagEntries, matchesTagFilters, matchesTextTokens (+2) |
| `web/src/components/RepoTable.tsx` | RepoTable, toggleProject, selectors, ProjectSection, matchesFilter (+2) |
| `web/src/components/WorkspaceExplorer.tsx` | formatTag, WorkspaceExplorer, toggleProject, ProjectBranch, RepoLeaf (+1) |
| `web/src/components/SyncDialog.tsx` | SyncDialog, reset, poll, timer, handleSubmit |
| `web/src/components/GraphDiagram.tsx` | edgeStroke, center, GraphDiagram, computeLayout, layout |
| `web/src/components/SchemaTree.tsx` | isOptionalToggleable, displayType, isListItemNode, TreeNode |
| `web/src/lib/editorLinks.ts` | editorProtocolUrl |

## Entry Points

Start here when exploring this area:

- **`postHealth`** (Function) — `web/src/api/client.ts:265`
- **`postPrunePreview`** (Function) — `web/src/api/client.ts:299`
- **`postPrune`** (Function) — `web/src/api/client.ts:309`
- **`getApprovals`** (Function) — `web/src/api/client.ts:356`
- **`resolveApproval`** (Function) — `web/src/api/client.ts:361`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `postHealth` | Function | `web/src/api/client.ts` | 265 |
| `postPrunePreview` | Function | `web/src/api/client.ts` | 299 |
| `postPrune` | Function | `web/src/api/client.ts` | 309 |
| `getApprovals` | Function | `web/src/api/client.ts` | 356 |
| `resolveApproval` | Function | `web/src/api/client.ts` | 361 |
| `postSourceSync` | Function | `web/src/api/client.ts` | 389 |
| `OpsPanel` | Function | `web/src/components/OpsPanel.tsx` | 21 |
| `loadApprovals` | Function | `web/src/components/OpsPanel.tsx` | 53 |
| `runHealth` | Function | `web/src/components/OpsPanel.tsx` | 70 |
| `runPrunePreview` | Function | `web/src/components/OpsPanel.tsx` | 86 |
| `runPruneExecute` | Function | `web/src/components/OpsPanel.tsx` | 111 |
| `runSourceSync` | Function | `web/src/components/OpsPanel.tsx` | 139 |
| `resolvePendingApproval` | Function | `web/src/components/OpsPanel.tsx` | 173 |
| `postSync` | Function | `web/src/api/client.ts` | 274 |
| `getSyncJob` | Function | `web/src/api/client.ts` | 281 |
| `SyncDialog` | Function | `web/src/components/SyncDialog.tsx` | 20 |
| `reset` | Function | `web/src/components/SyncDialog.tsx` | 34 |
| `poll` | Function | `web/src/components/SyncDialog.tsx` | 56 |
| `timer` | Function | `web/src/components/SyncDialog.tsx` | 87 |
| `handleSubmit` | Function | `web/src/components/SyncDialog.tsx` | 97 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `OpsPanel → ApiError` | cross_community | 6 |
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
| Api | 8 calls |
| Pages | 2 calls |

## How to Explore

1. `gitnexus_context({name: "postHealth"})` — see callers and callees
2. `gitnexus_query({query: "components"})` — find related execution flows
3. Read key files listed above for implementation details
