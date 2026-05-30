---
name: record
description: "Skill for the Record area of metagit-cli. 26 symbols across 4 files."
---

# Record

26 symbols | 4 files | Cohesion: 100%

## When to Use

- Working with code in `src/`
- Understanding how store_record, get_record, update_record work
- Modifying record-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/record/manager.py` | _load_index, _save_index, _get_next_id, store_record, get_record (+11) |
| `src/metagit/core/record/models.py` | _convert_model_data, to_metagit_config, to_metagit_config_advanced, _get_common_fields, get_compatible_fields (+2) |
| `tests/test_record_conversion.py` | test_conversion_performance, test_conversion_validation |
| `examples/record_conversion_advanced_example.py` | main |

## Entry Points

Start here when exploring this area:

- **`store_record`** (Function) — `src/metagit/core/record/manager.py:116`
- **`get_record`** (Function) — `src/metagit/core/record/manager.py:145`
- **`update_record`** (Function) — `src/metagit/core/record/manager.py:164`
- **`delete_record`** (Function) — `src/metagit/core/record/manager.py:198`
- **`search_records`** (Function) — `src/metagit/core/record/manager.py:216`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `RecordStorageBackend` | Class | `src/metagit/core/record/manager.py` | 33 |
| `LocalFileStorageBackend` | Class | `src/metagit/core/record/manager.py` | 77 |
| `OpenSearchStorageBackend` | Class | `src/metagit/core/record/manager.py` | 290 |
| `store_record` | Function | `src/metagit/core/record/manager.py` | 116 |
| `get_record` | Function | `src/metagit/core/record/manager.py` | 145 |
| `update_record` | Function | `src/metagit/core/record/manager.py` | 164 |
| `delete_record` | Function | `src/metagit/core/record/manager.py` | 198 |
| `search_records` | Function | `src/metagit/core/record/manager.py` | 216 |
| `list_records` | Function | `src/metagit/core/record/manager.py` | 265 |
| `test_conversion_performance` | Function | `tests/test_record_conversion.py` | 290 |
| `test_conversion_validation` | Function | `tests/test_record_conversion.py` | 389 |
| `main` | Function | `examples/record_conversion_advanced_example.py` | 35 |
| `to_metagit_config` | Function | `src/metagit/core/record/models.py` | 264 |
| `to_metagit_config_advanced` | Function | `src/metagit/core/record/models.py` | 300 |
| `get_compatible_fields` | Function | `src/metagit/core/record/models.py` | 490 |
| `from_metagit_config` | Function | `src/metagit/core/record/models.py` | 329 |
| `from_metagit_config_advanced` | Function | `src/metagit/core/record/models.py` | 388 |
| `search_records` | Function | `src/metagit/core/record/manager.py` | 320 |
| `list_records` | Function | `src/metagit/core/record/manager.py` | 335 |
| `_load_index` | Function | `src/metagit/core/record/manager.py` | 98 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Store_record → _load_index` | intra_community | 3 |
| `Store_record → _save_index` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "store_record"})` — see callers and callees
2. `gitnexus_query({query: "record"})` — find related execution flows
3. Read key files listed above for implementation details
