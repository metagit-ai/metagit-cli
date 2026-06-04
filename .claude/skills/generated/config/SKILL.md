---
name: config
description: "Skill for the Config area of metagit-cli. 128 symbols across 30 files."
---

# Config

128 symbols | 30 files | Cohesion: 79%

## When to Use

- Working with code in `src/`
- Understanding how fmt_cmd, prune_empty_dict_nodes, prepare_format_payload work
- Modifying config-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/config/graph_cypher_export.py` | _escape_cypher_string, _literal_string, _literal_json, _build_statements, _merge_node_statement (+8) |
| `src/metagit/core/config/documentation_models.py` | documentation_entry_identity, is_documentation_shorthand_eligible, compact_documentation_entry, _documentation_representation_richness, _merge_documentation_representations (+7) |
| `src/metagit/core/config/example_generator.py` | load_example_overrides, render_yaml, deep_merge, build, _render_mapping (+7) |
| `src/metagit/core/config/yaml_roundtrip.py` | _normalize_value, build_roundtrip_yaml, format_yaml_document, _merge_map, _copy_map_key_comment (+5) |
| `src/metagit/core/config/yaml_order.py` | find_source_key, nested_model, _unwrap_optional, _resolve_field_value, order_payload (+4) |
| `tests/core/config/test_format_service.py` | test_render_metagit_omits_schema_defaults_by_default, test_render_metagit_include_defaults_preserves_default_fields, _minimal_metagit_yaml, test_render_metagit_normalizes_messy_description, test_format_metagit_writes_ordered_file (+2) |
| `src/metagit/core/config/yaml_display.py` | _looks_like_url, should_use_literal_block, wrap_long_string, prepare_literal_block_string, normalize_yaml_string (+2) |
| `src/metagit/core/config/format_service.py` | format_metagit, format_appconfig, render_metagit, render_appconfig, _read_text (+1) |
| `src/metagit/core/config/models.py` | _override_from_environment, load, _coerce_documentation, Dependency, documentation_graph_nodes (+1) |
| `src/metagit/core/config/patch_service.py` | patch, build_tree, preview, _load_metagit, _load_appconfig |

## Entry Points

Start here when exploring this area:

- **`fmt_cmd`** (Function) — `src/metagit/cli/commands/fmt.py:107`
- **`prune_empty_dict_nodes`** (Function) — `src/metagit/core/config/payload_compact.py:10`
- **`prepare_format_payload`** (Function) — `src/metagit/core/config/payload_compact.py:20`
- **`config_validate`** (Function) — `src/metagit/cli/commands/config.py:161`
- **`config_info`** (Function) — `src/metagit/cli/commands/config.py:379`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Dependency` | Class | `src/metagit/core/config/models.py` | 276 |
| `ProjectPath` | Class | `src/metagit/core/project/models.py` | 63 |
| `fmt_cmd` | Function | `src/metagit/cli/commands/fmt.py` | 107 |
| `prune_empty_dict_nodes` | Function | `src/metagit/core/config/payload_compact.py` | 10 |
| `prepare_format_payload` | Function | `src/metagit/core/config/payload_compact.py` | 20 |
| `config_validate` | Function | `src/metagit/cli/commands/config.py` | 161 |
| `config_info` | Function | `src/metagit/cli/commands/config.py` | 379 |
| `config_graph_export` | Function | `src/metagit/cli/commands/config.py` | 699 |
| `workspace` | Function | `src/metagit/cli/commands/workspace.py` | 93 |
| `test_render_metagit_omits_schema_defaults_by_default` | Function | `tests/core/config/test_format_service.py` | 101 |
| `test_render_metagit_include_defaults_preserves_default_fields` | Function | `tests/core/config/test_format_service.py` | 135 |
| `appconfig_set` | Function | `src/metagit/cli/commands/appconfig.py` | 202 |
| `save_config` | Function | `src/metagit/core/appconfig/__init__.py` | 41 |
| `set_config` | Function | `src/metagit/core/appconfig/__init__.py` | 80 |
| `test_patch_metagit_set_name_dry_run` | Function | `tests/core/config/test_patch_service.py` | 16 |
| `test_patch_metagit_set_name_save` | Function | `tests/core/config/test_patch_service.py` | 41 |
| `test_patch_append_workspace_project` | Function | `tests/core/config/test_patch_service.py` | 65 |
| `should_use_literal_block` | Function | `src/metagit/core/config/yaml_display.py` | 22 |
| `wrap_long_string` | Function | `src/metagit/core/config/yaml_display.py` | 36 |
| `prepare_literal_block_string` | Function | `src/metagit/core/config/yaml_display.py` | 51 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Config_example → _nested_model_for_annotation` | cross_community | 7 |
| `Init → Load_config` | cross_community | 5 |
| `Main → _override_from_environment` | cross_community | 5 |
| `Handle → _override_from_environment` | cross_community | 5 |
| `Config_example → _format_scalar` | cross_community | 5 |
| `Do_GET → Load_config` | cross_community | 4 |
| `Do_POST → Load_config` | cross_community | 4 |
| `Preview → _override_from_environment` | cross_community | 4 |
| `Pack_cmd → Load_config` | cross_community | 4 |
| `Repomix_cmd → Load_config` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 3 calls |
| Web | 1 calls |
| Appconfig | 1 calls |

## How to Explore

1. `gitnexus_context({name: "fmt_cmd"})` — see callers and callees
2. `gitnexus_query({query: "config"})` — find related execution flows
3. Read key files listed above for implementation details
