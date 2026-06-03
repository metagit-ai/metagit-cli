---
name: services
description: "Skill for the Services area of metagit-cli. 160 symbols across 33 files."
---

# Services

160 symbols | 33 files | Cohesion: 86%

## When to Use

- Working with code in `src/`
- Understanding how test_restore_switches_active_project, test_get_workspace_meta_returns_defaults_when_missing, test_set_active_project_persists_workspace_meta work
- Modifying services-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/mcp/services/workspace_search.py` | _search_fallback, discover_files, _list_files_with_rg, _list_files_fallback, _categorize_files (+10) |
| `src/metagit/core/mcp/services/session_store.py` | get_workspace_meta, save_workspace_meta, set_active_project, link_snapshot, touch_session (+9) |
| `src/metagit/core/mcp/services/cross_project_dependencies.py` | map_dependencies, _normalize_types, _build_nodes, _filter_by_depth, _build_impact_summary (+9) |
| `src/metagit/core/mcp/services/project_context.py` | switch, _build_bundle, _build_repo_context, _build_env, _resolve_suggested_cwd (+5) |
| `tests/core/mcp/services/test_workspace_search.py` | test_discover_files_returns_categorized_entries, test_workspace_search_returns_scoped_hits, test_workspace_search_terraform_preset_fallback_without_rg, test_workspace_search_includes_context_when_rg_available, test_workspace_search_excludes_node_modules_without_rg (+3) |
| `src/metagit/core/mcp/services/workspace_template.py` | apply, list_templates, _templates_root, _resolve_template_dir, _project_target_root (+2) |
| `tests/core/mcp/services/test_project_context.py` | _write_multi_project_workspace, _load_config, test_switch_sets_active_project_and_returns_repos, test_switch_unknown_project_returns_error, test_env_export_includes_metagit_and_config_variables (+2) |
| `tests/core/mcp/services/test_session_store.py` | test_get_workspace_meta_returns_defaults_when_missing, test_set_active_project_persists_workspace_meta, test_save_workspace_meta_writes_json, test_project_session_roundtrip, test_corrupt_project_session_returns_empty (+1) |
| `src/metagit/core/mcp/services/workspace_snapshot.py` | create, _snapshot_repo_row, _write_snapshot, restore, _load_snapshot (+1) |
| `src/metagit/core/mcp/services/import_hint_scanner.py` | scan_repo, _scan_package_json, _scan_go_mod, _scan_text_paths, _scan_terraform_modules (+1) |

## Entry Points

Start here when exploring this area:

- **`test_restore_switches_active_project`** (Function) — `tests/core/mcp/services/test_workspace_snapshot.py:80`
- **`test_get_workspace_meta_returns_defaults_when_missing`** (Function) — `tests/core/mcp/services/test_session_store.py:14`
- **`test_set_active_project_persists_workspace_meta`** (Function) — `tests/core/mcp/services/test_session_store.py:20`
- **`test_save_workspace_meta_writes_json`** (Function) — `tests/core/mcp/services/test_session_store.py:60`
- **`pack`** (Function) — `src/metagit/core/context/context_pack_service.py:37`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_restore_switches_active_project` | Function | `tests/core/mcp/services/test_workspace_snapshot.py` | 80 |
| `test_get_workspace_meta_returns_defaults_when_missing` | Function | `tests/core/mcp/services/test_session_store.py` | 14 |
| `test_set_active_project_persists_workspace_meta` | Function | `tests/core/mcp/services/test_session_store.py` | 20 |
| `test_save_workspace_meta_writes_json` | Function | `tests/core/mcp/services/test_session_store.py` | 60 |
| `pack` | Function | `src/metagit/core/context/context_pack_service.py` | 37 |
| `create` | Function | `src/metagit/core/mcp/services/workspace_snapshot.py` | 34 |
| `get_workspace_meta` | Function | `src/metagit/core/mcp/services/session_store.py` | 43 |
| `save_workspace_meta` | Function | `src/metagit/core/mcp/services/session_store.py` | 50 |
| `set_active_project` | Function | `src/metagit/core/mcp/services/session_store.py` | 57 |
| `link_snapshot` | Function | `src/metagit/core/mcp/services/session_store.py` | 129 |
| `touch_session` | Function | `src/metagit/core/mcp/services/session_store.py` | 140 |
| `get_last_session_at` | Function | `src/metagit/core/mcp/services/session_store.py` | 147 |
| `test_discover_files_returns_categorized_entries` | Function | `tests/core/mcp/services/test_workspace_search.py` | 202 |
| `discover_files` | Function | `src/metagit/core/mcp/services/workspace_search.py` | 369 |
| `test_workspace_search_returns_scoped_hits` | Function | `tests/core/mcp/services/test_workspace_search.py` | 11 |
| `test_workspace_search_terraform_preset_fallback_without_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 60 |
| `test_workspace_search_includes_context_when_rg_available` | Function | `tests/core/mcp/services/test_workspace_search.py` | 78 |
| `test_workspace_search_excludes_node_modules_without_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 134 |
| `test_workspace_search_excludes_venv_without_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 157 |
| `test_workspace_search_excludes_node_modules_with_rg` | Function | `tests/core/mcp/services/test_workspace_search.py` | 179 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Workspace_grep_search → _path_has_scaffold_segment` | cross_community | 5 |
| `Pack_cmd → _read_json` | cross_community | 5 |
| `Pack_cmd → Ensure_dirs` | cross_community | 5 |
| `Pack_cmd → _write_json` | cross_community | 5 |
| `Workspace_grep_search → _terms` | cross_community | 4 |
| `Show → _match_repo_target` | cross_community | 4 |
| `List_env_export_keys → _match_repo_target` | cross_community | 4 |
| `Workspace_grep_search → _resolve_repo_path` | intra_community | 3 |
| `Workspace_grep_search → _search_with_rg` | cross_community | 3 |
| `Build → _resolve_repo_path` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Config | 2 calls |
| Commands | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_restore_switches_active_project"})` — see callers and callees
2. `gitnexus_query({query: "services"})` — find related execution flows
3. Read key files listed above for implementation details
