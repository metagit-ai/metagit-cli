---
name: mcp
description: "Skill for the Mcp area of metagit-cli. 13 symbols across 6 files."
---

# Mcp

13 symbols | 6 files | Cohesion: 96%

## When to Use

- Working with code in `tests/`
- Understanding how test_env_root_has_highest_precedence, test_cli_root_used_when_env_unset, test_walk_up_finds_workspace_root work
- Modifying mcp-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/core/mcp/test_gate.py` | test_missing_root_is_inactive_missing, test_missing_config_file_is_inactive_missing, test_invalid_config_file_is_inactive_invalid, test_valid_config_file_is_active |
| `tests/core/mcp/test_root_resolver.py` | test_env_root_has_highest_precedence, test_cli_root_used_when_env_unset, test_walk_up_finds_workspace_root |
| `src/metagit/core/mcp/root_resolver.py` | resolve, _walk_for_config |
| `tests/core/mcp/test_tool_registry.py` | test_inactive_registry_exposes_only_safe_tools, test_active_registry_exposes_full_toolset |
| `src/metagit/core/mcp/gate.py` | evaluate |
| `src/metagit/core/mcp/tool_registry.py` | list_tools |

## Entry Points

Start here when exploring this area:

- **`test_env_root_has_highest_precedence`** (Function) — `tests/core/mcp/test_root_resolver.py:10`
- **`test_cli_root_used_when_env_unset`** (Function) — `tests/core/mcp/test_root_resolver.py:21`
- **`test_walk_up_finds_workspace_root`** (Function) — `tests/core/mcp/test_root_resolver.py:32`
- **`resolve`** (Function) — `src/metagit/core/mcp/root_resolver.py:16`
- **`test_missing_root_is_inactive_missing`** (Function) — `tests/core/mcp/test_gate.py:11`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
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
| `list_tools` | Function | `src/metagit/core/mcp/tool_registry.py` | 54 |
| `_walk_for_config` | Function | `src/metagit/core/mcp/root_resolver.py` | 27 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_env_root_has_highest_precedence"})` — see callers and callees
2. `gitnexus_query({query: "mcp"})` — find related execution flows
3. Read key files listed above for implementation details
