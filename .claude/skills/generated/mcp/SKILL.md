---
name: mcp
description: "Skill for the Mcp area of metagit-cli. 19 symbols across 12 files."
---

# Mcp

19 symbols | 12 files | Cohesion: 87%

## When to Use

- Working with code in `tests/`
- Understanding how fetchWorkspaceGrep, getWorkspaceGrep, test_workspace_resources_available_when_active work
- Modifying mcp-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/core/mcp/test_gate.py` | test_missing_root_is_inactive_missing, test_missing_config_file_is_inactive_missing, test_invalid_config_file_is_inactive_invalid, test_valid_config_file_is_active |
| `tests/core/mcp/test_root_resolver.py` | test_env_root_has_highest_precedence, test_cli_root_used_when_env_unset, test_walk_up_finds_workspace_root |
| `src/metagit/core/mcp/root_resolver.py` | resolve, _walk_for_config |
| `tests/core/mcp/test_tool_registry.py` | test_inactive_registry_exposes_only_safe_tools, test_active_registry_exposes_full_toolset |
| `web/src/pages/grepQueries.ts` | fetchWorkspaceGrep |
| `web/src/api/client.ts` | getWorkspaceGrep |
| `tests/core/mcp/test_resources.py` | test_workspace_resources_available_when_active |
| `src/metagit/core/mcp/resources.py` | get_resource |
| `src/metagit/core/mcp/services/ops_log.py` | append |
| `src/metagit/data/web/assets/index-C6eUwfs-.js` | Qi |

## Entry Points

Start here when exploring this area:

- **`fetchWorkspaceGrep`** (Function) — `web/src/pages/grepQueries.ts:22`
- **`getWorkspaceGrep`** (Function) — `web/src/api/client.ts:346`
- **`test_workspace_resources_available_when_active`** (Function) — `tests/core/mcp/test_resources.py:10`
- **`get_resource`** (Function) — `src/metagit/core/mcp/resources.py:18`
- **`append`** (Function) — `src/metagit/core/mcp/services/ops_log.py:15`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `fetchWorkspaceGrep` | Function | `web/src/pages/grepQueries.ts` | 22 |
| `getWorkspaceGrep` | Function | `web/src/api/client.ts` | 346 |
| `test_workspace_resources_available_when_active` | Function | `tests/core/mcp/test_resources.py` | 10 |
| `get_resource` | Function | `src/metagit/core/mcp/resources.py` | 18 |
| `append` | Function | `src/metagit/core/mcp/services/ops_log.py` | 15 |
| `test_env_root_has_highest_precedence` | Function | `tests/core/mcp/test_root_resolver.py` | 10 |
| `test_cli_root_used_when_env_unset` | Function | `tests/core/mcp/test_root_resolver.py` | 21 |
| `test_walk_up_finds_workspace_root` | Function | `tests/core/mcp/test_root_resolver.py` | 32 |
| `resolve` | Function | `src/metagit/core/mcp/root_resolver.py` | 16 |
| `test_missing_root_is_inactive_missing` | Function | `tests/core/mcp/test_gate.py` | 11 |
| `test_missing_config_file_is_inactive_missing` | Function | `tests/core/mcp/test_gate.py` | 19 |
| `test_invalid_config_file_is_inactive_invalid` | Function | `tests/core/mcp/test_gate.py` | 27 |
| `test_valid_config_file_is_active` | Function | `tests/core/mcp/test_gate.py` | 37 |
| `evaluate` | Function | `src/metagit/core/mcp/gate.py` | 18 |
| `test_inactive_registry_exposes_only_safe_tools` | Function | `tests/core/mcp/test_tool_registry.py` | 9 |
| `test_active_registry_exposes_full_toolset` | Function | `tests/core/mcp/test_tool_registry.py` | 25 |
| `list_tools` | Function | `src/metagit/core/mcp/tool_registry.py` | 55 |
| `Qi` | Function | `src/metagit/data/web/assets/index-C6eUwfs-.js` | 10 |
| `_walk_for_config` | Function | `src/metagit/core/mcp/root_resolver.py` | 27 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `WorkspacePage → Append` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Pages | 1 calls |
| Config | 1 calls |

## How to Explore

1. `gitnexus_context({name: "fetchWorkspaceGrep"})` — see callers and callees
2. `gitnexus_query({query: "mcp"})` — find related execution flows
3. Read key files listed above for implementation details
