---
name: web
description: "Skill for the Web area of metagit-cli. 139 symbols across 17 files."
metadata:
  internal: true
---
# Web

139 symbols | 17 files | Cohesion: 72%

## When to Use

- Working with code in `src/`
- Understanding how test_ops_objectives_get_post_patch, test_remove_workspace_project_when_projects_null, test_disable_optional_field_removes_key work
- Modifying web-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/web/schema_tree.py` | _disable_at_path, _enable_at_path, _append_at_path, _remove_at_path, _materialize_field (+25) |
| `src/metagit/core/web/ops_handler.py` | handle, _post_objectives, _post_approval_resolve, _post_open, _post_health (+15) |
| `src/metagit/core/web/config_handler.py` | handle, _respond_metagit_tree, _patch_metagit, _preview_metagit, _preview_appconfig (+12) |
| `tests/core/web/test_schema_tree.py` | test_remove_workspace_project_when_projects_null, test_disable_optional_field_removes_key, test_enable_optional_field_adds_default, test_set_field_updates_value, test_apply_operations_returns_original_instance_on_validation_error (+10) |
| `tests/core/web/test_config_handler.py` | _start_server, _patch_json, test_get_metagit_config_tree, test_patch_metagit_set_name_without_save, test_patch_metagit_set_name_with_save (+3) |
| `tests/core/web/test_ops_handler.py` | _start_server, test_prune_preview_empty, test_open_rejects_unknown_path, test_source_sync_manifest_dry_run, _post_json (+3) |
| `src/metagit/core/web/agent_handler.py` | handle, _service, _respond_catalog, _respond_preview, _respond_dispatch_plan (+2) |
| `src/metagit/core/web/job_store.py` | create_job, append_event, drain_events, mark_running, complete (+2) |
| `src/metagit/core/web/server.py` | do_GET, do_PATCH, do_POST, do_DELETE, _dispatch (+1) |
| `tests/core/web/test_agent_web.py` | _start_server, test_agent_catalog_route, test_agent_overlay_init_route, test_agent_dispatch_plan_route, test_agent_preview_route |

## Entry Points

Start here when exploring this area:

- **`test_ops_objectives_get_post_patch`** (Function) — `tests/core/web/test_ops_objectives.py:9`
- **`test_remove_workspace_project_when_projects_null`** (Function) — `tests/core/web/test_schema_tree.py:167`
- **`test_disable_optional_field_removes_key`** (Function) — `tests/core/web/test_schema_tree.py:35`
- **`test_enable_optional_field_adds_default`** (Function) — `tests/core/web/test_schema_tree.py:48`
- **`test_set_field_updates_value`** (Function) — `tests/core/web/test_schema_tree.py:67`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_ops_objectives_get_post_patch` | Function | `tests/core/web/test_ops_objectives.py` | 9 |
| `test_remove_workspace_project_when_projects_null` | Function | `tests/core/web/test_schema_tree.py` | 167 |
| `test_disable_optional_field_removes_key` | Function | `tests/core/web/test_schema_tree.py` | 35 |
| `test_enable_optional_field_adds_default` | Function | `tests/core/web/test_schema_tree.py` | 48 |
| `test_set_field_updates_value` | Function | `tests/core/web/test_schema_tree.py` | 67 |
| `test_apply_operations_returns_original_instance_on_validation_error` | Function | `tests/core/web/test_schema_tree.py` | 97 |
| `test_sensitive_token_unchanged_after_masked_set` | Function | `tests/core/web/test_schema_tree.py` | 112 |
| `test_enable_optional_list_defaults_empty` | Function | `tests/core/web/test_schema_tree.py` | 154 |
| `test_remove_workspace_project_from_preview_batch` | Function | `tests/core/web/test_schema_tree.py` | 180 |
| `test_append_workspace_project_validates_with_empty_sources` | Function | `tests/core/web/test_schema_tree.py` | 237 |
| `read_disk_text` | Function | `src/metagit/core/web/config_preview.py` | 19 |
| `test_get_metagit_config_tree` | Function | `tests/core/web/test_config_handler.py` | 67 |
| `test_patch_metagit_set_name_without_save` | Function | `tests/core/web/test_config_handler.py` | 87 |
| `test_patch_metagit_set_name_with_save` | Function | `tests/core/web/test_config_handler.py` | 117 |
| `test_patch_metagit_save_true_invalid_op_returns_422_and_does_not_write` | Function | `tests/core/web/test_config_handler.py` | 147 |
| `test_get_metagit_preview_normalized` | Function | `tests/core/web/test_config_handler.py` | 176 |
| `test_post_metagit_preview_draft_operations` | Function | `tests/core/web/test_config_handler.py` | 193 |
| `config_show` | Function | `src/metagit/cli/commands/config.py` | 70 |
| `dump_config_dict` | Function | `src/metagit/core/config/yaml_display.py` | 131 |
| `redact_secrets` | Function | `src/metagit/core/web/config_preview.py` | 27 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Handle → _override_from_environment` | cross_community | 5 |
| `Handle → Load_config` | cross_community | 4 |
| `Handle → _parse_body` | intra_community | 4 |
| `Handle → _tree_response` | cross_community | 4 |
| `Preview → Dump_config_dict` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 8 calls |
| Config | 6 calls |
| Api | 5 calls |
| Agent | 5 calls |
| Context | 4 calls |
| Services | 2 calls |
| Tests | 1 calls |
| Project | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_ops_objectives_get_post_patch"})` — see callers and callees
2. `gitnexus_query({query: "web"})` — find related execution flows
3. Read key files listed above for implementation details
