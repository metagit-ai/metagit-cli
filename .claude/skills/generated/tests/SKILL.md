---
name: tests
description: "Skill for the Tests area of metagit-cli. 37 symbols across 15 files."
---

# Tests

37 symbols | 15 files | Cohesion: 85%

## When to Use

- Working with code in `tests/`
- Understanding how test_render_yaml_includes_header_and_workspace, test_build_merges_overrides, test_generated_payload_validates_when_overrides_used work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/utils/fuzzyfinder.py` | on_mount, on_input_changed, _perform_search, _update_results_meta, _search |
| `tests/test_project_search_service.py` | _config, test_search_prioritizes_exact_repo_name, test_search_can_filter_by_tag, test_search_filters_by_status_and_has_url, test_search_sorts_by_project_name |
| `tests/test_project_manager_prune.py` | _config_one_repo, test_list_unmanaged_sync_directories_excludes_managed, test_list_unmanaged_respects_dot_directories_when_ignore_hidden, test_select_repo_skips_dot_directories_when_ignore_hidden |
| `tests/test_project_manager_select_repo.py` | _build_metagit_config, test_select_repo_respects_gitignore_and_sets_total_count, test_select_repo_preview_contains_extended_metadata, test_select_repo_missing_project_returns_value_error |
| `tests/test_config_example_generator.py` | test_render_yaml_includes_header_and_workspace, test_build_merges_overrides, test_generated_payload_validates_when_overrides_used |
| `src/metagit/core/config/example_generator.py` | deep_merge, build, render_yaml |
| `tests/test_gitcache.py` | test_git_cache_config_get_cache_path, test_git_cache_config_stale_detection |
| `src/metagit/core/gitcache/config.py` | get_cache_path, is_entry_stale |
| `tests/test_documentation_graph_models.py` | test_documentation_accepts_strings_and_dicts, test_graph_relationships_and_export |
| `src/metagit/core/config/models.py` | documentation_graph_nodes, graph_export_payload |

## Entry Points

Start here when exploring this area:

- **`test_render_yaml_includes_header_and_workspace`** (Function) — `tests/test_config_example_generator.py:10`
- **`test_build_merges_overrides`** (Function) — `tests/test_config_example_generator.py:18`
- **`test_generated_payload_validates_when_overrides_used`** (Function) — `tests/test_config_example_generator.py:25`
- **`deep_merge`** (Function) — `src/metagit/core/config/example_generator.py:32`
- **`build`** (Function) — `src/metagit/core/config/example_generator.py:49`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_render_yaml_includes_header_and_workspace` | Function | `tests/test_config_example_generator.py` | 10 |
| `test_build_merges_overrides` | Function | `tests/test_config_example_generator.py` | 18 |
| `test_generated_payload_validates_when_overrides_used` | Function | `tests/test_config_example_generator.py` | 25 |
| `deep_merge` | Function | `src/metagit/core/config/example_generator.py` | 32 |
| `build` | Function | `src/metagit/core/config/example_generator.py` | 49 |
| `render_yaml` | Function | `src/metagit/core/config/example_generator.py` | 56 |
| `config_example` | Function | `src/metagit/cli/commands/config.py` | 446 |
| `test_fuzzyfinder_app_search_not_capped_by_max_results` | Function | `tests/test_utils_fuzzyfinder.py` | 27 |
| `on_mount` | Function | `src/metagit/core/utils/fuzzyfinder.py` | 291 |
| `on_input_changed` | Function | `src/metagit/core/utils/fuzzyfinder.py` | 298 |
| `test_search_prioritizes_exact_repo_name` | Function | `tests/test_project_search_service.py` | 54 |
| `test_search_can_filter_by_tag` | Function | `tests/test_project_search_service.py` | 65 |
| `test_search_filters_by_status_and_has_url` | Function | `tests/test_project_search_service.py` | 76 |
| `test_search_sorts_by_project_name` | Function | `tests/test_project_search_service.py` | 99 |
| `test_list_unmanaged_sync_directories_excludes_managed` | Function | `tests/test_project_manager_prune.py` | 41 |
| `test_list_unmanaged_respects_dot_directories_when_ignore_hidden` | Function | `tests/test_project_manager_prune.py` | 55 |
| `test_select_repo_skips_dot_directories_when_ignore_hidden` | Function | `tests/test_project_manager_prune.py` | 77 |
| `list_unmanaged_sync_directories` | Function | `src/metagit/core/project/manager.py` | 545 |
| `test_select_repo_respects_gitignore_and_sets_total_count` | Function | `tests/test_project_manager_select_repo.py` | 55 |
| `test_select_repo_preview_contains_extended_metadata` | Function | `tests/test_project_manager_select_repo.py` | 85 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Project | 8 calls |
| Cluster_134 | 3 calls |
| Config | 2 calls |

## How to Explore

1. `gitnexus_context({name: "test_render_yaml_includes_header_and_workspace"})` — see callers and callees
2. `gitnexus_query({query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
