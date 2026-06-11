---
name: providers
description: "Skill for the Providers area of metagit-cli. 27 symbols across 9 files."
metadata:
  internal: true
---
# Providers

27 symbols | 9 files | Cohesion: 83%

## When to Use

- Working with code in `src/`
- Understanding how detect_repository, evaluate_existing_manifest, manifest_gate_error_message work
- Modifying providers-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/providers/__init__.py` | register, clear, get_all_providers, configure_from_app_config, configure_from_environment (+1) |
| `src/metagit/core/providers/github.py` | extract_repo_info, GitHubProvider, __init__, get_repository_metrics, _calculate_commit_frequency |
| `src/metagit/core/providers/gitlab.py` | extract_repo_info, GitLabProvider, __init__, get_repository_metrics, _calculate_commit_frequency |
| `src/metagit/core/providers/base.py` | can_handle_url, supports_url, GitProvider, __init__ |
| `src/metagit/core/config/manifest_gate.py` | evaluate_existing_manifest, manifest_gate_error_message |
| `src/metagit/core/gitcache/manager.py` | _get_provider_for_url, _generate_cache_name |
| `src/metagit/cli/commands/detect.py` | detect_repository |
| `src/metagit/core/init/service.py` | _resolve_existing_manifest |
| `src/metagit/core/utils/common.py` | normalize_git_url |

## Entry Points

Start here when exploring this area:

- **`detect_repository`** (Function) — `src/metagit/cli/commands/detect.py:290`
- **`evaluate_existing_manifest`** (Function) — `src/metagit/core/config/manifest_gate.py:33`
- **`manifest_gate_error_message`** (Function) — `src/metagit/core/config/manifest_gate.py:58`
- **`normalize_git_url`** (Function) — `src/metagit/core/utils/common.py:279`
- **`GitProvider`** (Class) — `src/metagit/core/providers/base.py:15`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `GitProvider` | Class | `src/metagit/core/providers/base.py` | 15 |
| `GitHubProvider` | Class | `src/metagit/core/providers/github.py` | 19 |
| `GitLabProvider` | Class | `src/metagit/core/providers/gitlab.py` | 19 |
| `detect_repository` | Function | `src/metagit/cli/commands/detect.py` | 290 |
| `evaluate_existing_manifest` | Function | `src/metagit/core/config/manifest_gate.py` | 33 |
| `manifest_gate_error_message` | Function | `src/metagit/core/config/manifest_gate.py` | 58 |
| `normalize_git_url` | Function | `src/metagit/core/utils/common.py` | 279 |
| `register` | Method | `src/metagit/core/providers/__init__.py` | 24 |
| `clear` | Method | `src/metagit/core/providers/__init__.py` | 32 |
| `get_all_providers` | Method | `src/metagit/core/providers/__init__.py` | 46 |
| `configure_from_app_config` | Method | `src/metagit/core/providers/__init__.py` | 57 |
| `configure_from_environment` | Method | `src/metagit/core/providers/__init__.py` | 97 |
| `get_provider_for_url` | Method | `src/metagit/core/providers/__init__.py` | 36 |
| `can_handle_url` | Method | `src/metagit/core/providers/base.py` | 36 |
| `supports_url` | Method | `src/metagit/core/providers/base.py` | 82 |
| `extract_repo_info` | Method | `src/metagit/core/providers/github.py` | 55 |
| `extract_repo_info` | Method | `src/metagit/core/providers/gitlab.py` | 55 |
| `get_repository_metrics` | Method | `src/metagit/core/providers/github.py` | 72 |
| `get_repository_metrics` | Method | `src/metagit/core/providers/gitlab.py` | 72 |
| `_resolve_existing_manifest` | Method | `src/metagit/core/init/service.py` | 55 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Init → Load_config` | cross_community | 5 |
| `Init → Manifest_gate_error_message` | cross_community | 4 |
| `Sync_project → Clear` | cross_community | 4 |
| `Sync_project → Register` | cross_community | 4 |
| `Sync_project → Normalize_git_url` | cross_community | 4 |
| `Main → Normalize_git_url` | cross_community | 4 |
| `Sync_example → Normalize_git_url` | cross_community | 4 |
| `Async_example → Normalize_git_url` | cross_community | 4 |
| `Detect_repository → Clear` | intra_community | 3 |
| `Detect_repository → Register` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Examples | 3 calls |
| Config | 1 calls |

## How to Explore

1. `gitnexus_context({name: "detect_repository"})` — see callers and callees
2. `gitnexus_query({query: "providers"})` — find related execution flows
3. Read key files listed above for implementation details
