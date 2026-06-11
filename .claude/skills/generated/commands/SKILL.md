---
name: commands
description: "Skill for the Commands area of metagit-cli. 212 symbols across 57 files."
metadata:
  internal: true
---
# Commands

212 symbols | 57 files | Cohesion: 70%

## When to Use

- Working with code in `src/`
- Understanding how pack_cmd, repo_card_cmd, repomix_cmd work
- Modifying commands-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/cli/commands/context.py` | _load_manifest, _context_paths, _summarize_digest_line, _summarize_pack, _summarize_card_line (+12) |
| `src/metagit/cli/commands/record.py` | _get_record_manager, record_create, store_record, record_show, get_record (+10) |
| `src/metagit/cli/commands/workspace.py` | _layout_ctx, workspace_project_rename, workspace_repo_rename, workspace_repo_move, workspace (+8) |
| `src/metagit/cli/commands/agent.py` | _emit_json, agent_preview, agent_export, agent_create, _require_manifest_root (+7) |
| `tests/cli/commands/test_context.py` | _env_workspace_root, test_context_repo_card_json, test_context_objective_list_after_set, test_context_objective_partial_update_without_title, test_context_approval_request_json (+5) |
| `src/metagit/cli/commands/config.py` | config_validate, config_set, set_nested_attr, config_info, config_graph_export (+4) |
| `src/metagit/cli/commands/project_repo.py` | repo_rename, repo_move, repo_add, repo_promote, repo_prune (+2) |
| `tests/cli/commands/test_version.py` | _sample_result, test_version_check_json, test_version_check_human_output, test_version_check_no_notes, _sample_upgrade_result (+2) |
| `tests/cli/commands/test_workspace_grep.py` | _env_workspace_root, _write_grep_fixture, test_workspace_grep_json_smoke, test_workspace_grep_excludes_node_modules, test_workspace_grep_info_without_rg (+2) |
| `src/metagit/cli/commands/appconfig.py` | appconfig_show, appconfig_get, appconfig_create, appconfig_tree, appconfig_patch (+2) |

## Entry Points

Start here when exploring this area:

- **`pack_cmd`** (Function) — `src/metagit/cli/commands/context.py:179`
- **`repo_card_cmd`** (Function) — `src/metagit/cli/commands/context.py:231`
- **`repomix_cmd`** (Function) — `src/metagit/cli/commands/context.py:280`
- **`objective_list_cmd`** (Function) — `src/metagit/cli/commands/context.py:343`
- **`objective_get_cmd`** (Function) — `src/metagit/cli/commands/context.py:458`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `pack_cmd` | Function | `src/metagit/cli/commands/context.py` | 179 |
| `repo_card_cmd` | Function | `src/metagit/cli/commands/context.py` | 231 |
| `repomix_cmd` | Function | `src/metagit/cli/commands/context.py` | 280 |
| `objective_list_cmd` | Function | `src/metagit/cli/commands/context.py` | 343 |
| `objective_get_cmd` | Function | `src/metagit/cli/commands/context.py` | 458 |
| `objective_complete_cmd` | Function | `src/metagit/cli/commands/context.py` | 487 |
| `objective_cancel_cmd` | Function | `src/metagit/cli/commands/context.py` | 513 |
| `approval_approve_cmd` | Function | `src/metagit/cli/commands/context.py` | 594 |
| `approval_request_cmd` | Function | `src/metagit/cli/commands/context.py` | 656 |
| `approval_deny_cmd` | Function | `src/metagit/cli/commands/context.py` | 711 |
| `resolve_definition_root` | Function | `src/metagit/core/workspace/root_resolver.py` | 10 |
| `record_create` | Function | `src/metagit/cli/commands/record.py` | 183 |
| `store_record` | Function | `src/metagit/cli/commands/record.py` | 226 |
| `record_show` | Function | `src/metagit/cli/commands/record.py` | 249 |
| `get_record` | Function | `src/metagit/cli/commands/record.py` | 258 |
| `list_records` | Function | `src/metagit/cli/commands/record.py` | 283 |
| `record_update` | Function | `src/metagit/cli/commands/record.py` | 417 |
| `update_record` | Function | `src/metagit/cli/commands/record.py` | 467 |
| `record_delete` | Function | `src/metagit/cli/commands/record.py` | 489 |
| `delete_record` | Function | `src/metagit/cli/commands/record.py` | 517 |

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
| Cluster_397 | 20 calls |
| Workspace | 12 calls |
| Examples | 11 calls |
| Cli | 10 calls |
| Agent | 9 calls |
| Services | 4 calls |
| Tests | 3 calls |
| Project | 2 calls |

## How to Explore

1. `gitnexus_context({name: "pack_cmd"})` — see callers and callees
2. `gitnexus_query({query: "commands"})` — find related execution flows
3. Read key files listed above for implementation details
