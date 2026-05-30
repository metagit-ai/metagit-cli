---
name: scripts
description: "Skill for the Scripts area of metagit-cli. 28 symbols across 5 files."
---

# Scripts

28 symbols | 5 files | Cohesion: 100%

## When to Use

- Working with code in `scripts/`
- Understanding how run_step, resolve_pytest_cmd, changed_paths_for_security work
- Modifying scripts-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `scripts/prepush-gate.py` | run_step, resolve_pytest_cmd, _git_lines, changed_paths_for_security, security_scan_plan (+2) |
| `skills/metagit-agent-access/scripts/optimize_agent_access.py` | _read_text, _detect_project, _fill_template, _html_comment_block, audit (+2) |
| `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | _read_text, _detect_project, _fill_template, _html_comment_block, audit (+2) |
| `tests/scripts/test_prepush_gate_security.py` | _prepush_gate_module, test_security_scan_plan_full_when_unknown, test_security_scan_plan_deps_triggers_sync, test_security_scan_plan_src_without_sync, test_security_scan_plan_skips_docs_only |
| `scripts/validate_skills.py` | validate_skill, main |

## Entry Points

Start here when exploring this area:

- **`run_step`** (Function) — `scripts/prepush-gate.py:12`
- **`resolve_pytest_cmd`** (Function) — `scripts/prepush-gate.py:37`
- **`changed_paths_for_security`** (Function) — `scripts/prepush-gate.py:61`
- **`security_scan_plan`** (Function) — `scripts/prepush-gate.py:81`
- **`run_security_scan`** (Function) — `scripts/prepush-gate.py:94`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `run_step` | Function | `scripts/prepush-gate.py` | 12 |
| `resolve_pytest_cmd` | Function | `scripts/prepush-gate.py` | 37 |
| `changed_paths_for_security` | Function | `scripts/prepush-gate.py` | 61 |
| `security_scan_plan` | Function | `scripts/prepush-gate.py` | 81 |
| `run_security_scan` | Function | `scripts/prepush-gate.py` | 94 |
| `main` | Function | `scripts/prepush-gate.py` | 120 |
| `audit` | Function | `skills/metagit-agent-access/scripts/optimize_agent_access.py` | 123 |
| `apply` | Function | `skills/metagit-agent-access/scripts/optimize_agent_access.py` | 137 |
| `main` | Function | `skills/metagit-agent-access/scripts/optimize_agent_access.py` | 180 |
| `audit` | Function | `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | 123 |
| `apply` | Function | `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | 137 |
| `main` | Function | `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | 180 |
| `test_security_scan_plan_full_when_unknown` | Function | `tests/scripts/test_prepush_gate_security.py` | 18 |
| `test_security_scan_plan_deps_triggers_sync` | Function | `tests/scripts/test_prepush_gate_security.py` | 24 |
| `test_security_scan_plan_src_without_sync` | Function | `tests/scripts/test_prepush_gate_security.py` | 30 |
| `test_security_scan_plan_skips_docs_only` | Function | `tests/scripts/test_prepush_gate_security.py` | 39 |
| `validate_skill` | Function | `scripts/validate_skills.py` | 50 |
| `main` | Function | `scripts/validate_skills.py` | 129 |
| `_git_lines` | Function | `scripts/prepush-gate.py` | 47 |
| `_read_text` | Function | `skills/metagit-agent-access/scripts/optimize_agent_access.py` | 23 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → _git_lines` | intra_community | 4 |

## How to Explore

1. `gitnexus_context({name: "run_step"})` — see callers and callees
2. `gitnexus_query({query: "scripts"})` — find related execution flows
3. Read key files listed above for implementation details
