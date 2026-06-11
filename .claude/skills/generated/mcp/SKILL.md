---
name: mcp
description: "Skill for the Mcp area of metagit-cli. 58 symbols across 13 files."
metadata:
  internal: true
---
# Mcp

58 symbols | 13 files | Cohesion: 79%

## When to Use

- Working with code in `tests/`
- Understanding how test_initialize_request_returns_capabilities, test_tools_list_returns_inactive_tools_without_config, test_tools_call_workspace_status_returns_text_payload work
- Modifying mcp-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/core/mcp/test_runtime.py` | test_initialize_request_returns_capabilities, test_tools_list_returns_inactive_tools_without_config, test_tools_call_workspace_status_returns_text_payload, test_resources_read_ops_log_returns_json_content, test_tools_call_invalid_arguments_returns_mcp_invalid_params (+17) |
| `src/metagit/core/mcp/runtime.py` | _handle_request, _handle_initialize, _error_response, _dispatch_tool, _catalog_paths (+13) |
| `tests/core/mcp/test_gate.py` | test_missing_root_is_inactive_missing, test_missing_config_file_is_inactive_missing, test_invalid_config_file_is_inactive_invalid, test_valid_config_file_is_active |
| `tests/core/mcp/test_root_resolver.py` | test_env_root_has_highest_precedence, test_cli_root_used_when_env_unset, test_walk_up_finds_workspace_root |
| `src/metagit/core/mcp/root_resolver.py` | resolve, _walk_for_config |
| `tests/core/mcp/test_tool_registry.py` | test_inactive_registry_exposes_only_safe_tools, test_active_registry_exposes_full_toolset |
| `tests/integration/test_mcp_workspace_flow.py` | test_end_to_end_workspace_activation_and_discovery |
| `src/metagit/core/mcp/tools/bootstrap_plan_only.py` | metagit_bootstrap_config_plan_only |
| `src/metagit/core/mcp/tools/workspace_status.py` | metagit_workspace_status |
| `src/metagit/core/workspace/root_resolver.py` | resolve_sync_root |

## Entry Points

Start here when exploring this area:

- **`test_initialize_request_returns_capabilities`** (Function) — `tests/core/mcp/test_runtime.py:13`
- **`test_tools_list_returns_inactive_tools_without_config`** (Function) — `tests/core/mcp/test_runtime.py:25`
- **`test_tools_call_workspace_status_returns_text_payload`** (Function) — `tests/core/mcp/test_runtime.py:43`
- **`test_resources_read_ops_log_returns_json_content`** (Function) — `tests/core/mcp/test_runtime.py:60`
- **`test_tools_call_invalid_arguments_returns_mcp_invalid_params`** (Function) — `tests/core/mcp/test_runtime.py:76`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_initialize_request_returns_capabilities` | Function | `tests/core/mcp/test_runtime.py` | 13 |
| `test_tools_list_returns_inactive_tools_without_config` | Function | `tests/core/mcp/test_runtime.py` | 25 |
| `test_tools_call_workspace_status_returns_text_payload` | Function | `tests/core/mcp/test_runtime.py` | 43 |
| `test_resources_read_ops_log_returns_json_content` | Function | `tests/core/mcp/test_runtime.py` | 60 |
| `test_tools_call_invalid_arguments_returns_mcp_invalid_params` | Function | `tests/core/mcp/test_runtime.py` | 76 |
| `test_tools_call_workspace_semantic_search_requires_query` | Function | `tests/core/mcp/test_runtime.py` | 93 |
| `test_initialize_can_enable_sampling_capability` | Function | `tests/core/mcp/test_runtime.py` | 126 |
| `test_bootstrap_uses_sampling_when_client_supports_it` | Function | `tests/core/mcp/test_runtime.py` | 142 |
| `test_tools_call_workspace_grep_info_returns_backend` | Function | `tests/core/mcp/test_runtime.py` | 190 |
| `test_tools_call_version_check_returns_structured_payload` | Function | `tests/core/mcp/test_runtime.py` | 221 |
| `test_tools_call_version_upgrade_dry_run_by_default` | Function | `tests/core/mcp/test_runtime.py` | 271 |
| `test_tools_list_includes_repo_search_for_active_workspace` | Function | `tests/core/mcp/test_runtime.py` | 309 |
| `test_tools_call_repo_search_returns_matches` | Function | `tests/core/mcp/test_runtime.py` | 334 |
| `test_tools_list_includes_project_context_tools` | Function | `tests/core/mcp/test_runtime.py` | 370 |
| `test_tools_call_project_context_switch_unknown_project` | Function | `tests/core/mcp/test_runtime.py` | 396 |
| `test_tools_call_cross_project_dependencies` | Function | `tests/core/mcp/test_runtime.py` | 430 |
| `test_tools_list_includes_context_pack_tools_when_active` | Function | `tests/core/mcp/test_runtime.py` | 479 |
| `test_tools_call_metagit_context_pack_tier_zero_succeeds` | Function | `tests/core/mcp/test_runtime.py` | 505 |
| `test_tools_call_metagit_context_pack_invalid_args_returns_invalid_arguments` | Function | `tests/core/mcp/test_runtime.py` | 550 |
| `test_tools_call_metagit_objective_list` | Function | `tests/core/mcp/test_runtime.py` | 600 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Pack_cmd → Resolve_sync_root` | cross_community | 3 |
| `Repomix_cmd → Resolve_sync_root` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Context | 6 calls |
| Services | 3 calls |
| Tests | 3 calls |
| Commands | 3 calls |
| Agent | 2 calls |

## How to Explore

1. `gitnexus_context({name: "test_initialize_request_returns_capabilities"})` — see callers and callees
2. `gitnexus_query({query: "mcp"})` — find related execution flows
3. Read key files listed above for implementation details
