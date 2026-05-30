---
name: cli
description: "Skill for the Cli area of metagit-cli. 33 symbols across 8 files."
---

# Cli

33 symbols | 8 files | Cohesion: 86%

## When to Use

- Working with code in `src/`
- Understanding how cli, emit_patch_result, emit_preview_result work
- Modifying cli-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/cli/shell_completion.py` | _definition_path_from_ctx, _project_names_from_manifest, _repo_names_from_manifest, _filter_incomplete, complete_projects (+6) |
| `src/metagit/cli/config_patch_ops.py` | emit_patch_result, emit_preview_result, parse_cli_value, load_operations_file, resolve_operations (+2) |
| `src/metagit/core/utils/logging.py` | print_debug, debug, warning, error, success |
| `tests/cli/test_shell_completion.py` | _write_manifest, test_complete_projects_from_manifest, test_complete_repos_scoped_to_project |
| `src/metagit/cli/json_output.py` | emit_json, exit_on_catalog_mutation, exit_on_layout_mutation |
| `src/metagit/cli/commands/project_repo.py` | repo_add, repo_prune |
| `src/metagit/cli/main.py` | cli |
| `src/metagit/cli/commands/project_source.py` | source_sync |

## Entry Points

Start here when exploring this area:

- **`cli`** (Function) — `src/metagit/cli/main.py:63`
- **`emit_patch_result`** (Function) — `src/metagit/cli/config_patch_ops.py:92`
- **`emit_preview_result`** (Function) — `src/metagit/cli/config_patch_ops.py:121`
- **`print_debug`** (Function) — `src/metagit/core/utils/logging.py:306`
- **`debug`** (Function) — `src/metagit/core/utils/logging.py:426`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `cli` | Function | `src/metagit/cli/main.py` | 63 |
| `emit_patch_result` | Function | `src/metagit/cli/config_patch_ops.py` | 92 |
| `emit_preview_result` | Function | `src/metagit/cli/config_patch_ops.py` | 121 |
| `print_debug` | Function | `src/metagit/core/utils/logging.py` | 306 |
| `debug` | Function | `src/metagit/core/utils/logging.py` | 426 |
| `warning` | Function | `src/metagit/core/utils/logging.py` | 442 |
| `error` | Function | `src/metagit/core/utils/logging.py` | 450 |
| `success` | Function | `src/metagit/core/utils/logging.py` | 584 |
| `source_sync` | Function | `src/metagit/cli/commands/project_source.py` | 77 |
| `repo_add` | Function | `src/metagit/cli/commands/project_repo.py` | 253 |
| `repo_prune` | Function | `src/metagit/cli/commands/project_repo.py` | 404 |
| `complete_projects` | Function | `src/metagit/cli/shell_completion.py` | 90 |
| `complete_repos` | Function | `src/metagit/cli/shell_completion.py` | 100 |
| `complete_repomix_profiles` | Function | `src/metagit/cli/shell_completion.py` | 123 |
| `test_complete_projects_from_manifest` | Function | `tests/cli/test_shell_completion.py` | 48 |
| `test_complete_repos_scoped_to_project` | Function | `tests/cli/test_shell_completion.py` | 65 |
| `emit_json` | Function | `src/metagit/cli/json_output.py` | 14 |
| `exit_on_catalog_mutation` | Function | `src/metagit/cli/json_output.py` | 23 |
| `exit_on_layout_mutation` | Function | `src/metagit/cli/json_output.py` | 50 |
| `parse_cli_value` | Function | `src/metagit/cli/config_patch_ops.py` | 16 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Source_sync → _include_candidate` | cross_community | 4 |
| `Source_sync → _to_project_path` | cross_community | 3 |
| `Source_sync → _normalized_url` | cross_community | 3 |
| `Source_sync → _needs_update` | cross_community | 3 |
| `Repo_add → _find_project` | cross_community | 3 |
| `Repo_add → _mutation_error` | cross_community | 3 |
| `Complete_projects → Load_config` | cross_community | 3 |
| `Complete_repos → Load_config` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_189 | 15 calls |
| Project | 3 calls |
| Commands | 2 calls |
| Workspace | 2 calls |

## How to Explore

1. `gitnexus_context({name: "cli"})` — see callers and callees
2. `gitnexus_query({query: "cli"})` — find related execution flows
3. Read key files listed above for implementation details
