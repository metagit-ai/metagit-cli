---
name: providers
description: "Skill for the Providers area of metagit-cli. 16 symbols across 4 files."
metadata:
  internal: true
---
# Providers

16 symbols | 4 files | Cohesion: 100%

## When to Use

- Working with code in `src/`
- Understanding how register, clear, configure_from_app_config work
- Modifying providers-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/providers/__init__.py` | register, clear, configure_from_app_config, configure_from_environment |
| `src/metagit/core/providers/gitlab.py` | GitLabProvider, __init__, get_repository_metrics, _calculate_commit_frequency |
| `src/metagit/core/providers/github.py` | GitHubProvider, __init__, get_repository_metrics, _calculate_commit_frequency |
| `src/metagit/core/providers/base.py` | GitProvider, __init__, can_handle_url, supports_url |

## Entry Points

Start here when exploring this area:

- **`register`** (Function) — `src/metagit/core/providers/__init__.py:24`
- **`clear`** (Function) — `src/metagit/core/providers/__init__.py:32`
- **`configure_from_app_config`** (Function) — `src/metagit/core/providers/__init__.py:57`
- **`configure_from_environment`** (Function) — `src/metagit/core/providers/__init__.py:97`
- **`get_repository_metrics`** (Function) — `src/metagit/core/providers/gitlab.py:72`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `GitLabProvider` | Class | `src/metagit/core/providers/gitlab.py` | 19 |
| `GitHubProvider` | Class | `src/metagit/core/providers/github.py` | 19 |
| `GitProvider` | Class | `src/metagit/core/providers/base.py` | 15 |
| `register` | Function | `src/metagit/core/providers/__init__.py` | 24 |
| `clear` | Function | `src/metagit/core/providers/__init__.py` | 32 |
| `configure_from_app_config` | Function | `src/metagit/core/providers/__init__.py` | 57 |
| `configure_from_environment` | Function | `src/metagit/core/providers/__init__.py` | 97 |
| `get_repository_metrics` | Function | `src/metagit/core/providers/gitlab.py` | 72 |
| `get_repository_metrics` | Function | `src/metagit/core/providers/github.py` | 72 |
| `can_handle_url` | Function | `src/metagit/core/providers/base.py` | 36 |
| `supports_url` | Function | `src/metagit/core/providers/base.py` | 82 |
| `__init__` | Function | `src/metagit/core/providers/gitlab.py` | 22 |
| `__init__` | Function | `src/metagit/core/providers/github.py` | 22 |
| `__init__` | Function | `src/metagit/core/providers/base.py` | 18 |
| `_calculate_commit_frequency` | Function | `src/metagit/core/providers/gitlab.py` | 183 |
| `_calculate_commit_frequency` | Function | `src/metagit/core/providers/github.py` | 190 |

## How to Explore

1. `gitnexus_context({name: "register"})` — see callers and callees
2. `gitnexus_query({query: "providers"})` — find related execution flows
3. Read key files listed above for implementation details
