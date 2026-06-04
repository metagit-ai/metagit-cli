---
name: gitcache
description: "Skill for the Gitcache area of metagit-cli. 32 symbols across 5 files."
---

# Gitcache

32 symbols | 5 files | Cohesion: 78%

## When to Use

- Working with code in `src/`
- Understanding how cache, details, cache_repository_async work
- Modifying gitcache-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/gitcache/manager.py` | _is_git_url, _clone_repository_async, _copy_local_directory_async, _pull_updates_async, _calculate_directory_size (+12) |
| `src/metagit/core/gitcache/config.py` | add_entry, remove_entry, get_entry, list_entries, get_cache_size_bytes (+4) |
| `tests/test_gitcache.py` | test_git_cache_config_entry_management, test_git_cache_config_get_cache_path, test_git_cache_config_stale_detection |
| `src/metagit/cli/commands/gitcache.py` | cache, details |
| `src/metagit/core/providers/base.py` | get_name |

## Entry Points

Start here when exploring this area:

- **`cache`** (Function) — `src/metagit/cli/commands/gitcache.py:31`
- **`details`** (Function) — `src/metagit/cli/commands/gitcache.py:248`
- **`cache_repository_async`** (Method) — `src/metagit/core/gitcache/manager.py:425`
- **`cache_repository`** (Method) — `src/metagit/core/gitcache/manager.py:296`
- **`get_cache_entry_details`** (Method) — `src/metagit/core/gitcache/manager.py:897`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `cache` | Function | `src/metagit/cli/commands/gitcache.py` | 31 |
| `details` | Function | `src/metagit/cli/commands/gitcache.py` | 248 |
| `cache_repository_async` | Method | `src/metagit/core/gitcache/manager.py` | 425 |
| `cache_repository` | Method | `src/metagit/core/gitcache/manager.py` | 296 |
| `get_cache_entry_details` | Method | `src/metagit/core/gitcache/manager.py` | 897 |
| `add_entry` | Method | `src/metagit/core/gitcache/config.py` | 178 |
| `remove_entry` | Method | `src/metagit/core/gitcache/config.py` | 182 |
| `get_entry` | Method | `src/metagit/core/gitcache/config.py` | 189 |
| `list_entries` | Method | `src/metagit/core/gitcache/config.py` | 193 |
| `test_git_cache_config_entry_management` | Method | `tests/test_gitcache.py` | 145 |
| `get_cache_size_bytes` | Method | `src/metagit/core/gitcache/config.py` | 155 |
| `get_cache_size_gb` | Method | `src/metagit/core/gitcache/config.py` | 170 |
| `is_cache_full` | Method | `src/metagit/core/gitcache/config.py` | 174 |
| `get_cache_path` | Method | `src/metagit/core/gitcache/config.py` | 146 |
| `test_git_cache_config_get_cache_path` | Method | `tests/test_gitcache.py` | 138 |
| `is_entry_stale` | Method | `src/metagit/core/gitcache/config.py` | 150 |
| `test_git_cache_config_stale_detection` | Method | `tests/test_gitcache.py` | 179 |
| `register_provider` | Method | `src/metagit/core/gitcache/manager.py` | 42 |
| `get_name` | Method | `src/metagit/core/providers/base.py` | 31 |
| `_is_git_url` | Method | `src/metagit/core/gitcache/manager.py` | 93 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Normalize_git_url` | cross_community | 4 |
| `Main → _is_git_repository` | cross_community | 4 |
| `Main → _get_repository_info` | cross_community | 4 |
| `Main → _get_remote_info` | cross_community | 4 |
| `Sync_example → Normalize_git_url` | cross_community | 4 |
| `Sync_example → _is_git_repository` | cross_community | 4 |
| `Sync_example → _get_repository_info` | cross_community | 4 |
| `Sync_example → _get_remote_info` | cross_community | 4 |
| `Async_example → Normalize_git_url` | cross_community | 4 |
| `Async_example → _is_git_repository` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Providers | 2 calls |

## How to Explore

1. `gitnexus_context({name: "cache"})` — see callers and callees
2. `gitnexus_query({query: "gitcache"})` — find related execution flows
3. Read key files listed above for implementation details
