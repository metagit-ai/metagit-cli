---
name: examples
description: "Skill for the Examples area of metagit-cli. 90 symbols across 26 files."
---

# Examples

90 symbols | 26 files | Cohesion: 94%

## When to Use

- Working with code in `examples/`
- Understanding how test_create_record_from_config_manager, test_store_record_without_backend, test_get_record_without_backend work
- Modifying examples-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `examples/fuzzyfinder_custom_colors_demo.py` | test_fuzzyfindertarget_with_colors, test_mixed_object_types, test_priority_demonstration, test_string_items_with_colors, test_object_items_with_colors (+4) |
| `src/metagit/core/record/manager.py` | create_record_from_config, _get_git_info, store_record, get_record, search_records (+3) |
| `examples/test_record_manager_simple.py` | test_basic_functionality, store_record, get_record, search_records, list_records (+2) |
| `examples/detection_manager_example.py` | example_local_repository_analysis, example_configuration_options, example_metagit_record_integration, example_output_formats, example_specific_analysis_methods (+2) |
| `examples/provider_example.py` | setup_providers_from_appconfig, setup_providers_from_environment, setup_providers_manually, analyze_local_repo, demonstrate_configuration_methods (+1) |
| `examples/repository_analysis_example.py` | example_local_repository_analysis, example_remote_repository_analysis, example_specific_analysis, example_configuration, main |
| `examples/gitcache_example.py` | create_sample_local_directory, sync_example, async_example, cleanup_example, main |
| `examples/record_manager_example.py` | example_local_file_storage, example_opensearch_storage, example_file_operations, main |
| `src/metagit/cli/commands/record.py` | record_create, store_record, search_records, record_import |
| `tests/test_record_manager.py` | test_create_record_from_config_manager, test_store_record_without_backend, test_get_record_without_backend |

## Entry Points

Start here when exploring this area:

- **`test_create_record_from_config_manager`** (Function) — `tests/test_record_manager.py:356`
- **`test_store_record_without_backend`** (Function) — `tests/test_record_manager.py:406`
- **`test_get_record_without_backend`** (Function) — `tests/test_record_manager.py:436`
- **`test_basic_functionality`** (Function) — `examples/test_record_manager_simple.py:16`
- **`store_record`** (Function) — `examples/test_record_manager_simple.py:64`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_create_record_from_config_manager` | Function | `tests/test_record_manager.py` | 356 |
| `test_store_record_without_backend` | Function | `tests/test_record_manager.py` | 406 |
| `test_get_record_without_backend` | Function | `tests/test_record_manager.py` | 436 |
| `test_basic_functionality` | Function | `examples/test_record_manager_simple.py` | 16 |
| `store_record` | Function | `examples/test_record_manager_simple.py` | 64 |
| `get_record` | Function | `examples/test_record_manager_simple.py` | 74 |
| `search_records` | Function | `examples/test_record_manager_simple.py` | 84 |
| `list_records` | Function | `examples/test_record_manager_simple.py` | 94 |
| `test_error_handling` | Function | `examples/test_record_manager_simple.py` | 116 |
| `test_no_backend` | Function | `examples/test_record_manager_simple.py` | 124 |
| `example_local_file_storage` | Function | `examples/record_manager_example.py` | 23 |
| `example_opensearch_storage` | Function | `examples/record_manager_example.py` | 105 |
| `example_file_operations` | Function | `examples/record_manager_example.py` | 180 |
| `main` | Function | `examples/record_manager_example.py` | 235 |
| `demonstrate_datetime_serialization_fix` | Function | `examples/datetime_serialization_fix_example.py` | 19 |
| `demonstrate_record_creation` | Function | `examples/datetime_serialization_fix_example.py` | 66 |
| `main` | Function | `examples/datetime_serialization_fix_example.py` | 160 |
| `create_record_from_config` | Function | `src/metagit/core/record/manager.py` | 381 |
| `store_record` | Function | `src/metagit/core/record/manager.py` | 456 |
| `get_record` | Function | `src/metagit/core/record/manager.py` | 471 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → _get_git_info` | intra_community | 4 |
| `Main → Run` | intra_community | 3 |
| `Record_create → Store_record` | intra_community | 3 |
| `Record_create → _get_git_info` | intra_community | 3 |
| `Record_update → Get_record` | cross_community | 3 |
| `Main → Get_enabled_methods` | cross_community | 3 |
| `Record_show → Get_record` | cross_community | 3 |
| `Record_show → List_records` | cross_community | 3 |
| `Record_delete → Get_record` | cross_community | 3 |
| `Record_export → Get_record` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 3 calls |
| Config | 2 calls |
| Cli | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_create_record_from_config_manager"})` — see callers and callees
2. `gitnexus_query({query: "examples"})` — find related execution flows
3. Read key files listed above for implementation details
