---
name: cli
description: "Skill for the Cli area of metagit-cli. 29 symbols across 8 files."
metadata:
  internal: true
---
# Cli

29 symbols | 8 files | Cohesion: 78%

## When to Use

- Working with code in `src/`
- Understanding how completion_install, completion_doctor, default_install_path work
- Modifying cli-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/cli/shell_completion.py` | default_install_path, install_completion_script, shell_activation_hint, metagit_executable, verify_completion_callback (+8) |
| `src/metagit/cli/config_patch_ops.py` | parse_cli_value, load_operations_file, resolve_operations, emit_preview_result |
| `src/metagit/core/utils/logging.py` | print_debug, print_error, debug, error |
| `tests/cli/test_shell_completion.py` | _write_manifest, test_complete_projects_from_manifest, test_complete_repos_scoped_to_project |
| `src/metagit/cli/commands/completion_cmd.py` | completion_install, completion_doctor |
| `src/metagit/cli/commands/appconfig.py` | appconfig_preview |
| `src/metagit/cli/commands/config.py` | config_preview |
| `src/metagit/cli/main.py` | cli |

## Entry Points

Start here when exploring this area:

- **`completion_install`** (Function) — `src/metagit/cli/commands/completion_cmd.py:65`
- **`completion_doctor`** (Function) — `src/metagit/cli/commands/completion_cmd.py:90`
- **`default_install_path`** (Function) — `src/metagit/cli/shell_completion.py:163`
- **`install_completion_script`** (Function) — `src/metagit/cli/shell_completion.py:188`
- **`shell_activation_hint`** (Function) — `src/metagit/cli/shell_completion.py:206`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `completion_install` | Function | `src/metagit/cli/commands/completion_cmd.py` | 65 |
| `completion_doctor` | Function | `src/metagit/cli/commands/completion_cmd.py` | 90 |
| `default_install_path` | Function | `src/metagit/cli/shell_completion.py` | 163 |
| `install_completion_script` | Function | `src/metagit/cli/shell_completion.py` | 188 |
| `shell_activation_hint` | Function | `src/metagit/cli/shell_completion.py` | 206 |
| `metagit_executable` | Function | `src/metagit/cli/shell_completion.py` | 219 |
| `verify_completion_callback` | Function | `src/metagit/cli/shell_completion.py` | 235 |
| `format_install_message` | Function | `src/metagit/cli/shell_completion.py` | 258 |
| `complete_projects` | Function | `src/metagit/cli/shell_completion.py` | 90 |
| `complete_repos` | Function | `src/metagit/cli/shell_completion.py` | 100 |
| `complete_repomix_profiles` | Function | `src/metagit/cli/shell_completion.py` | 123 |
| `appconfig_preview` | Function | `src/metagit/cli/commands/appconfig.py` | 276 |
| `config_preview` | Function | `src/metagit/cli/commands/config.py` | 530 |
| `parse_cli_value` | Function | `src/metagit/cli/config_patch_ops.py` | 16 |
| `load_operations_file` | Function | `src/metagit/cli/config_patch_ops.py` | 38 |
| `resolve_operations` | Function | `src/metagit/cli/config_patch_ops.py` | 59 |
| `emit_preview_result` | Function | `src/metagit/cli/config_patch_ops.py` | 121 |
| `cli` | Function | `src/metagit/cli/main.py` | 66 |
| `test_complete_projects_from_manifest` | Function | `tests/cli/test_shell_completion.py` | 48 |
| `test_complete_repos_scoped_to_project` | Function | `tests/cli/test_shell_completion.py` | 65 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Debug` | cross_community | 4 |
| `Main → Debug` | cross_community | 4 |
| `Main → Debug` | cross_community | 4 |
| `Completion_install → _completion_class` | cross_community | 3 |
| `Cli → _override_from_environment` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 8 calls |
| Cluster_394 | 2 calls |

## How to Explore

1. `gitnexus_context({name: "completion_install"})` — see callers and callees
2. `gitnexus_query({query: "cli"})` — find related execution flows
3. Read key files listed above for implementation details
