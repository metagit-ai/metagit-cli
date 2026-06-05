---
name: detect
description: "Skill for the Detect area of metagit-cli. 26 symbols across 7 files."
metadata:
  internal: true
---
# Detect

26 symbols | 7 files | Cohesion: 94%

## When to Use

- Working with code in `src/`
- Understanding how detect_project, list_git_files, convert_objects work
- Modifying detect-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `src/metagit/core/detect/manager.py` | run_all, run_specific, _extract_metadata, _detect_languages, _detect_project_type (+14) |
| `src/metagit/core/detect/models.py` | GitBranchAnalysis, CIConfigAnalysis |
| `src/metagit/core/config/models.py` | MetagitConfig |
| `src/metagit/core/record/models.py` | MetagitRecord |
| `src/metagit/core/utils/logging.py` | LoggingModel |
| `src/metagit/cli/commands/detect.py` | detect_project |
| `src/metagit/core/utils/files.py` | list_git_files |

## Entry Points

Start here when exploring this area:

- **`detect_project`** (Function) — `src/metagit/cli/commands/detect.py:58`
- **`list_git_files`** (Function) — `src/metagit/core/utils/files.py:136`
- **`convert_objects`** (Function) — `src/metagit/core/detect/manager.py:682`
- **`MetagitConfig`** (Class) — `src/metagit/core/config/models.py:753`
- **`DetectionManager`** (Class) — `src/metagit/core/detect/manager.py:50`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `MetagitConfig` | Class | `src/metagit/core/config/models.py` | 753 |
| `DetectionManager` | Class | `src/metagit/core/detect/manager.py` | 50 |
| `GitBranchAnalysis` | Class | `src/metagit/core/detect/models.py` | 83 |
| `CIConfigAnalysis` | Class | `src/metagit/core/detect/models.py` | 177 |
| `MetagitRecord` | Class | `src/metagit/core/record/models.py` | 120 |
| `LoggingModel` | Class | `src/metagit/core/utils/logging.py` | 627 |
| `detect_project` | Function | `src/metagit/cli/commands/detect.py` | 58 |
| `list_git_files` | Function | `src/metagit/core/utils/files.py` | 136 |
| `convert_objects` | Function | `src/metagit/core/detect/manager.py` | 682 |
| `run_all` | Method | `src/metagit/core/detect/manager.py` | 218 |
| `run_specific` | Method | `src/metagit/core/detect/manager.py` | 305 |
| `run` | Method | `src/metagit/core/detect/manager.py` | 980 |
| `all_files` | Method | `src/metagit/core/detect/manager.py` | 1008 |
| `to_yaml` | Method | `src/metagit/core/detect/manager.py` | 671 |
| `to_json` | Method | `src/metagit/core/detect/manager.py` | 705 |
| `_extract_metadata` | Method | `src/metagit/core/detect/manager.py` | 365 |
| `_detect_languages` | Method | `src/metagit/core/detect/manager.py` | 394 |
| `_detect_project_type` | Method | `src/metagit/core/detect/manager.py` | 458 |
| `_analyze_files` | Method | `src/metagit/core/detect/manager.py` | 499 |
| `_detect_metrics` | Method | `src/metagit/core/detect/manager.py` | 523 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Commands | 4 calls |

## How to Explore

1. `gitnexus_context({name: "detect_project"})` — see callers and callees
2. `gitnexus_query({query: "detect"})` — find related execution flows
3. Read key files listed above for implementation details
