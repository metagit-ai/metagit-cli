---
name: init
description: "Skill for the Init area of metagit-cli. 26 symbols across 7 files."
---

# Init

26 symbols | 7 files | Cohesion: 74%

## When to Use

- Working with code in `src/`
- Understanding how resolve_target_dir, init, test_list_templates_includes_hermes work
- Modifying init-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/init/renderer.py` | render_placeholders, clean_manifest_payload, validate_metagit_yaml, render_file, render_manifest |
| `src/metagit/cli/commands/init.py` | _resolve_project_metadata, resolve_target_dir, init, _print_next_steps |
| `src/metagit/core/init/registry.py` | list_templates, load_manifest, template_dir, _safe_template_path |
| `src/metagit/core/init/service.py` | list_templates, resolve_template_id, initialize, initialize_minimal |
| `tests/core/init/test_init_service.py` | test_list_templates_includes_hermes, test_init_hermes_with_answers_file, test_init_minimal_library_kind, test_init_minimal_idempotent_when_manifest_valid |
| `src/metagit/core/init/prompts.py` | load_answers_file, build_builtin_defaults, resolve_prompt_default, collect_answers |
| `src/metagit/core/utils/logging.py` | header |

## Entry Points

Start here when exploring this area:

- **`resolve_target_dir`** (Function) — `src/metagit/cli/commands/init.py:46`
- **`init`** (Function) — `src/metagit/cli/commands/init.py:164`
- **`test_list_templates_includes_hermes`** (Function) — `tests/core/init/test_init_service.py:10`
- **`load_answers_file`** (Function) — `src/metagit/core/init/prompts.py:17`
- **`build_builtin_defaults`** (Function) — `src/metagit/core/init/prompts.py:33`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `resolve_target_dir` | Function | `src/metagit/cli/commands/init.py` | 46 |
| `init` | Function | `src/metagit/cli/commands/init.py` | 164 |
| `test_list_templates_includes_hermes` | Function | `tests/core/init/test_init_service.py` | 10 |
| `load_answers_file` | Function | `src/metagit/core/init/prompts.py` | 17 |
| `build_builtin_defaults` | Function | `src/metagit/core/init/prompts.py` | 33 |
| `resolve_prompt_default` | Function | `src/metagit/core/init/prompts.py` | 46 |
| `collect_answers` | Function | `src/metagit/core/init/prompts.py` | 58 |
| `test_init_hermes_with_answers_file` | Function | `tests/core/init/test_init_service.py` | 18 |
| `render_placeholders` | Function | `src/metagit/core/init/renderer.py` | 16 |
| `clean_manifest_payload` | Function | `src/metagit/core/init/renderer.py` | 26 |
| `validate_metagit_yaml` | Function | `src/metagit/core/init/renderer.py` | 36 |
| `test_init_minimal_library_kind` | Function | `tests/core/init/test_init_service.py` | 55 |
| `test_init_minimal_idempotent_when_manifest_valid` | Function | `tests/core/init/test_init_service.py` | 72 |
| `list_templates` | Method | `src/metagit/core/init/registry.py` | 23 |
| `load_manifest` | Method | `src/metagit/core/init/registry.py` | 36 |
| `list_templates` | Method | `src/metagit/core/init/service.py` | 41 |
| `resolve_template_id` | Method | `src/metagit/core/init/service.py` | 44 |
| `header` | Method | `src/metagit/core/utils/logging.py` | 504 |
| `template_dir` | Method | `src/metagit/core/init/registry.py` | 47 |
| `initialize` | Method | `src/metagit/core/init/service.py` | 78 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Init → _safe_template_path` | cross_community | 5 |
| `Init → Load_config` | cross_community | 5 |
| `Init → Render_placeholders` | cross_community | 5 |
| `Init → Clean_manifest_payload` | cross_community | 5 |
| `Init → Manifest_gate_error_message` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cluster_311 | 13 calls |
| Cli | 5 calls |
| Providers | 2 calls |
| Examples | 1 calls |
| Commands | 1 calls |

## How to Explore

1. `gitnexus_context({name: "resolve_target_dir"})` — see callers and callees
2. `gitnexus_query({query: "init"})` — find related execution flows
3. Read key files listed above for implementation details
