---
name: record
description: "Skill for the Record area of metagit-cli. 30 symbols across 5 files."
---

# Record

30 symbols | 5 files | Cohesion: 89%

## When to Use

- Working with code in `src/`
- Understanding how main, main, RecordStorageBackend work
- Modifying record-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/record/manager.py` | _load_index, _save_index, _get_next_id, store_record, get_record (+11) |
| `src/metagit/core/record/models.py` | _get_common_fields, from_metagit_config_advanced, get_field_differences, get_compatible_fields, _convert_model_data (+3) |
| `tests/test_record_conversion.py` | test_field_differences, test_compatible_fields, test_get_detection_summary_without_optional_fields, test_conversion_performance |
| `examples/record_conversion_advanced_example.py` | main |
| `examples/record_conversion_example.py` | main |

## Entry Points

Start here when exploring this area:

- **`main`** (Function) — `examples/record_conversion_advanced_example.py:35`
- **`main`** (Function) — `examples/record_conversion_example.py:35`
- **`RecordStorageBackend`** (Class) — `src/metagit/core/record/manager.py:33`
- **`LocalFileStorageBackend`** (Class) — `src/metagit/core/record/manager.py:77`
- **`OpenSearchStorageBackend`** (Class) — `src/metagit/core/record/manager.py:290`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `RecordStorageBackend` | Class | `src/metagit/core/record/manager.py` | 33 |
| `LocalFileStorageBackend` | Class | `src/metagit/core/record/manager.py` | 77 |
| `OpenSearchStorageBackend` | Class | `src/metagit/core/record/manager.py` | 290 |
| `main` | Function | `examples/record_conversion_advanced_example.py` | 35 |
| `main` | Function | `examples/record_conversion_example.py` | 35 |
| `store_record` | Method | `src/metagit/core/record/manager.py` | 116 |
| `get_record` | Method | `src/metagit/core/record/manager.py` | 145 |
| `update_record` | Method | `src/metagit/core/record/manager.py` | 164 |
| `delete_record` | Method | `src/metagit/core/record/manager.py` | 198 |
| `search_records` | Method | `src/metagit/core/record/manager.py` | 216 |
| `list_records` | Method | `src/metagit/core/record/manager.py` | 265 |
| `from_metagit_config_advanced` | Method | `src/metagit/core/record/models.py` | 388 |
| `get_field_differences` | Method | `src/metagit/core/record/models.py` | 467 |
| `get_compatible_fields` | Method | `src/metagit/core/record/models.py` | 490 |
| `test_field_differences` | Method | `tests/test_record_conversion.py` | 131 |
| `test_compatible_fields` | Method | `tests/test_record_conversion.py` | 153 |
| `to_metagit_config` | Method | `src/metagit/core/record/models.py` | 264 |
| `to_metagit_config_advanced` | Method | `src/metagit/core/record/models.py` | 300 |
| `get_detection_summary` | Method | `src/metagit/core/record/models.py` | 430 |
| `test_get_detection_summary_without_optional_fields` | Method | `tests/test_record_conversion.py` | 270 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → _convert_model_data` | intra_community | 3 |
| `Main → _get_common_fields` | intra_community | 3 |
| `Main → _convert_model_data` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 5 calls |

## How to Explore

1. `gitnexus_context({name: "main"})` — see callers and callees
2. `gitnexus_query({query: "record"})` — find related execution flows
3. Read key files listed above for implementation details
