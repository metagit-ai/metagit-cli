---
name: workspace
description: "Skill for the Workspace area of metagit-cli. 89 symbols across 23 files."
---

# Workspace

89 symbols | 23 files | Cohesion: 85%

## When to Use

- Working with code in `src/`
- Understanding how test_rename_repo_moves_mount, rename_project, rename_repo work
- Modifying workspace-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/workspace/catalog_service.py` | _repo_ensure_conflict, add_repo, build_repo_from_fields, remove_project, remove_repo (+9) |
| `tests/core/workspace/test_catalog_service.py` | _write_manifest, test_add_and_remove_repo, test_add_repo_rejects_duplicate_identity, test_add_repo_ensure_noop_when_matching, test_add_repo_ensure_conflict_on_url_mismatch (+3) |
| `src/metagit/core/workspace/layout_service.py` | rename_project, rename_repo, move_repo, _git_warnings, _save (+2) |
| `tests/core/workspace/test_layout_resolver.py` | _config_with_projects, test_resolve_active_project_prefers_explicit, test_resolve_active_project_uses_preference_when_present, test_resolve_active_project_falls_back_to_single_project, test_resolve_active_project_unresolved_when_multiple_without_preference (+2) |
| `src/metagit/core/workspace/layout_executor.py` | apply_plan, _apply_step, _apply_rename_or_move, _apply_unlink, _apply_symlink (+2) |
| `src/metagit/core/workspace/layout_resolver.py` | list_project_names, resolve_active_project_name, active_project_resolution_error, require_active_project_name, project_exists_in_manifest (+1) |
| `tests/core/workspace/test_layout_service.py` | test_rename_repo_moves_mount, _setup_workspace, test_rename_project_moves_sync_folder, test_move_repo_between_projects, test_dry_run_does_not_mutate |
| `src/metagit/core/workspace/workspace_dedupe.py` | build_repo_identity, find_duplicate_identities, list_canonical_references, _branch_suffix, _slugify |
| `tests/core/workspace/test_workspace_project_protected.py` | _protected_config, test_remove_protected_project_requires_force, test_add_repo_to_protected_project_requires_force |
| `tests/core/workspace/test_project_tag_inheritance.py` | _config_with_project_tags, test_index_merges_project_and_repo_tags, test_search_tag_filter_matches_inherited_project_tag |

## Entry Points

Start here when exploring this area:

- **`test_rename_repo_moves_mount`** (Function) — `tests/core/workspace/test_layout_service.py:57`
- **`rename_project`** (Function) — `src/metagit/core/workspace/layout_service.py:38`
- **`rename_repo`** (Function) — `src/metagit/core/workspace/layout_service.py:196`
- **`move_repo`** (Function) — `src/metagit/core/workspace/layout_service.py:396`
- **`add`** (Function) — `src/metagit/core/project/manager.py:85`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_rename_repo_moves_mount` | Function | `tests/core/workspace/test_layout_service.py` | 57 |
| `rename_project` | Function | `src/metagit/core/workspace/layout_service.py` | 38 |
| `rename_repo` | Function | `src/metagit/core/workspace/layout_service.py` | 196 |
| `move_repo` | Function | `src/metagit/core/workspace/layout_service.py` | 396 |
| `add` | Function | `src/metagit/core/project/manager.py` | 85 |
| `save_config` | Function | `src/metagit/core/config/manager.py` | 137 |
| `config_set` | Function | `src/metagit/cli/commands/config.py` | 337 |
| `set_nested_attr` | Function | `src/metagit/cli/commands/config.py` | 349 |
| `test_add_and_remove_repo` | Function | `tests/core/workspace/test_catalog_service.py` | 59 |
| `test_add_repo_rejects_duplicate_identity` | Function | `tests/core/workspace/test_catalog_service.py` | 93 |
| `test_add_repo_ensure_noop_when_matching` | Function | `tests/core/workspace/test_catalog_service.py` | 129 |
| `test_add_repo_ensure_conflict_on_url_mismatch` | Function | `tests/core/workspace/test_catalog_service.py` | 161 |
| `add_repo` | Function | `src/metagit/core/workspace/catalog_service.py` | 326 |
| `build_repo_from_fields` | Function | `src/metagit/core/workspace/catalog_service.py` | 499 |
| `workspace_repo_add` | Function | `src/metagit/cli/commands/workspace.py` | 361 |
| `test_remove_protected_project_requires_force` | Function | `tests/core/workspace/test_workspace_project_protected.py` | 26 |
| `test_add_repo_to_protected_project_requires_force` | Function | `tests/core/workspace/test_workspace_project_protected.py` | 36 |
| `remove_project` | Function | `src/metagit/core/workspace/catalog_service.py` | 262 |
| `remove_repo` | Function | `src/metagit/core/workspace/catalog_service.py` | 432 |
| `test_list_projects_and_repos` | Function | `tests/core/workspace/test_catalog_service.py` | 25 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Repo_add → _find_project` | cross_community | 3 |
| `Repo_add → _mutation_error` | cross_community | 3 |
| `Workspace_repo_add → _find_project` | cross_community | 3 |
| `Workspace_repo_add → _mutation_error` | cross_community | 3 |
| `Workspace_list → _workspace_summary` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Config | 7 calls |
| Services | 3 calls |
| Cli | 3 calls |
| Commands | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_rename_repo_moves_mount"})` — see callers and callees
2. `gitnexus_query({query: "workspace"})` — find related execution flows
3. Read key files listed above for implementation details
