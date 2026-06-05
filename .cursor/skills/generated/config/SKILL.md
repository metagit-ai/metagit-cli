---
name: config
description: "Skill for the Config area of metagit-cli. 88 symbols across 14 files."
metadata:
  internal: true
---
# Config

88 symbols | 14 files | Cohesion: 90%

## When to Use

- Working with code in `src/`
- Understanding how format_metagit, format_appconfig, render_metagit work
- Modifying config-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/config/graph_cypher_export.py` | export, _ensure_workspace_node, _add_structure_nodes, _add_structure_edges, _add_documentation_nodes (+8) |
| `src/metagit/core/config/yaml_roundtrip.py` | _merge_list, _match_source_item, _build_source_identity_index, _list_item_identity, _normalize_value (+5) |
| `src/metagit/core/config/yaml_order.py` | _unwrap_optional, nested_model, list_item_model, _nested_model, _list_item_model (+4) |
| `src/metagit/core/config/documentation_models.py` | documentation_entry_identity, is_documentation_shorthand_eligible, compact_documentation_entry, _documentation_representation_richness, _merge_documentation_representations (+3) |
| `src/metagit/core/config/example_generator.py` | _render_mapping, _render_key_value, _format_scalar, _nested_model_for_annotation, _sample_model (+3) |
| `src/metagit/core/config/format_service.py` | format_metagit, format_appconfig, render_metagit, render_appconfig, _read_text (+1) |
| `src/metagit/core/config/schema_generator.py` | generate_json_schema, patch_metagit_config_schema, patch_appconfig_schema, _patch_documentation_property, _patch_repos_items (+1) |
| `src/metagit/core/config/patch_service.py` | patch, build_tree, preview, _load_metagit, _load_appconfig |
| `tests/core/config/test_format_service.py` | _minimal_metagit_yaml, test_render_metagit_normalizes_messy_description, test_format_metagit_writes_ordered_file, test_fmt_check_reports_changes, test_fmt_writes_in_place |
| `src/metagit/core/config/yaml_display.py` | should_use_literal_block, prepare_literal_block_string, normalize_yaml_string, format_yaml_string, _represent_str |

## Entry Points

Start here when exploring this area:

- **`format_metagit`** (Function) — `src/metagit/core/config/format_service.py:38`
- **`format_appconfig`** (Function) — `src/metagit/core/config/format_service.py:62`
- **`render_metagit`** (Function) — `src/metagit/core/config/format_service.py:85`
- **`render_appconfig`** (Function) — `src/metagit/core/config/format_service.py:108`
- **`fmt_cmd`** (Function) — `src/metagit/cli/commands/fmt.py:96`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `TenantConfig` | Class | `src/metagit/core/config/models.py` | 884 |
| `AppConfig` | Class | `src/metagit/core/appconfig/models.py` | 194 |
| `format_metagit` | Function | `src/metagit/core/config/format_service.py` | 38 |
| `format_appconfig` | Function | `src/metagit/core/config/format_service.py` | 62 |
| `render_metagit` | Function | `src/metagit/core/config/format_service.py` | 85 |
| `render_appconfig` | Function | `src/metagit/core/config/format_service.py` | 108 |
| `fmt_cmd` | Function | `src/metagit/cli/commands/fmt.py` | 96 |
| `export` | Function | `src/metagit/core/config/graph_cypher_export.py` | 94 |
| `generate_json_schema` | Function | `src/metagit/core/config/schema_generator.py` | 66 |
| `patch_metagit_config_schema` | Function | `src/metagit/core/config/schema_generator.py` | 76 |
| `patch_appconfig_schema` | Function | `src/metagit/core/config/schema_generator.py` | 97 |
| `documentation_entry_identity` | Function | `src/metagit/core/config/documentation_models.py` | 125 |
| `is_documentation_shorthand_eligible` | Function | `src/metagit/core/config/documentation_models.py` | 134 |
| `compact_documentation_entry` | Function | `src/metagit/core/config/documentation_models.py` | 143 |
| `compact_documentation_list` | Function | `src/metagit/core/config/documentation_models.py` | 189 |
| `test_patch_metagit_set_name_dry_run` | Function | `tests/core/config/test_patch_service.py` | 16 |
| `test_patch_metagit_set_name_save` | Function | `tests/core/config/test_patch_service.py` | 41 |
| `test_patch_append_workspace_project` | Function | `tests/core/config/test_patch_service.py` | 65 |
| `patch` | Function | `src/metagit/core/config/patch_service.py` | 144 |
| `test_render_metagit_normalizes_messy_description` | Function | `tests/core/config/test_format_service.py` | 40 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Fmt_cmd → _read_text` | intra_community | 4 |
| `Fmt_cmd → _build_result` | intra_community | 4 |
| `Fmt_cmd → Render_metagit` | intra_community | 4 |
| `Fmt_cmd → Load_config` | cross_community | 4 |
| `Fmt_cmd → Render_appconfig` | intra_community | 4 |
| `Compact_documentation_list → Is_documentation_shorthand_eligible` | intra_community | 3 |
| `Compact_documentation_list → _documentation_representation_richness` | intra_community | 3 |
| `Order_payload → _unwrap_optional` | cross_community | 3 |
| `Order_payload → _field_source_keys` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 3 calls |

## How to Explore

1. `gitnexus_context({name: "format_metagit"})` — see callers and callees
2. `gitnexus_query({query: "config"})` — find related execution flows
3. Read key files listed above for implementation details
