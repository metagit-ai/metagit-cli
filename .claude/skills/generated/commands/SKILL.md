---
name: commands
description: "Skill for the Commands area of metagit-cli. 204 symbols across 56 files."
metadata:
  internal: true
---
# Commands

204 symbols | 56 files | Cohesion: 74%

## When to Use

- Working with code in `src/`
- Understanding how appconfig_preview, appconfig_patch, config_preview work
- Modifying commands-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/cli/commands/context.py` | _load_manifest, _context_paths, _summarize_digest_line, _summarize_pack, _summarize_card_line (+12) |
| `src/metagit/cli/commands/record.py` | _get_record_manager, record_create, store_record, record_show, get_record (+10) |
| `src/metagit/cli/commands/workspace.py` | _layout_ctx, workspace_project_rename, workspace_repo_rename, workspace_repo_move, workspace_project_add (+7) |
| `tests/cli/commands/test_context.py` | _env_workspace_root, test_context_repo_card_json, test_context_objective_list_after_set, test_context_objective_partial_update_without_title, test_context_approval_request_json (+5) |
| `src/metagit/cli/commands/agent.py` | agent_overlay_init, _emit_json, agent_preview, agent_export, agent_create (+4) |
| `src/metagit/cli/commands/appconfig.py` | appconfig_preview, appconfig_patch, appconfig_create, appconfig_show, appconfig_get (+3) |
| `src/metagit/cli/commands/config.py` | config_preview, config_patch, config_show, config_set, set_nested_attr (+2) |
| `src/metagit/cli/commands/project_repo.py` | repo_prune, repo_rename, repo_move, repo_remove, repo_add (+2) |
| `src/metagit/cli/config_patch_ops.py` | parse_cli_value, load_operations_file, resolve_operations, emit_patch_result, emit_preview_result (+2) |
| `tests/cli/commands/test_version.py` | _sample_result, test_version_check_json, test_version_check_human_output, test_version_check_no_notes, _sample_upgrade_result (+2) |

## Entry Points

Start here when exploring this area:

- **`appconfig_preview`** (Function) — `src/metagit/cli/commands/appconfig.py:276`
- **`appconfig_patch`** (Function) — `src/metagit/cli/commands/appconfig.py:356`
- **`config_preview`** (Function) — `src/metagit/cli/commands/config.py:530`
- **`config_patch`** (Function) — `src/metagit/cli/commands/config.py:610`
- **`repo_prune`** (Function) — `src/metagit/cli/commands/project_repo.py:509`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `appconfig_preview` | Function | `src/metagit/cli/commands/appconfig.py` | 276 |
| `appconfig_patch` | Function | `src/metagit/cli/commands/appconfig.py` | 356 |
| `config_preview` | Function | `src/metagit/cli/commands/config.py` | 530 |
| `config_patch` | Function | `src/metagit/cli/commands/config.py` | 610 |
| `repo_prune` | Function | `src/metagit/cli/commands/project_repo.py` | 509 |
| `source_sync` | Function | `src/metagit/cli/commands/project_source.py` | 77 |
| `parse_cli_value` | Function | `src/metagit/cli/config_patch_ops.py` | 16 |
| `load_operations_file` | Function | `src/metagit/cli/config_patch_ops.py` | 38 |
| `resolve_operations` | Function | `src/metagit/cli/config_patch_ops.py` | 59 |
| `emit_patch_result` | Function | `src/metagit/cli/config_patch_ops.py` | 92 |
| `emit_preview_result` | Function | `src/metagit/cli/config_patch_ops.py` | 121 |
| `pack_cmd` | Function | `src/metagit/cli/commands/context.py` | 178 |
| `repo_card_cmd` | Function | `src/metagit/cli/commands/context.py` | 230 |
| `repomix_cmd` | Function | `src/metagit/cli/commands/context.py` | 279 |
| `objective_list_cmd` | Function | `src/metagit/cli/commands/context.py` | 342 |
| `objective_get_cmd` | Function | `src/metagit/cli/commands/context.py` | 457 |
| `objective_complete_cmd` | Function | `src/metagit/cli/commands/context.py` | 486 |
| `objective_cancel_cmd` | Function | `src/metagit/cli/commands/context.py` | 512 |
| `approval_approve_cmd` | Function | `src/metagit/cli/commands/context.py` | 593 |
| `approval_request_cmd` | Function | `src/metagit/cli/commands/context.py` | 647 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Agent_list → Overlay_template_dir` | cross_community | 8 |
| `Agent_list → _bundled_template_dir` | cross_community | 7 |
| `Agent_list → _deep_merge_dict` | cross_community | 7 |
| `Agent_export → _bundled_template_dir` | cross_community | 7 |
| `Agent_export → _deep_merge_dict` | cross_community | 7 |
| `Agent_validate → Overlay_template_dir` | cross_community | 7 |
| `Repo_add → _promptkit` | cross_community | 6 |
| `Repo_add → _interactive_prompt_ui_enabled` | cross_community | 6 |
| `Agent_create → _validate_merged_payload` | cross_community | 6 |
| `Agent_create → _bundled_template_dir` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_385 | 16 calls |
| Examples | 11 calls |
| Config | 10 calls |
| Agent | 8 calls |
| Workspace | 5 calls |
| Project | 4 calls |
| Web | 4 calls |
| Tests | 3 calls |

## How to Explore

1. `gitnexus_context({name: "appconfig_preview"})` — see callers and callees
2. `gitnexus_query({query: "commands"})` — find related execution flows
3. Read key files listed above for implementation details
