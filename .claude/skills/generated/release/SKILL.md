---
name: release
description: "Skill for the Release area of metagit-cli. 37 symbols across 8 files."
metadata:
  internal: true
---
# Release

37 symbols | 8 files | Cohesion: 74%

## When to Use

- Working with code in `src/`
- Understanding how version_check, normalize_version, compare_versions work
- Modifying release-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `tests/core/release/test_release_check_service.py` | test_check_records_network_errors, _github_payload, test_check_reports_update_available, test_check_omits_notes_when_requested, test_github_published_at_parses_utc (+4) |
| `src/metagit/core/release/changelog_ops.py` | read_changelog, parse_changelog, promote_unreleased, generate_commit_notes, _section_for_commit (+4) |
| `src/metagit/core/release/install_detect.py` | build_upgrade_command, detect_install_method, _package_is_installed, _is_editable_install, _is_uv_tool_install |
| `tests/core/release/test_upgrade_service.py` | _check_result, test_upgrade_dry_run_when_update_available, test_upgrade_skips_when_already_latest, test_upgrade_refuses_editable_install, test_upgrade_applies_command |
| `src/metagit/core/release/release_check_service.py` | check, _github_headers, _fetch_github_latest, _fetch_pypi_latest |
| `src/metagit/core/release/version_compare.py` | _prerelease_key, normalize_version, compare_versions |
| `src/metagit/cli/commands/version_cmd.py` | version_check |
| `src/metagit/core/release/upgrade_service.py` | upgrade |

## Entry Points

Start here when exploring this area:

- **`version_check`** (Function) — `src/metagit/cli/commands/version_cmd.py:42`
- **`normalize_version`** (Function) — `src/metagit/core/release/version_compare.py:21`
- **`compare_versions`** (Function) — `src/metagit/core/release/version_compare.py:39`
- **`test_check_records_network_errors`** (Function) — `tests/core/release/test_release_check_service.py:106`
- **`build_upgrade_command`** (Function) — `src/metagit/core/release/install_detect.py:28`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `version_check` | Function | `src/metagit/cli/commands/version_cmd.py` | 42 |
| `normalize_version` | Function | `src/metagit/core/release/version_compare.py` | 21 |
| `compare_versions` | Function | `src/metagit/core/release/version_compare.py` | 39 |
| `test_check_records_network_errors` | Function | `tests/core/release/test_release_check_service.py` | 106 |
| `build_upgrade_command` | Function | `src/metagit/core/release/install_detect.py` | 28 |
| `test_upgrade_dry_run_when_update_available` | Function | `tests/core/release/test_upgrade_service.py` | 31 |
| `test_upgrade_skips_when_already_latest` | Function | `tests/core/release/test_upgrade_service.py` | 49 |
| `test_upgrade_refuses_editable_install` | Function | `tests/core/release/test_upgrade_service.py` | 65 |
| `test_upgrade_applies_command` | Function | `tests/core/release/test_upgrade_service.py` | 80 |
| `read_changelog` | Function | `src/metagit/core/release/changelog_ops.py` | 49 |
| `parse_changelog` | Function | `src/metagit/core/release/changelog_ops.py` | 77 |
| `promote_unreleased` | Function | `src/metagit/core/release/changelog_ops.py` | 97 |
| `generate_commit_notes` | Function | `src/metagit/core/release/changelog_ops.py` | 134 |
| `detect_install_method` | Function | `src/metagit/core/release/install_detect.py` | 17 |
| `test_check_reports_update_available` | Function | `tests/core/release/test_release_check_service.py` | 46 |
| `test_check_omits_notes_when_requested` | Function | `tests/core/release/test_release_check_service.py` | 77 |
| `test_github_published_at_parses_utc` | Function | `tests/core/release/test_release_check_service.py` | 134 |
| `test_check_marks_installed_as_latest` | Function | `tests/core/release/test_release_check_service.py` | 64 |
| `test_check_falls_back_to_pypi_when_github_missing` | Function | `tests/core/release/test_release_check_service.py` | 90 |
| `test_check_retries_github_without_token_after_401` | Function | `tests/core/release/test_release_check_service.py` | 118 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 1 calls |

## How to Explore

1. `gitnexus_context({name: "version_check"})` — see callers and callees
2. `gitnexus_query({query: "release"})` — find related execution flows
3. Read key files listed above for implementation details
