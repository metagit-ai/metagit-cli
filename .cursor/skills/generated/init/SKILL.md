---
name: init
description: "Skill for the Init area of metagit-cli. 18 symbols across 5 files."
---

# Init

18 symbols | 5 files | Cohesion: 92%

## When to Use

- Working with code in `src/`
- Understanding how test_init_hermes_with_answers_file, test_init_minimal_library_kind, test_init_minimal_idempotent_when_manifest_valid work
- Modifying init-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/init/renderer.py` | render_placeholders, clean_manifest_payload, validate_metagit_yaml, render_file, render_manifest |
| `src/metagit/core/init/registry.py` | list_templates, load_manifest, template_dir, _safe_template_path |
| `tests/core/init/test_init_service.py` | test_init_hermes_with_answers_file, test_init_minimal_library_kind, test_init_minimal_idempotent_when_manifest_valid |
| `src/metagit/core/init/service.py` | _resolve_existing_manifest, initialize, initialize_minimal |
| `src/metagit/core/init/prompts.py` | build_builtin_defaults, resolve_prompt_default, collect_answers |

## Entry Points

Start here when exploring this area:

- **`test_init_hermes_with_answers_file`** (Function) — `tests/core/init/test_init_service.py:18`
- **`test_init_minimal_library_kind`** (Function) — `tests/core/init/test_init_service.py:55`
- **`test_init_minimal_idempotent_when_manifest_valid`** (Function) — `tests/core/init/test_init_service.py:72`
- **`initialize`** (Function) — `src/metagit/core/init/service.py:78`
- **`initialize_minimal`** (Function) — `src/metagit/core/init/service.py:139`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_init_hermes_with_answers_file` | Function | `tests/core/init/test_init_service.py` | 18 |
| `test_init_minimal_library_kind` | Function | `tests/core/init/test_init_service.py` | 55 |
| `test_init_minimal_idempotent_when_manifest_valid` | Function | `tests/core/init/test_init_service.py` | 72 |
| `initialize` | Function | `src/metagit/core/init/service.py` | 78 |
| `initialize_minimal` | Function | `src/metagit/core/init/service.py` | 139 |
| `render_placeholders` | Function | `src/metagit/core/init/renderer.py` | 16 |
| `clean_manifest_payload` | Function | `src/metagit/core/init/renderer.py` | 26 |
| `validate_metagit_yaml` | Function | `src/metagit/core/init/renderer.py` | 36 |
| `render_file` | Function | `src/metagit/core/init/renderer.py` | 47 |
| `render_manifest` | Function | `src/metagit/core/init/renderer.py` | 59 |
| `list_templates` | Function | `src/metagit/core/init/registry.py` | 23 |
| `load_manifest` | Function | `src/metagit/core/init/registry.py` | 36 |
| `template_dir` | Function | `src/metagit/core/init/registry.py` | 47 |
| `build_builtin_defaults` | Function | `src/metagit/core/init/prompts.py` | 33 |
| `resolve_prompt_default` | Function | `src/metagit/core/init/prompts.py` | 46 |
| `collect_answers` | Function | `src/metagit/core/init/prompts.py` | 58 |
| `_resolve_existing_manifest` | Function | `src/metagit/core/init/service.py` | 55 |
| `_safe_template_path` | Function | `src/metagit/core/init/registry.py` | 51 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Examples | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_init_hermes_with_answers_file"})` — see callers and callees
2. `gitnexus_query({query: "init"})` — find related execution flows
3. Read key files listed above for implementation details
