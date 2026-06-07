---
name: scripts
description: "Skill for the Scripts area of metagit-cli. 54 symbols across 13 files."
metadata:
  internal: true
---
# Scripts

54 symbols | 13 files | Cohesion: 98%

## When to Use

- Working with code in `scripts/`
- Understanding how run_step, resolve_manifest_fixture_cmd, resolve_changelog_check_cmd work
- Modifying scripts-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `scripts/prepush-gate.py` | run_step, resolve_manifest_fixture_cmd, resolve_changelog_check_cmd, resolve_agent_template_fixture_cmd, resolve_pytest_cmd (+5) |
| `skills/metagit-agent-access/scripts/optimize_agent_access.py` | _read_text, _detect_project, _fill_template, _html_comment_block, audit (+2) |
| `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | _read_text, _detect_project, _fill_template, _html_comment_block, audit (+2) |
| `scripts/tag_internal_skills.py` | is_public_skill, find_skill_files, has_internal_metadata, add_internal_metadata, tag_internal_skills (+1) |
| `scripts/scaffold-agent-templates.py` | _skills_yaml, _body, _frontmatter, write_template, main |
| `tests/scripts/test_prepush_gate_security.py` | _prepush_gate_module, test_security_scan_plan_full_when_unknown, test_security_scan_plan_deps_triggers_sync, test_security_scan_plan_src_without_sync, test_security_scan_plan_skips_docs_only |
| `skills/metagit-gitnexus/scripts/ingest_workspace_graph.py` | _load_tool_calls, _run_cypher, main |
| `src/metagit/data/skills/metagit-gitnexus/scripts/ingest_workspace_graph.py` | _load_tool_calls, _run_cypher, main |
| `scripts/validate-agent-template-fixtures.py` | default_fixture_file, main |
| `src/metagit/core/agent/catalog.py` | validate_all_templates, _validate_manifest |

## Entry Points

Start here when exploring this area:

- **`run_step`** (Function) — `scripts/prepush-gate.py:12`
- **`resolve_manifest_fixture_cmd`** (Function) — `scripts/prepush-gate.py:37`
- **`resolve_changelog_check_cmd`** (Function) — `scripts/prepush-gate.py:43`
- **`resolve_agent_template_fixture_cmd`** (Function) — `scripts/prepush-gate.py:49`
- **`resolve_pytest_cmd`** (Function) — `scripts/prepush-gate.py:55`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `run_step` | Function | `scripts/prepush-gate.py` | 12 |
| `resolve_manifest_fixture_cmd` | Function | `scripts/prepush-gate.py` | 37 |
| `resolve_changelog_check_cmd` | Function | `scripts/prepush-gate.py` | 43 |
| `resolve_agent_template_fixture_cmd` | Function | `scripts/prepush-gate.py` | 49 |
| `resolve_pytest_cmd` | Function | `scripts/prepush-gate.py` | 55 |
| `changed_paths_for_security` | Function | `scripts/prepush-gate.py` | 79 |
| `security_scan_plan` | Function | `scripts/prepush-gate.py` | 99 |
| `run_security_scan` | Function | `scripts/prepush-gate.py` | 112 |
| `main` | Function | `scripts/prepush-gate.py` | 138 |
| `audit` | Function | `skills/metagit-agent-access/scripts/optimize_agent_access.py` | 123 |
| `apply` | Function | `skills/metagit-agent-access/scripts/optimize_agent_access.py` | 137 |
| `main` | Function | `skills/metagit-agent-access/scripts/optimize_agent_access.py` | 180 |
| `audit` | Function | `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | 123 |
| `apply` | Function | `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | 137 |
| `main` | Function | `src/metagit/data/skills/metagit-agent-access/scripts/optimize_agent_access.py` | 180 |
| `is_public_skill` | Function | `scripts/tag_internal_skills.py` | 30 |
| `find_skill_files` | Function | `scripts/tag_internal_skills.py` | 40 |
| `has_internal_metadata` | Function | `scripts/tag_internal_skills.py` | 44 |
| `add_internal_metadata` | Function | `scripts/tag_internal_skills.py` | 48 |
| `tag_internal_skills` | Function | `scripts/tag_internal_skills.py` | 70 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Agent_validate → Overlay_template_dir` | cross_community | 7 |
| `Agent_validate → _bundled_template_dir` | cross_community | 5 |
| `Agent_validate → Resolve_template_file` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Agent | 2 calls |

## How to Explore

1. `gitnexus_context({name: "run_step"})` — see callers and callees
2. `gitnexus_query({query: "scripts"})` — find related execution flows
3. Read key files listed above for implementation details
