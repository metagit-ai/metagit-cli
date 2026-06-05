---
name: services
description: "Skill for the Services area of metagit-cli. 166 symbols across 36 files."
metadata:
  internal: true
---
# Services

166 symbols | 36 files | Cohesion: 81%

## When to Use

- Working with code in `src/`
- Understanding how test_workspace_search_returns_scoped_hits, test_workspace_search_terraform_preset_fallback_without_rg, test_workspace_search_includes_context_when_rg_available work
- Modifying services-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/mcp/services/workspace_search.py` | search, _compose_query, _search_with_rg, _search_fallback, _terms (+11) |
| `src/metagit/core/mcp/services/session_store.py` | get_workspace_meta, set_active_project, touch_session, get_last_session_at, _read_json (+9) |
| `src/metagit/core/mcp/services/cross_project_dependencies.py` | _collect_edges, _declared_edges, _shared_config_edges, _import_edges, _ref_target (+8) |
| `tests/core/mcp/services/test_workspace_search.py` | test_workspace_search_returns_scoped_hits, test_workspace_search_terraform_preset_fallback_without_rg, test_workspace_search_includes_context_when_rg_available, test_workspace_search_excludes_node_modules_without_rg, test_workspace_search_excludes_venv_without_rg (+6) |
| `src/metagit/core/mcp/services/project_context.py` | _build_repo_context, switch, show, _build_bundle, list_env_export_keys (+4) |
| `src/metagit/core/mcp/services/workspace_template.py` | apply, list_templates, _templates_root, _resolve_template_dir, _project_target_root (+2) |
| `tests/core/mcp/services/test_project_context.py` | _write_multi_project_workspace, _load_config, test_switch_sets_active_project_and_returns_repos, test_switch_unknown_project_returns_error, test_env_export_includes_metagit_and_config_variables (+2) |
| `tests/core/mcp/services/test_session_store.py` | test_get_workspace_meta_returns_defaults_when_missing, test_set_active_project_persists_workspace_meta, test_save_workspace_meta_writes_json, test_project_session_roundtrip, test_corrupt_project_session_returns_empty (+1) |
| `src/metagit/core/mcp/services/repo_git_stats.py` | inspect_repo_state, _ahead_behind, head_commit_age_days, merge_base_age_days, _resolve_origin_default (+1) |
| `src/metagit/core/mcp/services/workspace_snapshot.py` | restore, _load_snapshot, _restore_session_file, create, _snapshot_repo_row (+1) |

## Entry Points

Start here when exploring this area:

- **`test_workspace_search_returns_scoped_hits`** (Function) — `tests/core/mcp/services/test_workspace_search.py:11`
- **`test_workspace_search_terraform_preset_fallback_without_rg`** (Function) — `tests/core/mcp/services/test_workspace_search.py:60`
- **`test_workspace_search_includes_context_when_rg_available`** (Function) — `tests/core/mcp/services/test_workspace_search.py:78`
- **`test_workspace_search_excludes_node_modules_without_rg`** (Function) — `tests/core/mcp/services/test_workspace_search.py:134`
- **`test_workspace_search_excludes_venv_without_rg`** (Function) — `tests/core/mcp/services/test_workspace_search.py:157`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_workspace_search_returns_scoped_hits` | Function | `tests/core/mcp/services/test_workspace_search.py` | 11 |
| `test_workspace_search_terraform_preset_fallback_without_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 60 |
| `test_workspace_search_includes_context_when_rg_available` | Function | `tests/core/mcp/services/test_workspace_search.py` | 78 |
| `test_workspace_search_excludes_node_modules_without_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 134 |
| `test_workspace_search_excludes_venv_without_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 157 |
| `test_workspace_search_excludes_node_modules_with_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 179 |
| `workspace_grep_search` | Function | `src/metagit/cli/commands/workspace.py` | 607 |
| `is_git_repository` | Function | `src/metagit/core/utils/common.py` | 330 |
| `merge_project_repo_tags` | Function | `src/metagit/core/workspace/protection.py` | 19 |
| `test_workspace_index_resolves_repo_paths` | Function | `tests/core/mcp/services/test_workspace_index.py` | 11 |
| `test_filter_repo_paths_supports_project_repo_selector` | Function | `tests/core/mcp/services/test_workspace_search.py` | 39 |
| `test_build_index_synced_git_repo_with_tags_and_paths` | Function | `tests/test_workspace_index_service.py` | 11 |
| `test_build_index_url_only_repo_uses_project_mount_path` | Function | `tests/test_workspace_index_service.py` | 54 |
| `test_build_index_missing_path_is_configured_missing` | Function | `tests/test_workspace_index_service.py` | 90 |
| `utc_now_iso` | Function | `src/metagit/core/workspace/context_models.py` | 23 |
| `test_get_workspace_meta_returns_defaults_when_missing` | Function | `tests/core/mcp/services/test_session_store.py` | 14 |
| `test_set_active_project_persists_workspace_meta` | Function | `tests/core/mcp/services/test_session_store.py` | 20 |
| `inspect_repo_state` | Function | `src/metagit/core/mcp/services/repo_git_stats.py` | 12 |
| `head_commit_age_days` | Function | `src/metagit/core/mcp/services/repo_git_stats.py` | 71 |
| `merge_base_age_days` | Function | `src/metagit/core/mcp/services/repo_git_stats.py` | 86 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Show → _resolve_origin_default` | cross_community | 6 |
| `Workspace_grep_search → _path_has_scaffold_segment` | cross_community | 5 |
| `Pack_cmd → _read_json` | cross_community | 5 |
| `Show → _ahead_behind` | cross_community | 5 |
| `Show → _uncommitted_count` | cross_community | 5 |
| `Show → Head_commit_age_days` | cross_community | 5 |
| `Workspace_grep_search → _terms` | cross_community | 4 |
| `Pack_cmd → _repo_digest_row` | cross_community | 4 |
| `Pack_cmd → _parse_since_iso` | cross_community | 4 |
| `Pack_cmd → _manifest_mtime_utc` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Config | 3 calls |
| Workspace | 3 calls |
| Commands | 3 calls |
| Context | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_workspace_search_returns_scoped_hits"})` — see callers and callees
2. `gitnexus_query({query: "services"})` — find related execution flows
3. Read key files listed above for implementation details
