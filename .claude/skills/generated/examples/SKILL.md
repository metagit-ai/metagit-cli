---
name: examples
description: "Skill for the Examples area of metagit-cli. 81 symbols across 24 files."
metadata:
  internal: true
---
# Examples

81 symbols | 24 files | Cohesion: 79%

## When to Use

- Working with code in `examples/`
- Understanding how main, create_sample_files, run_fuzzyfinder_test work
- Modifying examples-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `examples/fuzzyfinder_custom_colors_demo.py` | test_fuzzyfindertarget_with_colors, test_mixed_object_types, test_priority_demonstration, test_string_items_with_colors, test_object_items_with_colors (+4) |
| `examples/detection_manager_example.py` | example_local_repository_analysis, example_metagit_record_integration, example_output_formats, example_specific_analysis_methods, example_repository_analysis_access (+3) |
| `examples/provider_example.py` | analyze_remote_repo, setup_providers_from_appconfig, setup_providers_from_environment, setup_providers_manually, analyze_local_repo (+2) |
| `examples/detection_manager_config_example.py` | example_basic_usage, example_specific_method, example_metagit_record_integration, example_custom_config, example_preset_configs (+1) |
| `src/metagit/core/gitcache/manager.py` | get_cached_repository, list_cache_entries, refresh_cache_entry, refresh_cache_entry_async, get_cache_stats |
| `examples/repository_analysis_example.py` | example_configuration, example_local_repository_analysis, example_remote_repository_analysis, example_specific_analysis, main |
| `examples/gitcache_example.py` | create_sample_local_directory, sync_example, async_example, main |
| `src/metagit/cli/commands/gitcache.py` | list, refresh, path, stats |
| `src/metagit/core/detect/manager.py` | from_path, from_url, _load_existing_config, summary |
| `examples/fuzzyfinder_comprehensive_test.py` | create_sample_files, run_fuzzyfinder_test, main |

## Entry Points

Start here when exploring this area:

- **`main`** (Function) — `examples/enhanced_fuzzyfinder_demo.py:17`
- **`create_sample_files`** (Function) — `examples/fuzzyfinder_comprehensive_test.py:49`
- **`run_fuzzyfinder_test`** (Function) — `examples/fuzzyfinder_comprehensive_test.py:175`
- **`main`** (Function) — `examples/fuzzyfinder_comprehensive_test.py:201`
- **`test_fuzzyfindertarget_with_colors`** (Function) — `examples/fuzzyfinder_custom_colors_demo.py:22`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `main` | Function | `examples/enhanced_fuzzyfinder_demo.py` | 17 |
| `create_sample_files` | Function | `examples/fuzzyfinder_comprehensive_test.py` | 49 |
| `run_fuzzyfinder_test` | Function | `examples/fuzzyfinder_comprehensive_test.py` | 175 |
| `main` | Function | `examples/fuzzyfinder_comprehensive_test.py` | 201 |
| `test_fuzzyfindertarget_with_colors` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 22 |
| `test_mixed_object_types` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 105 |
| `test_priority_demonstration` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 172 |
| `test_string_items_with_colors` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 232 |
| `test_object_items_with_colors` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 286 |
| `test_mixed_color_formats` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 347 |
| `test_preview_with_colors` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 391 |
| `test_fuzzyfindertarget_with_preview` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 461 |
| `main` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 529 |
| `main` | Function | `examples/fuzzyfinder_debug_test.py` | 16 |
| `create_sample_project_files` | Function | `examples/fuzzyfinder_preview_test.py` | 34 |
| `main` | Function | `examples/fuzzyfinder_preview_test.py` | 156 |
| `main` | Function | `examples/fuzzyfinder_simple_colors.py` | 15 |
| `create_sample_strings` | Function | `examples/fuzzyfinder_simple_test.py` | 17 |
| `main` | Function | `examples/fuzzyfinder_simple_test.py` | 57 |
| `create_sample_local_directory` | Function | `examples/gitcache_example.py` | 15 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → _override_from_environment` | cross_community | 5 |
| `Main → Normalize_git_url` | cross_community | 4 |
| `Main → _is_git_repository` | cross_community | 4 |
| `Main → _get_repository_info` | cross_community | 4 |
| `Main → _get_remote_info` | cross_community | 4 |
| `Main → Debug` | cross_community | 4 |
| `Main → _load_existing_config` | cross_community | 4 |
| `Main → Set_logger` | cross_community | 4 |
| `Sync_example → Normalize_git_url` | cross_community | 4 |
| `Sync_example → _is_git_repository` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Gitcache | 11 calls |
| Cli | 3 calls |
| Tests | 1 calls |
| Detect | 1 calls |
| Commands | 1 calls |
| Providers | 1 calls |

## How to Explore

1. `gitnexus_context({name: "main"})` — see callers and callees
2. `gitnexus_query({query: "examples"})` — find related execution flows
3. Read key files listed above for implementation details
