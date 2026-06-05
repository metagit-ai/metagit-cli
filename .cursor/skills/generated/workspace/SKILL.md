---
name: workspace
description: "Skill for the Workspace area of metagit-cli. 69 symbols across 18 files."
metadata:
  internal: true
---
# Workspace

69 symbols | 18 files | Cohesion: 84%

## When to Use

- Working with code in `src/`
- Understanding how test_rename_repo_moves_mount, rename_project, rename_repo work
- Modifying workspace-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/workspace/catalog_service.py` | _repo_ensure_conflict, add_repo, build_repo_from_fields, list_workspace, list_projects (+9) |
| `tests/core/workspace/test_catalog_service.py` | _write_manifest, test_add_and_remove_repo, test_add_repo_rejects_duplicate_identity, test_add_repo_ensure_noop_when_matching, test_add_repo_ensure_conflict_on_url_mismatch (+3) |
| `src/metagit/core/workspace/layout_service.py` | rename_project, rename_repo, move_repo, _git_warnings, _save (+2) |
| `src/metagit/core/workspace/layout_executor.py` | apply_plan, _apply_step, _apply_rename_or_move, _apply_unlink, _apply_symlink (+2) |
| `tests/core/workspace/test_layout_service.py` | test_rename_repo_moves_mount, _setup_workspace, test_rename_project_moves_sync_folder, test_move_repo_between_projects, test_dry_run_does_not_mutate |
| `src/metagit/core/workspace/workspace_dedupe.py` | build_repo_identity, find_duplicate_identities, list_canonical_references, _branch_suffix, _slugify |
| `tests/core/workspace/test_dedupe_resolver.py` | _config_with_projects, test_resolve_effective_dedupe_for_project_by_name, test_resolve_dedupe_for_layout_without_project |
| `src/metagit/core/workspace/dedupe_resolver.py` | resolve_effective_dedupe, resolve_effective_dedupe_for_project, resolve_dedupe_for_layout |
| `src/metagit/core/workspace/context_models.py` | validate_env_key, validate_env_value, validate_env_overrides |
| `src/metagit/core/workspace/agent_instructions.py` | resolve, _normalized, _compose_text |

## Entry Points

Start here when exploring this area:

- **`test_rename_repo_moves_mount`** (Function) — `tests/core/workspace/test_layout_service.py:57`
- **`rename_project`** (Function) — `src/metagit/core/workspace/layout_service.py:37`
- **`rename_repo`** (Function) — `src/metagit/core/workspace/layout_service.py:187`
- **`move_repo`** (Function) — `src/metagit/core/workspace/layout_service.py:387`
- **`add`** (Function) — `src/metagit/core/project/manager.py:82`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_rename_repo_moves_mount` | Function | `tests/core/workspace/test_layout_service.py` | 57 |
| `rename_project` | Function | `src/metagit/core/workspace/layout_service.py` | 37 |
| `rename_repo` | Function | `src/metagit/core/workspace/layout_service.py` | 187 |
| `move_repo` | Function | `src/metagit/core/workspace/layout_service.py` | 387 |
| `add` | Function | `src/metagit/core/project/manager.py` | 82 |
| `save_config` | Function | `src/metagit/core/config/manager.py` | 137 |
| `config_set` | Function | `src/metagit/cli/commands/config.py` | 337 |
| `set_nested_attr` | Function | `src/metagit/cli/commands/config.py` | 349 |
| `test_add_and_remove_repo` | Function | `tests/core/workspace/test_catalog_service.py` | 59 |
| `test_add_repo_rejects_duplicate_identity` | Function | `tests/core/workspace/test_catalog_service.py` | 93 |
| `test_add_repo_ensure_noop_when_matching` | Function | `tests/core/workspace/test_catalog_service.py` | 129 |
| `test_add_repo_ensure_conflict_on_url_mismatch` | Function | `tests/core/workspace/test_catalog_service.py` | 161 |
| `add_repo` | Function | `src/metagit/core/workspace/catalog_service.py` | 288 |
| `build_repo_from_fields` | Function | `src/metagit/core/workspace/catalog_service.py` | 430 |
| `workspace_repo_add` | Function | `src/metagit/cli/commands/workspace.py` | 305 |
| `test_list_projects_and_repos` | Function | `tests/core/workspace/test_catalog_service.py` | 25 |
| `list_workspace` | Function | `src/metagit/core/workspace/catalog_service.py` | 76 |
| `list_projects` | Function | `src/metagit/core/workspace/catalog_service.py` | 102 |
| `list_repos` | Function | `src/metagit/core/workspace/catalog_service.py` | 126 |
| `echo` | Function | `src/metagit/core/utils/logging.py` | 593 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Repo_add → _find_project` | cross_community | 3 |
| `Repo_add → _mutation_error` | cross_community | 3 |
| `Workspace_repo_add → _find_project` | cross_community | 3 |
| `Workspace_repo_add → _mutation_error` | cross_community | 3 |
| `Remove_repo → Save_config` | cross_community | 3 |
| `Workspace_list → _workspace_summary` | intra_community | 3 |
| `Workspace_list → List_projects` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 9 calls |
| Services | 3 calls |
| Cli | 3 calls |

## How to Explore

1. `gitnexus_context({name: "test_rename_repo_moves_mount"})` — see callers and callees
2. `gitnexus_query({query: "workspace"})` — find related execution flows
3. Read key files listed above for implementation details
