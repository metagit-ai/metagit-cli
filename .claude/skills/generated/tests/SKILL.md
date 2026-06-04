---
name: tests
description: "Skill for the Tests area of metagit-cli. 40 symbols across 14 files."
---

# Tests

40 symbols | 14 files | Cohesion: 70%

## When to Use

- Working with code in `tests/`
- Understanding how test_prompt_for_model_project_path_url_only, test_prompt_for_model_validation_retry_drops_failed_fields, test_prompt_for_model_skips_decorative_output_without_console work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/test_record_conversion.py` | test_from_metagit_config_basic, test_from_metagit_config_with_custom_detection_data, test_conversion_round_trip, test_conversion_with_complex_nested_objects, test_conversion_with_minimal_data (+1) |
| `src/metagit/core/utils/fuzzyfinder.py` | on_mount, on_input_changed, _perform_search, _update_results_meta, _search |
| `tests/test_project_search_service.py` | _config, test_search_prioritizes_exact_repo_name, test_search_can_filter_by_tag, test_search_filters_by_status_and_has_url, test_search_sorts_by_project_name |
| `tests/test_utils_userprompt.py` | test_prompt_for_model_project_path_url_only, test_prompt_for_model_validation_retry_drops_failed_fields, test_prompt_for_model_skips_decorative_output_without_console, test_prompt_for_model_validation_retry_reprompts_failed_field |
| `tests/test_project_manager_prune.py` | _config_one_repo, test_list_unmanaged_sync_directories_excludes_managed, test_list_unmanaged_respects_dot_directories_when_ignore_hidden, test_select_repo_skips_dot_directories_when_ignore_hidden |
| `tests/test_project_manager_select_repo.py` | _build_metagit_config, test_select_repo_respects_gitignore_and_sets_total_count, test_select_repo_preview_contains_extended_metadata, test_select_repo_missing_project_returns_value_error |
| `src/metagit/core/utils/userprompt.py` | _default_for_unprompted_field, prompt_for_model, prompt_for_model_fields |
| `tests/test_appconfig_models.py` | test_appconfig_load_and_save, test_appconfig_load_file_not_found, test_appconfig_load_ignores_legacy_version_key |
| `src/metagit/core/record/models.py` | from_metagit_config |
| `examples/test_appconfig_env.py` | test_appconfig_env_loading |

## Entry Points

Start here when exploring this area:

- **`test_prompt_for_model_project_path_url_only`** (Function) — `tests/test_utils_userprompt.py:26`
- **`test_prompt_for_model_validation_retry_drops_failed_fields`** (Function) — `tests/test_utils_userprompt.py:55`
- **`test_prompt_for_model_skips_decorative_output_without_console`** (Function) — `tests/test_utils_userprompt.py:90`
- **`test_prompt_for_model_validation_retry_reprompts_failed_field`** (Function) — `tests/test_utils_userprompt.py:114`
- **`test_appconfig_env_loading`** (Function) — `examples/test_appconfig_env.py:12`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_prompt_for_model_project_path_url_only` | Function | `tests/test_utils_userprompt.py` | 26 |
| `test_prompt_for_model_validation_retry_drops_failed_fields` | Function | `tests/test_utils_userprompt.py` | 55 |
| `test_prompt_for_model_skips_decorative_output_without_console` | Function | `tests/test_utils_userprompt.py` | 90 |
| `test_prompt_for_model_validation_retry_reprompts_failed_field` | Function | `tests/test_utils_userprompt.py` | 114 |
| `test_appconfig_env_loading` | Function | `examples/test_appconfig_env.py` | 12 |
| `providers` | Function | `src/metagit/cli/commands/config.py` | 229 |
| `test_appconfig_load_and_save` | Function | `tests/test_appconfig_models.py` | 74 |
| `test_appconfig_load_file_not_found` | Function | `tests/test_appconfig_models.py` | 104 |
| `test_appconfig_load_ignores_legacy_version_key` | Function | `tests/test_appconfig_models.py` | 109 |
| `test_fuzzyfinder_app_search_not_capped_by_max_results` | Function | `tests/test_utils_fuzzyfinder.py` | 27 |
| `test_list_unmanaged_sync_directories_excludes_managed` | Function | `tests/test_project_manager_prune.py` | 41 |
| `test_list_unmanaged_respects_dot_directories_when_ignore_hidden` | Function | `tests/test_project_manager_prune.py` | 55 |
| `test_select_repo_skips_dot_directories_when_ignore_hidden` | Function | `tests/test_project_manager_prune.py` | 77 |
| `test_search_prioritizes_exact_repo_name` | Function | `tests/test_project_search_service.py` | 54 |
| `test_search_can_filter_by_tag` | Function | `tests/test_project_search_service.py` | 65 |
| `test_search_filters_by_status_and_has_url` | Function | `tests/test_project_search_service.py` | 76 |
| `test_search_sorts_by_project_name` | Function | `tests/test_project_search_service.py` | 99 |
| `test_select_repo_respects_gitignore_and_sets_total_count` | Function | `tests/test_project_manager_select_repo.py` | 55 |
| `test_select_repo_preview_contains_extended_metadata` | Function | `tests/test_project_manager_select_repo.py` | 85 |
| `test_select_repo_missing_project_returns_value_error` | Function | `tests/test_project_manager_select_repo.py` | 121 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Repo_add → _promptkit` | cross_community | 6 |
| `Repo_add → _interactive_prompt_ui_enabled` | cross_community | 6 |
| `Repo_add → _convert_input` | cross_community | 5 |
| `Main → _override_from_environment` | cross_community | 5 |
| `Repo_add → _default_for_unprompted_field` | cross_community | 4 |
| `Repo_prune → Parse_gitignore` | cross_community | 3 |
| `Repo_prune → Should_ignore_path` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Project | 8 calls |
| Record | 4 calls |
| Cluster_312 | 4 calls |
| Cluster_308 | 3 calls |
| Commands | 2 calls |
| Config | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_prompt_for_model_project_path_url_only"})` — see callers and callees
2. `gitnexus_query({query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
