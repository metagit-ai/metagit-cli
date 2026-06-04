---
name: web
description: "Skill for the Web area of metagit-cli. 114 symbols across 13 files."
---

# Web

114 symbols | 13 files | Cohesion: 79%

## When to Use

- Working with code in `src/`
- Understanding how test_remove_workspace_project_when_projects_null, test_ops_objectives_get_post_patch, handle work
- Modifying web-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/web/schema_tree.py` | _disable_at_path, _enable_at_path, _append_at_path, _remove_at_path, _materialize_field (+25) |
| `src/metagit/core/web/config_handler.py` | handle, _respond_metagit_tree, _patch_metagit, _preview_metagit, _preview_appconfig (+12) |
| `src/metagit/core/web/ops_handler.py` | handle, _post_objectives, _post_approval_resolve, _post_health, _get_graph (+10) |
| `tests/core/web/test_schema_tree.py` | test_remove_workspace_project_when_projects_null, test_disable_optional_field_removes_key, test_enable_optional_field_adds_default, test_set_field_updates_value, test_apply_operations_returns_original_instance_on_validation_error (+8) |
| `src/metagit/core/web/server.py` | do_GET, do_PATCH, do_POST, do_DELETE, _dispatch (+3) |
| `tests/core/web/test_config_handler.py` | _start_server, _patch_json, test_get_metagit_config_tree, test_patch_metagit_set_name_without_save, test_patch_metagit_set_name_with_save (+3) |
| `src/metagit/core/web/job_store.py` | create_job, append_event, drain_events, mark_running, complete (+2) |
| `tests/core/web/test_ops_handler.py` | _start_server, _post_json, test_health_endpoint_returns_ok, test_prune_preview_empty, test_sync_dry_run_job_completes |
| `src/metagit/core/web/graph_service.py` | build_view, _append_manual_edges, _append_inferred_edges, _append_edge |
| `src/metagit/core/web/static_handler.py` | handle, _resolve_file, _send_file |

## Entry Points

Start here when exploring this area:

- **`test_remove_workspace_project_when_projects_null`** (Function) — `tests/core/web/test_schema_tree.py:167`
- **`test_ops_objectives_get_post_patch`** (Function) — `tests/core/web/test_ops_objectives.py:9`
- **`handle`** (Function) — `src/metagit/core/web/ops_handler.py:76`
- **`handle`** (Function) — `src/metagit/core/web/static_handler.py:22`
- **`do_GET`** (Function) — `src/metagit/core/web/server.py:82`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_remove_workspace_project_when_projects_null` | Function | `tests/core/web/test_schema_tree.py` | 167 |
| `test_ops_objectives_get_post_patch` | Function | `tests/core/web/test_ops_objectives.py` | 9 |
| `handle` | Function | `src/metagit/core/web/ops_handler.py` | 76 |
| `handle` | Function | `src/metagit/core/web/static_handler.py` | 22 |
| `do_GET` | Function | `src/metagit/core/web/server.py` | 82 |
| `do_PATCH` | Function | `src/metagit/core/web/server.py` | 85 |
| `do_POST` | Function | `src/metagit/core/web/server.py` | 88 |
| `do_DELETE` | Function | `src/metagit/core/web/server.py` | 91 |
| `sync_events_job_id` | Function | `src/metagit/core/web/ops_handler.py` | 140 |
| `stream_sync_events` | Function | `src/metagit/core/web/ops_handler.py` | 148 |
| `test_disable_optional_field_removes_key` | Function | `tests/core/web/test_schema_tree.py` | 35 |
| `test_enable_optional_field_adds_default` | Function | `tests/core/web/test_schema_tree.py` | 48 |
| `test_set_field_updates_value` | Function | `tests/core/web/test_schema_tree.py` | 67 |
| `test_apply_operations_returns_original_instance_on_validation_error` | Function | `tests/core/web/test_schema_tree.py` | 97 |
| `test_sensitive_token_unchanged_after_masked_set` | Function | `tests/core/web/test_schema_tree.py` | 112 |
| `test_enable_optional_list_defaults_empty` | Function | `tests/core/web/test_schema_tree.py` | 154 |
| `test_remove_workspace_project_from_preview_batch` | Function | `tests/core/web/test_schema_tree.py` | 180 |
| `apply_operations` | Function | `src/metagit/core/web/schema_tree.py` | 58 |
| `handle` | Function | `src/metagit/core/web/config_handler.py` | 50 |
| `test_build_metagit_tree_marks_present_fields` | Function | `tests/core/web/test_schema_tree.py` | 9 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Handle → _validate_objective_id` | cross_community | 5 |
| `Handle → Load_config` | cross_community | 4 |
| `Handle → _parse_body` | intra_community | 4 |
| `Handle → _tree_response` | cross_community | 4 |
| `Handle → _load_appconfig` | cross_community | 4 |
| `Handle → Load_config` | cross_community | 4 |
| `Handle → Normalize_objective_partial` | cross_community | 4 |
| `Handle → _append_agent_note` | cross_community | 4 |
| `Build_view → _append_edge` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Context | 5 calls |
| Api | 5 calls |
| Config | 3 calls |
| Workspace | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_remove_workspace_project_when_projects_null"})` — see callers and callees
2. `gitnexus_query({query: "web"})` — find related execution flows
3. Read key files listed above for implementation details
