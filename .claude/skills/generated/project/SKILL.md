---
name: project
description: "Skill for the Project area of metagit-cli. 58 symbols across 13 files."
metadata:
  internal: true
---
# Project

58 symbols | 13 files | Cohesion: 82%

## When to Use

- Working with code in `src/`
- Understanding how source_sync, merge_repo_tags, topics_to_tags work
- Modifying project-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/project/source_sync.py` | plan, apply_plan, _to_project_path, _find_existing_by_repo_id, _needs_update (+5) |
| `src/metagit/core/project/manager.py` | _sync_repo, _sync_repo_deduped, _sync_local_canonical, _sync_remote_canonical, _sync_local (+5) |
| `tests/core/project/test_repo_promote_service.py` | _write_manifest, _init_local_git_repo, _load_config, test_resolve_git_remote_url_reads_origin, test_promote_dry_run_reports_plan (+2) |
| `tests/test_project_source_sync.py` | _service, test_plan_additive_adds_missing_repo, test_plan_reconcile_removes_unmatched_provider_managed_repo, test_apply_plan_reconcile_preserves_protected_repo, test_plan_ensure_skips_metadata_update (+1) |
| `src/metagit/core/project/source_enrichment.py` | merge_repo_tags, topics_to_tags, enrich_discovered_repos, _owner_repo_from_full_name, _provider_display_name |
| `src/metagit/core/project/search_service.py` | search, _to_match, _row_passes_filters, _sort_matches, _match_row |
| `tests/core/project/test_source_filters.py` | _repo, test_ignore_pattern_drops_match, test_include_pattern_allowlist, test_visibility_private_filter, test_ignore_language_filter |
| `tests/core/project/test_source_naming.py` | _repo, test_namespaced_collision_uses_parent_segment, test_short_strategy_uses_repo_name |
| `src/metagit/cli/commands/project_source.py` | _emit_json, source_sync |
| `src/metagit/core/project/source_filters.py` | _visibility_matches, apply_source_filters |

## Entry Points

Start here when exploring this area:

- **`source_sync`** (Function) — `src/metagit/cli/commands/project_source.py:131`
- **`merge_repo_tags`** (Function) — `src/metagit/core/project/source_enrichment.py:22`
- **`topics_to_tags`** (Function) — `src/metagit/core/project/source_enrichment.py:39`
- **`resolve_manifest_names`** (Function) — `src/metagit/core/project/source_naming.py:10`
- **`test_plan_additive_adds_missing_repo`** (Function) — `tests/test_project_source_sync.py:25`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `source_sync` | Function | `src/metagit/cli/commands/project_source.py` | 131 |
| `merge_repo_tags` | Function | `src/metagit/core/project/source_enrichment.py` | 22 |
| `topics_to_tags` | Function | `src/metagit/core/project/source_enrichment.py` | 39 |
| `resolve_manifest_names` | Function | `src/metagit/core/project/source_naming.py` | 10 |
| `test_plan_additive_adds_missing_repo` | Function | `tests/test_project_source_sync.py` | 25 |
| `test_plan_reconcile_removes_unmatched_provider_managed_repo` | Function | `tests/test_project_source_sync.py` | 44 |
| `test_apply_plan_reconcile_preserves_protected_repo` | Function | `tests/test_project_source_sync.py` | 74 |
| `test_plan_ensure_skips_metadata_update` | Function | `tests/test_project_source_sync.py` | 99 |
| `test_plan_ensure_refresh_metadata_updates` | Function | `tests/test_project_source_sync.py` | 131 |
| `test_resolve_git_remote_url_reads_origin` | Function | `tests/core/project/test_repo_promote_service.py` | 70 |
| `test_promote_dry_run_reports_plan` | Function | `tests/core/project/test_repo_promote_service.py` | 82 |
| `test_promote_updates_manifest_and_clones` | Function | `tests/core/project/test_repo_promote_service.py` | 115 |
| `test_promote_rejects_non_local_entry` | Function | `tests/core/project/test_repo_promote_service.py` | 173 |
| `enrich_discovered_repos` | Function | `src/metagit/core/project/source_enrichment.py` | 49 |
| `apply_source_filters` | Function | `src/metagit/core/project/source_filters.py` | 24 |
| `test_ignore_pattern_drops_match` | Function | `tests/core/project/test_source_filters.py` | 30 |
| `test_include_pattern_allowlist` | Function | `tests/core/project/test_source_filters.py` | 41 |
| `test_visibility_private_filter` | Function | `tests/core/project/test_source_filters.py` | 53 |
| `test_ignore_language_filter` | Function | `tests/core/project/test_source_filters.py` | 65 |
| `test_namespaced_collision_uses_parent_segment` | Function | `tests/core/project/test_source_naming.py` | 19 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Source_sync → Clear` | cross_community | 4 |
| `Source_sync → Register` | cross_community | 4 |
| `Source_sync → _visibility_matches` | cross_community | 4 |
| `Source_sync → Topics_to_tags` | intra_community | 4 |
| `Source_sync → Normalize_git_url` | cross_community | 4 |
| `Search → _row_passes_filters` | cross_community | 4 |
| `Search → _match_row` | cross_community | 4 |
| `Search → _to_match` | cross_community | 4 |
| `Search → _sort_matches` | cross_community | 4 |
| `Source_sync → _discover_github` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_389 | 9 calls |
| Commands | 7 calls |
| Workspace | 4 calls |
| Cli | 3 calls |
| Providers | 2 calls |
| Examples | 1 calls |

## How to Explore

1. `gitnexus_context({name: "source_sync"})` — see callers and callees
2. `gitnexus_query({query: "project"})` — find related execution flows
3. Read key files listed above for implementation details
