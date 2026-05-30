---
name: commands
description: "Skill for the Commands area of metagit-cli. 88 symbols across 21 files."
---

# Commands

88 symbols | 21 files | Cohesion: 72%

## When to Use

- Working with code in `src/`
- Understanding how update_record, delete_record, record_show work
- Modifying commands-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/cli/commands/context.py` | _load_manifest, _context_paths, _summarize_card, repo_card_cmd, objective_list_cmd (+12) |
| `src/metagit/cli/commands/record.py` | _get_record_manager, record_show, get_record, list_records, record_search (+6) |
| `src/metagit/cli/commands/workspace.py` | workspace, _catalog_ctx, workspace_project_list, workspace_project_add, workspace_project_remove (+6) |
| `tests/cli/commands/test_context.py` | _env_workspace_root, test_context_repo_card_json, test_context_objective_list_after_set, test_context_pack_tier_two_json_contains_digest, test_context_pack_tier_zero_json (+3) |
| `src/metagit/cli/commands/init.py` | _resolve_project_metadata, resolve_target_dir, init, _print_next_steps, _sanitize_workspace_path (+1) |
| `src/metagit/cli/commands/prompt.py` | _load_manifest, _prompt_ctx, _run_emit, prompt_workspace, prompt_project (+1) |
| `src/metagit/cli/commands/config.py` | config_show, config_validate, config_info, config_graph_export |
| `tests/cli/commands/test_config_patch.py` | _minimal_metagit, test_config_patch_single_op_save, test_config_patch_operations_file, test_config_preview_json |
| `src/metagit/core/config/manager.py` | load_config, validate_config, reload_config |
| `src/metagit/cli/commands/completion_cmd.py` | _root_cli, completion_show, completion_install |

## Entry Points

Start here when exploring this area:

- **`update_record`** (Function) — `src/metagit/core/record/manager.py:486`
- **`delete_record`** (Function) — `src/metagit/core/record/manager.py:504`
- **`record_show`** (Function) — `src/metagit/cli/commands/record.py:249`
- **`get_record`** (Function) — `src/metagit/cli/commands/record.py:258`
- **`list_records`** (Function) — `src/metagit/cli/commands/record.py:283`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `update_record` | Function | `src/metagit/core/record/manager.py` | 486 |
| `delete_record` | Function | `src/metagit/core/record/manager.py` | 504 |
| `record_show` | Function | `src/metagit/cli/commands/record.py` | 249 |
| `get_record` | Function | `src/metagit/cli/commands/record.py` | 258 |
| `list_records` | Function | `src/metagit/cli/commands/record.py` | 283 |
| `record_search` | Function | `src/metagit/cli/commands/record.py` | 329 |
| `record_update` | Function | `src/metagit/cli/commands/record.py` | 417 |
| `update_record` | Function | `src/metagit/cli/commands/record.py` | 467 |
| `record_delete` | Function | `src/metagit/cli/commands/record.py` | 489 |
| `delete_record` | Function | `src/metagit/cli/commands/record.py` | 517 |
| `record_export` | Function | `src/metagit/cli/commands/record.py` | 541 |
| `record_stats` | Function | `src/metagit/cli/commands/record.py` | 637 |
| `repo_card_cmd` | Function | `src/metagit/cli/commands/context.py` | 219 |
| `objective_list_cmd` | Function | `src/metagit/cli/commands/context.py` | 327 |
| `objective_set_cmd` | Function | `src/metagit/cli/commands/context.py` | 396 |
| `objective_get_cmd` | Function | `src/metagit/cli/commands/context.py` | 454 |
| `objective_complete_cmd` | Function | `src/metagit/cli/commands/context.py` | 483 |
| `objective_cancel_cmd` | Function | `src/metagit/cli/commands/context.py` | 509 |
| `approval_approve_cmd` | Function | `src/metagit/cli/commands/context.py` | 590 |
| `approval_deny_cmd` | Function | `src/metagit/cli/commands/context.py` | 620 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Pack_cmd → _read_json` | cross_community | 5 |
| `Pack_cmd → Ensure_dirs` | cross_community | 5 |
| `Pack_cmd → _write_json` | cross_community | 5 |
| `Do_POST → Load_config` | cross_community | 4 |
| `Search → _row_passes_filters` | cross_community | 4 |
| `Search → _match_row` | cross_community | 4 |
| `Search → _to_match` | cross_community | 4 |
| `Search → _sort_matches` | cross_community | 4 |
| `Objective_set_cmd → Load_config` | cross_community | 4 |
| `Do_DELETE → Load_config` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_189 | 17 calls |
| Examples | 9 calls |
| Cli | 6 calls |
| Project | 2 calls |
| Init | 2 calls |
| Context | 2 calls |
| Tests | 1 calls |

## How to Explore

1. `gitnexus_context({name: "update_record"})` — see callers and callees
2. `gitnexus_query({query: "commands"})` — find related execution flows
3. Read key files listed above for implementation details
