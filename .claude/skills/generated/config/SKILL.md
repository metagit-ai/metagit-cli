---
name: config
description: "Skill for the Config area of metagit-cli. 109 symbols across 22 files."
---

# Config

109 symbols | 22 files | Cohesion: 84%

## When to Use

- Working with code in `src/`
- Understanding how test_render_metagit_omits_schema_defaults_by_default, test_render_metagit_include_defaults_preserves_default_fields, resolve_sync_context work
- Modifying config-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/config/graph_cypher_export.py` | export, _ensure_workspace_node, _add_structure_nodes, _add_structure_edges, _add_documentation_nodes (+8) |
| `src/metagit/core/config/yaml_roundtrip.py` | _merge_list, _match_source_item, _build_source_identity_index, _list_item_identity, _normalize_value (+5) |
| `src/metagit/core/config/yaml_order.py` | _unwrap_optional, nested_model, list_item_model, _nested_model, _list_item_model (+4) |
| `src/metagit/core/config/documentation_models.py` | documentation_entry_identity, is_documentation_shorthand_eligible, compact_documentation_entry, _documentation_representation_richness, _merge_documentation_representations (+3) |
| `src/metagit/core/config/example_generator.py` | _render_mapping, _render_key_value, _format_scalar, _nested_model_for_annotation, _sample_model (+3) |
| `tests/core/config/test_format_service.py` | test_render_metagit_omits_schema_defaults_by_default, test_render_metagit_include_defaults_preserves_default_fields, _minimal_metagit_yaml, test_render_metagit_normalizes_messy_description, test_format_metagit_writes_ordered_file (+2) |
| `src/metagit/core/config/yaml_display.py` | _looks_like_url, should_use_literal_block, wrap_long_string, prepare_literal_block_string, normalize_yaml_string (+2) |
| `src/metagit/core/config/format_service.py` | format_metagit, format_appconfig, render_metagit, render_appconfig, _read_text (+1) |
| `src/metagit/core/config/schema_generator.py` | generate_json_schema, patch_metagit_config_schema, patch_appconfig_schema, _patch_documentation_property, _patch_repos_items (+1) |
| `src/metagit/core/config/patch_service.py` | patch, build_tree, preview, _load_metagit, _load_appconfig |

## Entry Points

Start here when exploring this area:

- **`test_render_metagit_omits_schema_defaults_by_default`** (Function) — `tests/core/config/test_format_service.py:101`
- **`test_render_metagit_include_defaults_preserves_default_fields`** (Function) — `tests/core/config/test_format_service.py:135`
- **`resolve_sync_context`** (Function) — `src/metagit/core/workspace/layout_context.py:15`
- **`evaluate_existing_manifest`** (Function) — `src/metagit/core/config/manifest_gate.py:33`
- **`load_config`** (Function) — `src/metagit/core/config/manager.py:50`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `TenantConfig` | Class | `src/metagit/core/config/models.py` | 912 |
| `AppConfig` | Class | `src/metagit/core/appconfig/models.py` | 194 |
| `test_render_metagit_omits_schema_defaults_by_default` | Function | `tests/core/config/test_format_service.py` | 101 |
| `test_render_metagit_include_defaults_preserves_default_fields` | Function | `tests/core/config/test_format_service.py` | 135 |
| `resolve_sync_context` | Function | `src/metagit/core/workspace/layout_context.py` | 15 |
| `evaluate_existing_manifest` | Function | `src/metagit/core/config/manifest_gate.py` | 33 |
| `load_config` | Function | `src/metagit/core/config/manager.py` | 50 |
| `validate_config` | Function | `src/metagit/core/config/manager.py` | 76 |
| `reload_config` | Function | `src/metagit/core/config/manager.py` | 127 |
| `workspace` | Function | `src/metagit/cli/commands/workspace.py` | 92 |
| `project` | Function | `src/metagit/cli/commands/project.py` | 42 |
| `config_show` | Function | `src/metagit/cli/commands/config.py` | 69 |
| `config_validate` | Function | `src/metagit/cli/commands/config.py` | 156 |
| `config_info` | Function | `src/metagit/cli/commands/config.py` | 374 |
| `config_graph_export` | Function | `src/metagit/cli/commands/config.py` | 694 |
| `format_metagit` | Function | `src/metagit/core/config/format_service.py` | 39 |
| `format_appconfig` | Function | `src/metagit/core/config/format_service.py` | 63 |
| `render_metagit` | Function | `src/metagit/core/config/format_service.py` | 86 |
| `render_appconfig` | Function | `src/metagit/core/config/format_service.py` | 115 |
| `fmt_cmd` | Function | `src/metagit/cli/commands/fmt.py` | 107 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Do_POST → Load_config` | cross_community | 4 |
| `Objective_set_cmd → Load_config` | cross_community | 4 |
| `Do_DELETE → Load_config` | cross_community | 4 |
| `Pack_cmd → Load_config` | cross_community | 4 |
| `Repomix_cmd → Load_config` | cross_community | 4 |
| `Approval_list_cmd → Load_config` | cross_community | 4 |
| `Handle → Load_config` | cross_community | 4 |
| `Fmt_cmd → _read_text` | intra_community | 4 |
| `Fmt_cmd → _build_result` | intra_community | 4 |
| `Fmt_cmd → Render_metagit` | intra_community | 4 |

## How to Explore

1. `gitnexus_context({name: "test_render_metagit_omits_schema_defaults_by_default"})` — see callers and callees
2. `gitnexus_query({query: "config"})` — find related execution flows
3. Read key files listed above for implementation details
