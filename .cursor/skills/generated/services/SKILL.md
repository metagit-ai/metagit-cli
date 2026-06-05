---
name: services
description: "Skill for the Services area of metagit-cli. 143 symbols across 28 files."
metadata:
  internal: true
---
# Services

143 symbols | 28 files | Cohesion: 85%

## When to Use

- Working with code in `src/`
- Understanding how test_create_writes_snapshot_file, test_restore_missing_snapshot_returns_error, test_restore_switches_active_project work
- Modifying services-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/mcp/services/cross_project_dependencies.py` | map_dependencies, _normalize_types, _build_nodes, _filter_by_depth, _build_impact_summary (+9) |
| `src/metagit/core/mcp/services/workspace_search.py` | discover_files, _list_files_with_rg, _list_files_fallback, _categorize_files, _category_for_path (+7) |
| `src/metagit/core/mcp/services/session_store.py` | get_project_session, update_project_session, _read_json, ensure_dirs, save_project_session (+7) |
| `src/metagit/core/mcp/services/project_context.py` | switch, _build_bundle, _build_repo_context, _build_env, _resolve_suggested_cwd (+5) |
| `src/metagit/core/mcp/services/workspace_template.py` | apply, list_templates, _templates_root, _resolve_template_dir, _project_target_root (+2) |
| `tests/core/mcp/services/test_project_context.py` | _write_multi_project_workspace, _load_config, test_switch_sets_active_project_and_returns_repos, test_switch_unknown_project_returns_error, test_env_export_includes_metagit_and_config_variables (+2) |
| `src/metagit/core/mcp/services/workspace_snapshot.py` | create, restore, _snapshot_repo_row, _write_snapshot, _load_snapshot (+1) |
| `src/metagit/core/mcp/services/import_hint_scanner.py` | scan_repo, _scan_package_json, _scan_go_mod, _scan_text_paths, _scan_terraform_modules (+1) |
| `src/metagit/core/mcp/services/repo_git_stats.py` | inspect_repo_state, _ahead_behind, head_commit_age_days, merge_base_age_days, _resolve_origin_default (+1) |
| `src/metagit/core/mcp/services/gitnexus_registry.py` | load_entries, lookup_by_path, index_status, _status_via_cli, summarize_for_paths (+1) |

## Entry Points

Start here when exploring this area:

- **`test_create_writes_snapshot_file`** (Function) — `tests/core/mcp/services/test_workspace_snapshot.py:47`
- **`test_restore_missing_snapshot_returns_error`** (Function) — `tests/core/mcp/services/test_workspace_snapshot.py:65`
- **`test_restore_switches_active_project`** (Function) — `tests/core/mcp/services/test_workspace_snapshot.py:80`
- **`create`** (Function) — `src/metagit/core/mcp/services/workspace_snapshot.py:34`
- **`restore`** (Function) — `src/metagit/core/mcp/services/workspace_snapshot.py:89`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_create_writes_snapshot_file` | Function | `tests/core/mcp/services/test_workspace_snapshot.py` | 47 |
| `test_restore_missing_snapshot_returns_error` | Function | `tests/core/mcp/services/test_workspace_snapshot.py` | 65 |
| `test_restore_switches_active_project` | Function | `tests/core/mcp/services/test_workspace_snapshot.py` | 80 |
| `create` | Function | `src/metagit/core/mcp/services/workspace_snapshot.py` | 34 |
| `restore` | Function | `src/metagit/core/mcp/services/workspace_snapshot.py` | 89 |
| `test_template_apply_dry_run_lists_files` | Function | `tests/core/mcp/services/test_workspace_template.py` | 13 |
| `test_template_apply_requires_confirm_when_not_dry_run` | Function | `tests/core/mcp/services/test_workspace_template.py` | 50 |
| `apply` | Function | `src/metagit/core/mcp/services/workspace_template.py` | 22 |
| `list_templates` | Function | `src/metagit/core/mcp/services/workspace_template.py` | 122 |
| `test_map_dependencies_finds_url_match_and_imports` | Function | `tests/core/mcp/services/test_cross_project_dependencies.py` | 73 |
| `test_map_dependencies_unknown_project` | Function | `tests/core/mcp/services/test_cross_project_dependencies.py` | 97 |
| `test_map_dependencies_respects_depth` | Function | `tests/core/mcp/services/test_cross_project_dependencies.py` | 111 |
| `map_dependencies` | Function | `src/metagit/core/mcp/services/cross_project_dependencies.py` | 47 |
| `test_health_check_reports_missing_repo` | Function | `tests/core/mcp/services/test_workspace_health.py` | 52 |
| `test_health_check_stale_branch_metrics_and_recommendations` | Function | `tests/core/mcp/services/test_workspace_health.py` | 71 |
| `check` | Function | `src/metagit/core/mcp/services/workspace_health.py` | 37 |
| `test_switch_sets_active_project_and_returns_repos` | Function | `tests/core/mcp/services/test_project_context.py` | 59 |
| `test_switch_unknown_project_returns_error` | Function | `tests/core/mcp/services/test_project_context.py` | 82 |
| `test_env_export_includes_metagit_and_config_variables` | Function | `tests/core/mcp/services/test_project_context.py` | 97 |
| `test_update_session_persists_notes` | Function | `tests/core/mcp/services/test_project_context.py` | 113 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Pack_cmd → _read_json` | cross_community | 5 |
| `Pack_cmd → Ensure_dirs` | cross_community | 5 |
| `Pack_cmd → _write_json` | cross_community | 5 |
| `Show → _match_repo_target` | cross_community | 4 |
| `List_env_export_keys → _match_repo_target` | cross_community | 4 |
| `Inspect_repo_state → _resolve_origin_default` | intra_community | 3 |
| `Show → _build_repo_context` | cross_community | 3 |
| `Show → _build_env` | cross_community | 3 |
| `Show → _read_json` | cross_community | 3 |
| `Rename_project_session → _project_session_path` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 2 calls |

## How to Explore

1. `gitnexus_context({name: "test_create_writes_snapshot_file"})` — see callers and callees
2. `gitnexus_query({query: "services"})` — find related execution flows
3. Read key files listed above for implementation details
