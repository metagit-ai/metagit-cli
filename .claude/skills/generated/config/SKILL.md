---
name: config
description: "Skill for the Config area of metagit-cli. 137 symbols across 31 files."
metadata:
  internal: true
---
# Config

137 symbols | 31 files | Cohesion: 82%

## When to Use

- Working with code in `src/`
- Understanding how node_id_to_endpoint, test_suggest_finds_import_and_url_match_candidates, test_suggest_skips_existing_manual_relationships work
- Modifying config-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/config/graph_cypher_export.py` | _escape_cypher_string, _literal_string, _literal_json, _build_statements, _merge_node_statement (+8) |
| `src/metagit/core/config/documentation_models.py` | documentation_entry_identity, is_documentation_shorthand_eligible, compact_documentation_entry, _documentation_representation_richness, _merge_documentation_representations (+7) |
| `src/metagit/core/config/example_generator.py` | load_example_overrides, render_yaml, deep_merge, build, _render_mapping (+7) |
| `src/metagit/core/config/graph_suggest.py` | node_id_to_endpoint, _slug, _relationship_signature, suggest, _resolve_dependency_types (+6) |
| `src/metagit/core/config/yaml_roundtrip.py` | _normalize_value, build_roundtrip_yaml, format_yaml_document, _merge_map, _copy_map_key_comment (+5) |
| `src/metagit/core/config/yaml_order.py` | find_source_key, nested_model, _unwrap_optional, _resolve_field_value, order_payload (+4) |
| `src/metagit/core/config/yaml_display.py` | _looks_like_url, should_use_literal_block, wrap_long_string, prepare_literal_block_string, normalize_yaml_string (+2) |
| `src/metagit/core/config/format_service.py` | format_metagit, format_appconfig, render_metagit, render_appconfig, _read_text (+1) |
| `src/metagit/core/config/models.py` | _override_from_environment, load, _coerce_documentation, Dependency, documentation_graph_nodes (+1) |
| `src/metagit/core/config/patch_service.py` | patch, build_tree, preview, _load_metagit, _load_appconfig |

## Entry Points

Start here when exploring this area:

- **`node_id_to_endpoint`** (Function) — `src/metagit/core/config/graph_suggest.py:86`
- **`test_suggest_finds_import_and_url_match_candidates`** (Function) — `tests/core/config/test_graph_suggest.py:72`
- **`test_suggest_skips_existing_manual_relationships`** (Function) — `tests/core/config/test_graph_suggest.py:95`
- **`fmt_cmd`** (Function) — `src/metagit/cli/commands/fmt.py:107`
- **`prune_empty_dict_nodes`** (Function) — `src/metagit/core/config/payload_compact.py:10`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Dependency` | Class | `src/metagit/core/config/models.py` | 276 |
| `ProjectPath` | Class | `src/metagit/core/project/models.py` | 63 |
| `node_id_to_endpoint` | Function | `src/metagit/core/config/graph_suggest.py` | 86 |
| `test_suggest_finds_import_and_url_match_candidates` | Function | `tests/core/config/test_graph_suggest.py` | 72 |
| `test_suggest_skips_existing_manual_relationships` | Function | `tests/core/config/test_graph_suggest.py` | 95 |
| `fmt_cmd` | Function | `src/metagit/cli/commands/fmt.py` | 107 |
| `prune_empty_dict_nodes` | Function | `src/metagit/core/config/payload_compact.py` | 10 |
| `prepare_format_payload` | Function | `src/metagit/core/config/payload_compact.py` | 20 |
| `appconfig_set` | Function | `src/metagit/cli/commands/appconfig.py` | 202 |
| `save_config` | Function | `src/metagit/core/appconfig/__init__.py` | 41 |
| `set_config` | Function | `src/metagit/core/appconfig/__init__.py` | 80 |
| `test_patch_metagit_set_name_dry_run` | Function | `tests/core/config/test_patch_service.py` | 16 |
| `test_patch_metagit_set_name_save` | Function | `tests/core/config/test_patch_service.py` | 41 |
| `test_patch_append_workspace_project` | Function | `tests/core/config/test_patch_service.py` | 65 |
| `should_use_literal_block` | Function | `src/metagit/core/config/yaml_display.py` | 22 |
| `wrap_long_string` | Function | `src/metagit/core/config/yaml_display.py` | 36 |
| `prepare_literal_block_string` | Function | `src/metagit/core/config/yaml_display.py` | 51 |
| `normalize_yaml_string` | Function | `src/metagit/core/config/yaml_display.py` | 82 |
| `format_yaml_string` | Function | `src/metagit/core/config/yaml_display.py` | 97 |
| `schema_language_server_directive` | Function | `src/metagit/core/config/schema_urls.py` | 13 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Config_graph_suggest → Resolve_graph_endpoint_id` | cross_community | 5 |
| `Config_graph_suggest → Node_id_to_endpoint` | cross_community | 5 |
| `Config_graph_suggest → _relationship_signature` | cross_community | 5 |
| `Main → _override_from_environment` | cross_community | 5 |
| `Handle → _override_from_environment` | cross_community | 5 |
| `Preview → _override_from_environment` | cross_community | 4 |
| `Config_graph_suggest → _resolve_dependency_types` | cross_community | 4 |
| `Config_graph_suggest → _filter_candidate_ids` | cross_community | 4 |
| `Config_graph_suggest → _slug` | cross_community | 4 |
| `Preview → Load_config` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 9 calls |
| Web | 1 calls |
| Appconfig | 1 calls |

## How to Explore

1. `gitnexus_context({name: "node_id_to_endpoint"})` — see callers and callees
2. `gitnexus_query({query: "config"})` — find related execution flows
3. Read key files listed above for implementation details
