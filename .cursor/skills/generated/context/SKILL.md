---
name: context
description: "Skill for the Context area of metagit-cli. 99 symbols across 19 files."
---

# Context

99 symbols | 19 files | Cohesion: 86%

## When to Use

- Working with code in `tests/`
- Understanding how test_list_returns_empty_when_no_file, test_upsert_persists_under_sessions, test_get_and_list_roundtrip work
- Modifying context-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/core/context/test_objective_service.py` | _sample_objective, test_list_returns_empty_when_no_file, test_upsert_persists_under_sessions, test_get_and_list_roundtrip, test_upsert_updates_existing_keeps_created_at (+5) |
| `src/metagit/core/context/repo_card_service.py` | build_one, build_many, _find_index_row, _locate_manifest_entries, _tags_to_list (+5) |
| `tests/core/context/test_context_pack_service.py` | _fixture, test_tier_zero_returns_map_no_cards, test_tier_one_single_repo_filter, test_token_estimate_excludes_estimate_field, test_tier_two_includes_digest_and_touches_session (+4) |
| `tests/core/context/test_session_digest_service.py` | _load_cfg, test_build_first_session_empty_repos, test_manifest_changed_false_when_mtime_not_after_since, test_manifest_changed_true_when_mtime_after_since, test_git_activity_populates_count_and_subjects (+3) |
| `tests/core/context/test_repomix_profile_service.py` | test_unknown_profile_raises, test_build_argv_include_comma_join, test_build_argv_exclude_when_present, test_build_argv_writes_file_not_stdout, test_run_repomix_injects_runner (+3) |
| `src/metagit/core/context/objective_service.py` | list, upsert, get, complete, cancel (+2) |
| `src/metagit/core/context/repomix_profile_service.py` | get_profile, build_repomix_argv, _run_repomix_process, run_repomix, profile_names (+2) |
| `tests/core/context/test_approval_service.py` | test_request_persists_hex_id_and_pending_status, test_list_optional_status_filter, test_resolve_sets_status_timestamp_and_note, test_resolve_unknown_id_raises, test_resolve_non_pending_raises (+1) |
| `tests/core/context/test_repo_card_service.py` | _load_config, test_build_one_git_repo_detects_pyproject_and_branch, test_build_one_missing_clone_sets_missing_clone_flag, test_health_flags_stale_head_via_mock, test_build_many_respects_max_cards |
| `tests/core/context/test_workspace_map_service.py` | _write_single_project_workspace, _load_config, test_build_maps_catalog_to_workspace_map_result, test_build_passes_through_active_project, test_build_missing_repo_reports_configured_missing |

## Entry Points

Start here when exploring this area:

- **`test_list_returns_empty_when_no_file`** (Function) — `tests/core/context/test_objective_service.py:29`
- **`test_upsert_persists_under_sessions`** (Function) — `tests/core/context/test_objective_service.py:35`
- **`test_get_and_list_roundtrip`** (Function) — `tests/core/context/test_objective_service.py:48`
- **`test_upsert_updates_existing_keeps_created_at`** (Function) — `tests/core/context/test_objective_service.py:59`
- **`test_objective_model_rejects_invalid_id`** (Function) — `tests/core/context/test_objective_service.py:108`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_list_returns_empty_when_no_file` | Function | `tests/core/context/test_objective_service.py` | 29 |
| `test_upsert_persists_under_sessions` | Function | `tests/core/context/test_objective_service.py` | 35 |
| `test_get_and_list_roundtrip` | Function | `tests/core/context/test_objective_service.py` | 48 |
| `test_upsert_updates_existing_keeps_created_at` | Function | `tests/core/context/test_objective_service.py` | 59 |
| `test_objective_model_rejects_invalid_id` | Function | `tests/core/context/test_objective_service.py` | 108 |
| `test_objective_model_rejects_blank_title` | Function | `tests/core/context/test_objective_service.py` | 113 |
| `list` | Function | `src/metagit/core/context/objective_service.py` | 21 |
| `upsert` | Function | `src/metagit/core/context/objective_service.py` | 33 |
| `test_build_one_git_repo_detects_pyproject_and_branch` | Function | `tests/core/context/test_repo_card_service.py` | 22 |
| `test_build_one_missing_clone_sets_missing_clone_flag` | Function | `tests/core/context/test_repo_card_service.py` | 63 |
| `test_health_flags_stale_head_via_mock` | Function | `tests/core/context/test_repo_card_service.py` | 95 |
| `test_build_many_respects_max_cards` | Function | `tests/core/context/test_repo_card_service.py` | 145 |
| `build_one` | Function | `src/metagit/core/context/repo_card_service.py` | 46 |
| `build_many` | Function | `src/metagit/core/context/repo_card_service.py` | 66 |
| `test_complete_and_cancel` | Function | `tests/core/context/test_objective_service.py` | 78 |
| `test_get_complete_cancel_reject_bad_id_slug` | Function | `tests/core/context/test_objective_service.py` | 92 |
| `test_complete_missing_raises` | Function | `tests/core/context/test_objective_service.py` | 102 |
| `get` | Function | `src/metagit/core/context/objective_service.py` | 25 |
| `complete` | Function | `src/metagit/core/context/objective_service.py` | 59 |
| `cancel` | Function | `src/metagit/core/context/objective_service.py` | 63 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Pack_cmd → _read_json` | cross_community | 5 |
| `Pack_cmd → Ensure_dirs` | cross_community | 5 |
| `Pack_cmd → _write_json` | cross_community | 5 |
| `Repomix_cmd → Load_config` | cross_community | 4 |
| `Repomix_cmd → Get_profile` | cross_community | 4 |
| `Approval_list_cmd → Load_config` | cross_community | 4 |
| `Build → _resolve_repo_path` | cross_community | 3 |
| `Pack_cmd → _estimate_tokens` | cross_community | 3 |
| `Repomix_cmd → _run_repomix_process` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 7 calls |
| Services | 3 calls |
| Web | 1 calls |
| Tests | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_list_returns_empty_when_no_file"})` — see callers and callees
2. `gitnexus_query({query: "context"})` — find related execution flows
3. Read key files listed above for implementation details
