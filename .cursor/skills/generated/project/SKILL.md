---
name: project
description: "Skill for the Project area of metagit-cli. 38 symbols across 8 files."
metadata:
  internal: true
---
# Project

38 symbols | 8 files | Cohesion: 88%

## When to Use

- Working with code in `src/`
- Understanding how test_plan_additive_adds_missing_repo, test_plan_reconcile_removes_unmatched_provider_managed_repo, test_apply_plan_reconcile_preserves_protected_repo work
- Modifying project-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/project/manager.py` | select_repo, _append_preview_lines, _build_preview_sections, _build_project_repo_summary, sync (+8) |
| `src/metagit/core/project/source_sync.py` | plan, apply_plan, _to_project_path, _needs_update, _normalized_url (+4) |
| `src/metagit/core/project/search_service.py` | search, _to_match, _row_passes_filters, _sort_matches, _match_row |
| `tests/test_project_source_sync.py` | _service, test_plan_additive_adds_missing_repo, test_plan_reconcile_removes_unmatched_provider_managed_repo, test_apply_plan_reconcile_preserves_protected_repo |
| `tests/test_project_manager_select_repo.py` | _build_metagit_config, test_select_repo_respects_gitignore_and_sets_total_count, test_select_repo_preview_contains_extended_metadata |
| `tests/test_project_manager_dedupe.py` | test_deduped_local_path_creates_single_canonical_and_two_mounts, test_deduped_remote_clone_is_shared |
| `tests/core/workspace/test_hydrate.py` | test_project_sync_hydrate_after_deduped_symlink |
| `src/metagit/cli/commands/project.py` | project_sync |

## Entry Points

Start here when exploring this area:

- **`test_plan_additive_adds_missing_repo`** (Function) — `tests/test_project_source_sync.py:25`
- **`test_plan_reconcile_removes_unmatched_provider_managed_repo`** (Function) — `tests/test_project_source_sync.py:44`
- **`test_apply_plan_reconcile_preserves_protected_repo`** (Function) — `tests/test_project_source_sync.py:74`
- **`plan`** (Function) — `src/metagit/core/project/source_sync.py:42`
- **`apply_plan`** (Function) — `src/metagit/core/project/source_sync.py:87`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_plan_additive_adds_missing_repo` | Function | `tests/test_project_source_sync.py` | 25 |
| `test_plan_reconcile_removes_unmatched_provider_managed_repo` | Function | `tests/test_project_source_sync.py` | 44 |
| `test_apply_plan_reconcile_preserves_protected_repo` | Function | `tests/test_project_source_sync.py` | 74 |
| `plan` | Function | `src/metagit/core/project/source_sync.py` | 42 |
| `apply_plan` | Function | `src/metagit/core/project/source_sync.py` | 87 |
| `test_select_repo_respects_gitignore_and_sets_total_count` | Function | `tests/test_project_manager_select_repo.py` | 56 |
| `test_select_repo_preview_contains_extended_metadata` | Function | `tests/test_project_manager_select_repo.py` | 86 |
| `select_repo` | Function | `src/metagit/core/project/manager.py` | 582 |
| `test_deduped_local_path_creates_single_canonical_and_two_mounts` | Function | `tests/test_project_manager_dedupe.py` | 24 |
| `test_deduped_remote_clone_is_shared` | Function | `tests/test_project_manager_dedupe.py` | 64 |
| `test_project_sync_hydrate_after_deduped_symlink` | Function | `tests/core/workspace/test_hydrate.py` | 51 |
| `sync` | Function | `src/metagit/core/project/manager.py` | 182 |
| `hydrate_project` | Function | `src/metagit/core/project/manager.py` | 234 |
| `project_sync` | Function | `src/metagit/cli/commands/project.py` | 260 |
| `search` | Function | `src/metagit/core/project/search_service.py` | 24 |
| `discover` | Function | `src/metagit/core/project/source_sync.py` | 32 |
| `_service` | Function | `tests/test_project_source_sync.py` | 18 |
| `_to_project_path` | Function | `src/metagit/core/project/source_sync.py` | 240 |
| `_needs_update` | Function | `src/metagit/core/project/source_sync.py` | 252 |
| `_normalized_url` | Function | `src/metagit/core/project/source_sync.py` | 262 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Source_sync → _include_candidate` | cross_community | 4 |
| `Search → _row_passes_filters` | cross_community | 4 |
| `Search → _match_row` | cross_community | 4 |
| `Search → _to_match` | cross_community | 4 |
| `Search → _sort_matches` | cross_community | 4 |
| `Source_sync → _to_project_path` | cross_community | 3 |
| `Source_sync → _normalized_url` | cross_community | 3 |
| `Source_sync → _needs_update` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Examples | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_plan_additive_adds_missing_repo"})` — see callers and callees
2. `gitnexus_query({query: "project"})` — find related execution flows
3. Read key files listed above for implementation details
