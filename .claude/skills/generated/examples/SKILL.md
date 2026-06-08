---
name: examples
description: "Skill for the Examples area of metagit-cli. 109 symbols across 32 files."
metadata:
  internal: true
---
# Examples

109 symbols | 32 files | Cohesion: 80%

## When to Use

- Working with code in `examples/`
- Understanding how demonstrate_datetime_serialization_fix, demonstrate_record_creation, main work
- Modifying examples-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `examples/fuzzyfinder_custom_colors_demo.py` | test_fuzzyfindertarget_with_colors, test_mixed_object_types, test_priority_demonstration, test_string_items_with_colors, test_object_items_with_colors (+4) |
| `examples/detection_manager_example.py` | example_remote_repository_analysis, example_local_repository_analysis, example_metagit_record_integration, example_output_formats, example_specific_analysis_methods (+3) |
| `examples/provider_example.py` | analyze_remote_repo, setup_providers_from_appconfig, setup_providers_from_environment, setup_providers_manually, analyze_local_repo (+2) |
| `examples/test_record_manager_simple.py` | test_basic_functionality, store_record, get_record, list_records, test_error_handling (+1) |
| `src/metagit/core/record/manager.py` | create_record_from_config, _get_git_info, store_record, get_record, list_records (+1) |
| `examples/detection_manager_config_example.py` | example_basic_usage, example_specific_method, example_metagit_record_integration, example_custom_config, example_preset_configs (+1) |
| `src/metagit/core/gitcache/manager.py` | get_cached_repository, list_cache_entries, refresh_cache_entry, refresh_cache_entry_async, get_cache_stats |
| `examples/repository_analysis_example.py` | example_configuration, example_local_repository_analysis, example_remote_repository_analysis, example_specific_analysis, main |
| `examples/record_manager_example.py` | example_local_file_storage, example_opensearch_storage, example_file_operations, main |
| `src/metagit/core/detect/manager.py` | from_url, _load_existing_config, from_path, summary |

## Entry Points

Start here when exploring this area:

- **`demonstrate_datetime_serialization_fix`** (Function) — `examples/datetime_serialization_fix_example.py:19`
- **`demonstrate_record_creation`** (Function) — `examples/datetime_serialization_fix_example.py:66`
- **`main`** (Function) — `examples/datetime_serialization_fix_example.py:160`
- **`example_local_file_storage`** (Function) — `examples/record_manager_example.py:23`
- **`example_opensearch_storage`** (Function) — `examples/record_manager_example.py:105`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `demonstrate_datetime_serialization_fix` | Function | `examples/datetime_serialization_fix_example.py` | 19 |
| `demonstrate_record_creation` | Function | `examples/datetime_serialization_fix_example.py` | 66 |
| `main` | Function | `examples/datetime_serialization_fix_example.py` | 160 |
| `example_local_file_storage` | Function | `examples/record_manager_example.py` | 23 |
| `example_opensearch_storage` | Function | `examples/record_manager_example.py` | 105 |
| `example_file_operations` | Function | `examples/record_manager_example.py` | 180 |
| `main` | Function | `examples/record_manager_example.py` | 235 |
| `test_basic_functionality` | Function | `examples/test_record_manager_simple.py` | 16 |
| `store_record` | Function | `examples/test_record_manager_simple.py` | 64 |
| `get_record` | Function | `examples/test_record_manager_simple.py` | 74 |
| `list_records` | Function | `examples/test_record_manager_simple.py` | 94 |
| `test_error_handling` | Function | `examples/test_record_manager_simple.py` | 116 |
| `test_no_backend` | Function | `examples/test_record_manager_simple.py` | 124 |
| `config_create` | Function | `src/metagit/cli/commands/config.py` | 125 |
| `create_metagit_config` | Function | `src/metagit/core/config/manager.py` | 183 |
| `main` | Function | `examples/enhanced_fuzzyfinder_demo.py` | 17 |
| `create_sample_files` | Function | `examples/fuzzyfinder_comprehensive_test.py` | 49 |
| `run_fuzzyfinder_test` | Function | `examples/fuzzyfinder_comprehensive_test.py` | 175 |
| `main` | Function | `examples/fuzzyfinder_comprehensive_test.py` | 201 |
| `test_fuzzyfindertarget_with_colors` | Function | `examples/fuzzyfinder_custom_colors_demo.py` | 22 |

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
| Commands | 11 calls |
| Gitcache | 11 calls |
| Tests | 1 calls |
| Detect | 1 calls |
| Config | 1 calls |
| Cluster_385 | 1 calls |
| Providers | 1 calls |

## How to Explore

1. `gitnexus_context({name: "demonstrate_datetime_serialization_fix"})` — see callers and callees
2. `gitnexus_query({query: "examples"})` — find related execution flows
3. Read key files listed above for implementation details
