---
name: commands
description: "Skill for the Commands area of metagit-cli. 168 symbols across 44 files."
metadata:
  internal: true
---
# Commands

168 symbols | 44 files | Cohesion: 73%

## When to Use

- Working with code in `src/`
- Understanding how pack_cmd, repo_card_cmd, repomix_cmd work
- Modifying commands-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/cli/commands/context.py` | _load_manifest, _context_paths, _summarize_digest_line, _summarize_pack, _summarize_card_line (+12) |
| `src/metagit/cli/commands/record.py` | _get_record_manager, record_create, store_record, record_show, get_record (+10) |
| `src/metagit/cli/commands/workspace.py` | _catalog_ctx, workspace_project_add, workspace_project_remove, workspace_repo_add, workspace_repo_remove (+7) |
| `src/metagit/cli/commands/agent.py` | _emit_json, agent_preview, agent_export, agent_create, _require_manifest_root (+7) |
| `tests/cli/commands/test_context.py` | _env_workspace_root, test_context_repo_card_json, test_context_objective_list_after_set, test_context_objective_partial_update_without_title, test_context_approval_request_json (+5) |
| `tests/cli/commands/test_workspace_grep.py` | _env_workspace_root, _write_grep_fixture, test_workspace_grep_json_smoke, test_workspace_grep_excludes_node_modules, test_workspace_grep_info_without_rg (+2) |
| `src/metagit/cli/commands/prompt.py` | prompt_list, _load_manifest, _prompt_ctx, _run_emit, prompt_workspace (+2) |
| `src/metagit/cli/commands/appconfig.py` | appconfig_preview, appconfig_get, appconfig_create, appconfig_tree, appconfig_schema (+1) |
| `tests/cli/commands/test_project.py` | _write_manifest, _write_app_config, test_project_list_catalog_when_default_missing, test_project_list_catalog_when_multiple_without_default, test_project_list_empty_workspace (+1) |
| `src/metagit/cli/commands/project.py` | project_add, project_remove, project_rename, project_list, project_select |

## Entry Points

Start here when exploring this area:

- **`pack_cmd`** (Function) — `src/metagit/cli/commands/context.py:178`
- **`repo_card_cmd`** (Function) — `src/metagit/cli/commands/context.py:230`
- **`repomix_cmd`** (Function) — `src/metagit/cli/commands/context.py:279`
- **`objective_list_cmd`** (Function) — `src/metagit/cli/commands/context.py:342`
- **`objective_get_cmd`** (Function) — `src/metagit/cli/commands/context.py:457`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `pack_cmd` | Function | `src/metagit/cli/commands/context.py` | 178 |
| `repo_card_cmd` | Function | `src/metagit/cli/commands/context.py` | 230 |
| `repomix_cmd` | Function | `src/metagit/cli/commands/context.py` | 279 |
| `objective_list_cmd` | Function | `src/metagit/cli/commands/context.py` | 342 |
| `objective_get_cmd` | Function | `src/metagit/cli/commands/context.py` | 457 |
| `objective_complete_cmd` | Function | `src/metagit/cli/commands/context.py` | 486 |
| `objective_cancel_cmd` | Function | `src/metagit/cli/commands/context.py` | 512 |
| `approval_approve_cmd` | Function | `src/metagit/cli/commands/context.py` | 593 |
| `approval_request_cmd` | Function | `src/metagit/cli/commands/context.py` | 647 |
| `approval_deny_cmd` | Function | `src/metagit/cli/commands/context.py` | 702 |
| `resolve_definition_root` | Function | `src/metagit/core/workspace/root_resolver.py` | 10 |
| `resolve_session_root` | Function | `src/metagit/core/workspace/root_resolver.py` | 30 |
| `record_create` | Function | `src/metagit/cli/commands/record.py` | 183 |
| `store_record` | Function | `src/metagit/cli/commands/record.py` | 226 |
| `record_show` | Function | `src/metagit/cli/commands/record.py` | 249 |
| `get_record` | Function | `src/metagit/cli/commands/record.py` | 258 |
| `list_records` | Function | `src/metagit/cli/commands/record.py` | 283 |
| `record_update` | Function | `src/metagit/cli/commands/record.py` | 417 |
| `update_record` | Function | `src/metagit/cli/commands/record.py` | 467 |
| `record_delete` | Function | `src/metagit/cli/commands/record.py` | 489 |

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
| Examples | 11 calls |
| Config | 9 calls |
| Workspace | 9 calls |
| Cluster_370 | 9 calls |
| Agent | 9 calls |
| Cli | 6 calls |
| Project | 2 calls |
| Tests | 2 calls |

## How to Explore

1. `gitnexus_context({name: "pack_cmd"})` — see callers and callees
2. `gitnexus_query({query: "commands"})` — find related execution flows
3. Read key files listed above for implementation details
