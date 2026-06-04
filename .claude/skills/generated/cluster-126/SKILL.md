---
name: cluster-126
description: "Skill for the Cluster_126 area of metagit-cli. 15 symbols across 1 files."
---

# Cluster_126

15 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `src/`
- Understanding how session, prompt_for_model, validate_type work
- Modifying cluster_126-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/utils/userprompt.py` | _promptkit, _prompt_style, _interactive_prompt_ui_enabled, _safe_print_formatted_text, session (+10) |

## Entry Points

Start here when exploring this area:

- **`session`** (Function) — `src/metagit/core/utils/userprompt.py:120`
- **`prompt_for_model`** (Function) — `src/metagit/core/utils/userprompt.py:146`
- **`validate_type`** (Function) — `src/metagit/core/utils/userprompt.py:494`
- **`prompt_for_single_field`** (Function) — `src/metagit/core/utils/userprompt.py:601`
- **`confirm_action`** (Function) — `src/metagit/core/utils/userprompt.py:638`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `session` | Function | `src/metagit/core/utils/userprompt.py` | 120 |
| `prompt_for_model` | Function | `src/metagit/core/utils/userprompt.py` | 146 |
| `validate_type` | Function | `src/metagit/core/utils/userprompt.py` | 494 |
| `prompt_for_single_field` | Function | `src/metagit/core/utils/userprompt.py` | 601 |
| `confirm_action` | Function | `src/metagit/core/utils/userprompt.py` | 638 |
| `prompt_for_model_fields` | Function | `src/metagit/core/utils/userprompt.py` | 667 |
| `_promptkit` | Function | `src/metagit/core/utils/userprompt.py` | 24 |
| `_prompt_style` | Function | `src/metagit/core/utils/userprompt.py` | 56 |
| `_interactive_prompt_ui_enabled` | Function | `src/metagit/core/utils/userprompt.py` | 75 |
| `_safe_print_formatted_text` | Function | `src/metagit/core/utils/userprompt.py` | 97 |
| `_default_for_unprompted_field` | Function | `src/metagit/core/utils/userprompt.py` | 128 |
| `_prompt_for_field` | Function | `src/metagit/core/utils/userprompt.py` | 267 |
| `_prompt_for_optional_field` | Function | `src/metagit/core/utils/userprompt.py` | 372 |
| `_create_field_validator` | Function | `src/metagit/core/utils/userprompt.py` | 477 |
| `_convert_input` | Function | `src/metagit/core/utils/userprompt.py` | 532 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Prompt_for_model → _promptkit` | intra_community | 4 |
| `Prompt_for_model → _interactive_prompt_ui_enabled` | intra_community | 4 |
| `Confirm_action → _promptkit` | intra_community | 3 |
| `Confirm_action → _interactive_prompt_ui_enabled` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "session"})` — see callers and callees
2. `gitnexus_query({query: "cluster_126"})` — find related execution flows
3. Read key files listed above for implementation details
