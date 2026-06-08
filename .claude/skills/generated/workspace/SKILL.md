---
name: workspace
description: "Skill for the Workspace area of metagit-cli. 98 symbols across 24 files."
metadata:
  internal: true
---
# Workspace

98 symbols | 24 files | Cohesion: 78%

## When to Use

- Working with code in `src/`
- Understanding how apply_plan, validate_layout_name, sync_root_path work
- Modifying workspace-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/workspace/catalog_service.py` | _project_ensure_conflict, add_project, remove_project, remove_repo, _find_project (+9) |
| `src/metagit/core/workspace/layout_resolver.py` | validate_layout_name, sync_root_path, project_dir, repo_mount_path, find_project (+6) |
| `tests/core/workspace/test_catalog_service.py` | test_add_and_remove_project, test_add_project_ensure_noop, _write_manifest, test_add_and_remove_repo, test_add_repo_rejects_duplicate_identity (+3) |
| `src/metagit/core/workspace/layout_executor.py` | apply_plan, _apply_step, _apply_rename_or_move, _apply_unlink, _apply_symlink (+2) |
| `src/metagit/core/workspace/layout_service.py` | rename_project, rename_repo, move_repo, _git_warnings, _save (+2) |
| `tests/core/workspace/test_layout_resolver.py` | _config_with_projects, test_resolve_active_project_prefers_explicit, test_resolve_active_project_uses_preference_when_present, test_resolve_active_project_falls_back_to_single_project, test_resolve_active_project_unresolved_when_multiple_without_preference (+2) |
| `src/metagit/core/workspace/workspace_dedupe.py` | build_repo_identity, find_duplicate_identities, list_canonical_references, _branch_suffix, _slugify |
| `tests/core/workspace/test_layout_service.py` | _setup_workspace, test_rename_project_moves_sync_folder, test_rename_repo_moves_mount, test_move_repo_between_projects, test_dry_run_does_not_mutate |
| `tests/core/workspace/test_workspace_project_protected.py` | _protected_config, test_remove_protected_project_requires_force, test_add_repo_to_protected_project_requires_force |
| `src/metagit/core/project/manager.py` | _create_vscode_workspace, sync, hydrate_project |

## Entry Points

Start here when exploring this area:

- **`apply_plan`** (Function) — `src/metagit/core/workspace/layout_executor.py:15`
- **`validate_layout_name`** (Function) — `src/metagit/core/workspace/layout_resolver.py:20`
- **`sync_root_path`** (Function) — `src/metagit/core/workspace/layout_resolver.py:32`
- **`project_dir`** (Function) — `src/metagit/core/workspace/layout_resolver.py:37`
- **`repo_mount_path`** (Function) — `src/metagit/core/workspace/layout_resolver.py:42`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `apply_plan` | Function | `src/metagit/core/workspace/layout_executor.py` | 15 |
| `validate_layout_name` | Function | `src/metagit/core/workspace/layout_resolver.py` | 20 |
| `sync_root_path` | Function | `src/metagit/core/workspace/layout_resolver.py` | 32 |
| `project_dir` | Function | `src/metagit/core/workspace/layout_resolver.py` | 37 |
| `repo_mount_path` | Function | `src/metagit/core/workspace/layout_resolver.py` | 42 |
| `find_project` | Function | `src/metagit/core/workspace/layout_resolver.py` | 124 |
| `find_repo` | Function | `src/metagit/core/workspace/layout_resolver.py` | 137 |
| `dedupe_enabled` | Function | `src/metagit/core/workspace/layout_resolver.py` | 148 |
| `project_is_protected` | Function | `src/metagit/core/workspace/protection.py` | 9 |
| `repo_is_protected` | Function | `src/metagit/core/workspace/protection.py` | 14 |
| `test_add_and_remove_project` | Function | `tests/core/workspace/test_catalog_service.py` | 46 |
| `test_add_project_ensure_noop` | Function | `tests/core/workspace/test_catalog_service.py` | 194 |
| `test_remove_protected_project_requires_force` | Function | `tests/core/workspace/test_workspace_project_protected.py` | 26 |
| `test_add_repo_to_protected_project_requires_force` | Function | `tests/core/workspace/test_workspace_project_protected.py` | 36 |
| `workspace_repo_add` | Function | `src/metagit/cli/commands/workspace.py` | 361 |
| `test_add_and_remove_repo` | Function | `tests/core/workspace/test_catalog_service.py` | 59 |
| `test_add_repo_rejects_duplicate_identity` | Function | `tests/core/workspace/test_catalog_service.py` | 93 |
| `test_add_repo_ensure_noop_when_matching` | Function | `tests/core/workspace/test_catalog_service.py` | 129 |
| `test_add_repo_ensure_conflict_on_url_mismatch` | Function | `tests/core/workspace/test_catalog_service.py` | 161 |
| `create_vscode_workspace` | Function | `src/metagit/core/utils/common.py` | 34 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Promote → Collect_file_copy_jobs` | cross_community | 5 |
| `Project_sync → Collect_file_copy_jobs` | cross_community | 5 |
| `Promote → Create_vscode_workspace` | cross_community | 4 |
| `Project_sync → Create_vscode_workspace` | cross_community | 4 |
| `Workspace_project_rename → Find_project` | cross_community | 4 |
| `Workspace_repo_rename → Find_project` | cross_community | 4 |
| `Workspace_repo_move → Find_project` | cross_community | 4 |
| `Show → Validate_env_value` | cross_community | 4 |
| `Repo_add → _find_project` | cross_community | 3 |
| `Repo_add → _mutation_error` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 9 calls |
| Config | 7 calls |
| Services | 4 calls |
| Providers | 1 calls |
| Web | 1 calls |

## How to Explore

1. `gitnexus_context({name: "apply_plan"})` — see callers and callees
2. `gitnexus_query({query: "workspace"})` — find related execution flows
3. Read key files listed above for implementation details
