---
name: cluster-130
description: "Skill for the Cluster_130 area of metagit-cli. 12 symbols across 1 files."
---

# Cluster_130

12 symbols | 1 files | Cohesion: 82%

## When to Use

- Working with code in `src/`
- Understanding how print_agent_message, print_task_status, print_crew_status work
- Modifying cluster_130-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/utils/logging.py` | print_agent_message, print_task_status, print_crew_status, print_input, print_output (+7) |

## Entry Points

Start here when exploring this area:

- **`print_agent_message`** (Function) — `src/metagit/core/utils/logging.py:318`
- **`print_task_status`** (Function) — `src/metagit/core/utils/logging.py:329`
- **`print_crew_status`** (Function) — `src/metagit/core/utils/logging.py:346`
- **`print_input`** (Function) — `src/metagit/core/utils/logging.py:357`
- **`print_output`** (Function) — `src/metagit/core/utils/logging.py:366`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `print_agent_message` | Function | `src/metagit/core/utils/logging.py` | 318 |
| `print_task_status` | Function | `src/metagit/core/utils/logging.py` | 329 |
| `print_crew_status` | Function | `src/metagit/core/utils/logging.py` | 346 |
| `print_input` | Function | `src/metagit/core/utils/logging.py` | 357 |
| `print_output` | Function | `src/metagit/core/utils/logging.py` | 366 |
| `print_error` | Function | `src/metagit/core/utils/logging.py` | 375 |
| `print_success` | Function | `src/metagit/core/utils/logging.py` | 384 |
| `print_info` | Function | `src/metagit/core/utils/logging.py` | 393 |
| `print_json` | Function | `src/metagit/core/utils/logging.py` | 402 |
| `print_debug_json` | Function | `src/metagit/core/utils/logging.py` | 414 |
| `info` | Function | `src/metagit/core/utils/logging.py` | 434 |
| `_format_output` | Function | `src/metagit/core/utils/logging.py` | 474 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Init → Info` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cli | 1 calls |

## How to Explore

1. `gitnexus_context({name: "print_agent_message"})` — see callers and callees
2. `gitnexus_query({query: "cluster_130"})` — find related execution flows
3. Read key files listed above for implementation details
