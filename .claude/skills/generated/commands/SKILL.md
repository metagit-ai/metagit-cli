---
name: commands
description: "Skill for the Commands area of metagit-cli. 217 symbols across 56 files."
metadata:
  internal: true
---
# Commands

217 symbols | 56 files | Cohesion: 77%

## When to Use

- Working with code in `src/`
- Understanding how demonstrate_datetime_serialization_fix, demonstrate_record_creation, main work
- Modifying commands-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/cli/commands/context.py` | _load_manifest, _context_paths, _summarize_digest_line, _summarize_pack, _summarize_card_line (+12) |
| `src/metagit/cli/commands/record.py` | _get_record_manager, record_create, store_record, record_show, get_record (+10) |
| `src/metagit/cli/commands/workspace.py` | _layout_ctx, workspace_project_rename, workspace_repo_rename, workspace_repo_move, workspace_project_add (+7) |
| `src/metagit/cli/commands/agent.py` | _require_manifest_root, agent_dispatch_plan, agent_overlay_init, agent_overlay_path, _emit_json (+7) |
| `src/metagit/core/record/manager.py` | create_record_from_config, _get_git_info, store_record, get_record, update_record (+5) |
| `tests/cli/commands/test_context.py` | _env_workspace_root, test_context_repo_card_json, test_context_objective_list_after_set, test_context_objective_partial_update_without_title, test_context_approval_request_json (+5) |
| `examples/test_record_manager_simple.py` | test_basic_functionality, store_record, get_record, list_records, test_error_handling (+2) |
| `src/metagit/cli/commands/project_repo.py` | repo_add, repo_prune, repo_rename, repo_move, repo_select (+2) |
| `tests/cli/commands/test_version.py` | _sample_result, test_version_check_json, test_version_check_human_output, test_version_check_no_notes, _sample_upgrade_result (+2) |
| `tests/cli/commands/test_workspace_grep.py` | _env_workspace_root, _write_grep_fixture, test_workspace_grep_json_smoke, test_workspace_grep_excludes_node_modules, test_workspace_grep_info_without_rg (+2) |

## Entry Points

Start here when exploring this area:

- **`demonstrate_datetime_serialization_fix`** (Function) — `examples/datetime_serialization_fix_example.py:19`
- **`demonstrate_record_creation`** (Function) — `examples/datetime_serialization_fix_example.py:66`
- **`main`** (Function) — `examples/datetime_serialization_fix_example.py:160`
- **`example_local_file_storage`** (Function) — `examples/record_manager_example.py:23`
- **`example_opensearch_storage`** (Function) — `examples/record_manager_example.py:105`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `demonstrate_datetime_serialization_fix` | Function | `examples/datetime_serialization_fix_example.py` | 19 |
| `demonstrate_record_creation` | Function | `examples/datetime_serialization_fix_example.py` | 66 |
| `main` | Function | `examples/datetime_serialization_fix_example.py` | 160 |
| `example_local_file_storage` | Function | `examples/record_manager_example.py` | 23 |
| `example_opensearch_storage` | Function | `examples/record_manager_example.py` | 105 |
| `example_file_operations` | Function | `examples/record_manager_example.py` | 180 |
| `main` | Function | `examples/record_manager_example.py` | 235 |
| `test_basic_functionality` | Function | `examples/test_record_manager_simple.py` | 16 |
| `store_record` | Function | `examples/test_record_manager_simple.py` | 64 |
| `get_record` | Function | `examples/test_record_manager_simple.py` | 74 |
| `list_records` | Function | `examples/test_record_manager_simple.py` | 94 |
| `test_error_handling` | Function | `examples/test_record_manager_simple.py` | 116 |
| `test_no_backend` | Function | `examples/test_record_manager_simple.py` | 124 |
| `config_create` | Function | `src/metagit/cli/commands/config.py` | 125 |
| `record_create` | Function | `src/metagit/cli/commands/record.py` | 183 |
| `store_record` | Function | `src/metagit/cli/commands/record.py` | 226 |
| `record_show` | Function | `src/metagit/cli/commands/record.py` | 249 |
| `get_record` | Function | `src/metagit/cli/commands/record.py` | 258 |
| `list_records` | Function | `src/metagit/cli/commands/record.py` | 283 |
| `record_update` | Function | `src/metagit/cli/commands/record.py` | 417 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Agent_list → Overlay_template_dir` | cross_community | 8 |
| `Agent_list → _bundled_template_dir` | cross_community | 7 |
| `Agent_list → _deep_merge_dict` | cross_community | 7 |
| `Agent_export → _bundled_template_dir` | cross_community | 7 |
| `Agent_export → _deep_merge_dict` | cross_community | 7 |
| `Agent_validate → Overlay_template_dir` | cross_community | 7 |
| `Agent_dispatch_plan → Expand_agent_path` | cross_community | 7 |
| `Repo_add → _promptkit` | cross_community | 6 |
| `Repo_add → _interactive_prompt_ui_enabled` | cross_community | 6 |
| `Agent_create → _validate_merged_payload` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Config | 11 calls |
| Workspace | 11 calls |
| Cluster_384 | 9 calls |
| Agent | 9 calls |
| Cli | 7 calls |
| Services | 3 calls |
| Project | 3 calls |
| Tests | 3 calls |

## How to Explore

1. `gitnexus_context({name: "demonstrate_datetime_serialization_fix"})` — see callers and callees
2. `gitnexus_query({query: "commands"})` — find related execution flows
3. Read key files listed above for implementation details
