---
name: project
description: "Skill for the Project area of metagit-cli. 31 symbols across 5 files."
metadata:
  internal: true
---
# Project

31 symbols | 5 files | Cohesion: 79%

## When to Use

- Working with code in `src/`
- Understanding how test_plan_additive_adds_missing_repo, test_plan_reconcile_removes_unmatched_provider_managed_repo, test_apply_plan_reconcile_preserves_protected_repo work
- Modifying project-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/project/manager.py` | _sync_repo, _sync_repo_deduped, _sync_local_canonical, _sync_remote_canonical, _sync_local (+5) |
| `tests/core/project/test_repo_promote_service.py` | _write_manifest, _init_local_git_repo, _load_config, test_resolve_git_remote_url_reads_origin, test_promote_dry_run_reports_plan (+2) |
| `src/metagit/core/project/source_sync.py` | plan, apply_plan, _to_project_path, _needs_update, _normalized_url |
| `src/metagit/core/project/search_service.py` | search, _to_match, _row_passes_filters, _sort_matches, _match_row |
| `tests/test_project_source_sync.py` | _service, test_plan_additive_adds_missing_repo, test_plan_reconcile_removes_unmatched_provider_managed_repo, test_apply_plan_reconcile_preserves_protected_repo |

## Entry Points

Start here when exploring this area:

- **`test_plan_additive_adds_missing_repo`** (Function) — `tests/test_project_source_sync.py:25`
- **`test_plan_reconcile_removes_unmatched_provider_managed_repo`** (Function) — `tests/test_project_source_sync.py:44`
- **`test_apply_plan_reconcile_preserves_protected_repo`** (Function) — `tests/test_project_source_sync.py:74`
- **`test_resolve_git_remote_url_reads_origin`** (Function) — `tests/core/project/test_repo_promote_service.py:70`
- **`test_promote_dry_run_reports_plan`** (Function) — `tests/core/project/test_repo_promote_service.py:82`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_plan_additive_adds_missing_repo` | Function | `tests/test_project_source_sync.py` | 25 |
| `test_plan_reconcile_removes_unmatched_provider_managed_repo` | Function | `tests/test_project_source_sync.py` | 44 |
| `test_apply_plan_reconcile_preserves_protected_repo` | Function | `tests/test_project_source_sync.py` | 74 |
| `test_resolve_git_remote_url_reads_origin` | Function | `tests/core/project/test_repo_promote_service.py` | 70 |
| `test_promote_dry_run_reports_plan` | Function | `tests/core/project/test_repo_promote_service.py` | 82 |
| `test_promote_updates_manifest_and_clones` | Function | `tests/core/project/test_repo_promote_service.py` | 115 |
| `test_promote_rejects_non_local_entry` | Function | `tests/core/project/test_repo_promote_service.py` | 173 |
| `plan` | Method | `src/metagit/core/project/source_sync.py` | 43 |
| `apply_plan` | Method | `src/metagit/core/project/source_sync.py` | 90 |
| `search` | Method | `src/metagit/core/project/search_service.py` | 24 |
| `select_repo` | Method | `src/metagit/core/project/manager.py` | 597 |
| `_service` | Function | `tests/test_project_source_sync.py` | 18 |
| `_write_manifest` | Function | `tests/core/project/test_repo_promote_service.py` | 32 |
| `_init_local_git_repo` | Function | `tests/core/project/test_repo_promote_service.py` | 51 |
| `_load_config` | Function | `tests/core/project/test_repo_promote_service.py` | 61 |
| `_to_project_path` | Method | `src/metagit/core/project/source_sync.py` | 248 |
| `_needs_update` | Method | `src/metagit/core/project/source_sync.py` | 260 |
| `_normalized_url` | Method | `src/metagit/core/project/source_sync.py` | 270 |
| `_sync_repo` | Method | `src/metagit/core/project/manager.py` | 322 |
| `_sync_repo_deduped` | Method | `src/metagit/core/project/manager.py` | 355 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Source_sync → Normalize_git_url` | cross_community | 4 |
| `Search → _row_passes_filters` | cross_community | 4 |
| `Search → _match_row` | cross_community | 4 |
| `Search → _to_match` | cross_community | 4 |
| `Search → _sort_matches` | cross_community | 4 |
| `Source_sync → _to_project_path` | cross_community | 3 |
| `Source_sync → _needs_update` | cross_community | 3 |
| `Repo_select → _build_preview_sections` | cross_community | 3 |
| `Repo_select → _build_project_repo_summary` | cross_community | 3 |
| `Repo_select → _append_preview_lines` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Workspace | 3 calls |
| Commands | 2 calls |
| Config | 1 calls |
| Examples | 1 calls |
| Providers | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_plan_additive_adds_missing_repo"})` — see callers and callees
2. `gitnexus_query({query: "project"})` — find related execution flows
3. Read key files listed above for implementation details
