---
name: project
description: "Skill for the Project area of metagit-cli. 29 symbols across 5 files."
metadata:
  internal: true
---
# Project

29 symbols | 5 files | Cohesion: 71%

## When to Use

- Working with code in `src/`
- Understanding how test_plan_additive_adds_missing_repo, test_plan_reconcile_removes_unmatched_provider_managed_repo, test_apply_plan_reconcile_preserves_protected_repo work
- Modifying project-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/project/manager.py` | _sync_repo, _sync_repo_deduped, _sync_local_canonical, _sync_remote_canonical, _sync_local (+5) |
| `src/metagit/core/project/source_sync.py` | plan, apply_plan, _to_project_path, _needs_update, _normalized_url (+4) |
| `src/metagit/core/project/search_service.py` | search, _to_match, _row_passes_filters, _sort_matches, _match_row |
| `tests/test_project_source_sync.py` | _service, test_plan_additive_adds_missing_repo, test_plan_reconcile_removes_unmatched_provider_managed_repo, test_apply_plan_reconcile_preserves_protected_repo |
| `src/metagit/cli/commands/project_source.py` | source_sync |

## Entry Points

Start here when exploring this area:

- **`test_plan_additive_adds_missing_repo`** (Function) — `tests/test_project_source_sync.py:25`
- **`test_plan_reconcile_removes_unmatched_provider_managed_repo`** (Function) — `tests/test_project_source_sync.py:44`
- **`test_apply_plan_reconcile_preserves_protected_repo`** (Function) — `tests/test_project_source_sync.py:74`
- **`source_sync`** (Function) — `src/metagit/cli/commands/project_source.py:77`
- **`plan`** (Method) — `src/metagit/core/project/source_sync.py:43`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_plan_additive_adds_missing_repo` | Function | `tests/test_project_source_sync.py` | 25 |
| `test_plan_reconcile_removes_unmatched_provider_managed_repo` | Function | `tests/test_project_source_sync.py` | 44 |
| `test_apply_plan_reconcile_preserves_protected_repo` | Function | `tests/test_project_source_sync.py` | 74 |
| `source_sync` | Function | `src/metagit/cli/commands/project_source.py` | 77 |
| `plan` | Method | `src/metagit/core/project/source_sync.py` | 43 |
| `apply_plan` | Method | `src/metagit/core/project/source_sync.py` | 90 |
| `discover` | Method | `src/metagit/core/project/source_sync.py` | 33 |
| `search` | Method | `src/metagit/core/project/search_service.py` | 24 |
| `select_repo` | Method | `src/metagit/core/project/manager.py` | 597 |
| `_service` | Function | `tests/test_project_source_sync.py` | 18 |
| `_to_project_path` | Method | `src/metagit/core/project/source_sync.py` | 248 |
| `_needs_update` | Method | `src/metagit/core/project/source_sync.py` | 260 |
| `_normalized_url` | Method | `src/metagit/core/project/source_sync.py` | 270 |
| `_sync_repo` | Method | `src/metagit/core/project/manager.py` | 322 |
| `_sync_repo_deduped` | Method | `src/metagit/core/project/manager.py` | 355 |
| `_sync_local_canonical` | Method | `src/metagit/core/project/manager.py` | 395 |
| `_sync_remote_canonical` | Method | `src/metagit/core/project/manager.py` | 432 |
| `_sync_local` | Method | `src/metagit/core/project/manager.py` | 456 |
| `_sync_remote` | Method | `src/metagit/core/project/manager.py` | 488 |
| `_discover_github` | Method | `src/metagit/core/project/source_sync.py` | 136 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Source_sync → _include_candidate` | intra_community | 4 |
| `Source_sync → Normalize_git_url` | cross_community | 4 |
| `Search → _row_passes_filters` | cross_community | 4 |
| `Search → _match_row` | cross_community | 4 |
| `Search → _to_match` | cross_community | 4 |
| `Search → _sort_matches` | cross_community | 4 |
| `Source_sync → _to_project_path` | cross_community | 3 |
| `Source_sync → _needs_update` | cross_community | 3 |
| `Repo_select → _build_preview_sections` | cross_community | 3 |
| `Repo_select → _build_project_repo_summary` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_370 | 8 calls |
| Commands | 4 calls |
| Cli | 3 calls |
| Workspace | 3 calls |
| Examples | 1 calls |
| Providers | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_plan_additive_adds_missing_repo"})` — see callers and callees
2. `gitnexus_query({query: "project"})` — find related execution flows
3. Read key files listed above for implementation details
